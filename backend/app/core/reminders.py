"""Find and send due vaccination reminders (e-mail / SMS) for one tenant.

Reuses the annual-recall heuristic of the postal-due endpoint, but actually
sends via the mailer / SMS provider, honours the client opt-out, dedupes via
ReminderLog (only successes are logged, so failures retry next run) and records
each attempt as a Communication.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.mailer import send_email, MailerError
from app.core.sms import send_sms, SmsError
from app.models.communication import Communication, ReminderRule, ReminderLog
from app.models.medical import MedicalRecord
from app.models.animal import Animal
from app.models.client import Client
from app.models.settings import ClinicSettings


def _render(template, ctx, default):
    text = template or default
    for key, value in ctx.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def _ensure_token(db, client):
    if not client.unsubscribe_token:
        client.unsubscribe_token = uuid.uuid4().hex
        db.flush()
    return client.unsubscribe_token


def send_due_reminders(db: Session, base_url: str = "", modules=None):
    """Send all due vaccination reminders for this tenant DB. Returns counts.

    ``modules`` is the tenant's unlocked module set; when it doesn't include
    ``sms`` the SMS channel is skipped (e-mail still goes out). Defaults to all
    modules so direct callers / tests keep the previous behaviour.
    """
    from app.core.licensing import ALL_MODULES, MODULE_SMS

    if modules is None:
        modules = ALL_MODULES
    sms_enabled = MODULE_SMS in modules

    rules = db.query(ReminderRule).filter(
        ReminderRule.is_active == True,
        ReminderRule.channel.in_(["email", "sms", "both"]),
        ReminderRule.reminder_type == "vaccine",
    ).all()
    counts = {"sent": 0, "failed": 0, "skipped": 0}
    if not rules:
        return counts

    clinic = db.query(ClinicSettings).first()
    clinic_name = (clinic.clinic_name if clinic else None) or settings.APP_NAME
    clinic_email = clinic.email if clinic else None
    today = datetime.utcnow().date()

    for rule in rules:
        channels = ["email", "sms"] if rule.channel == "both" else [rule.channel]
        # Drop SMS when the paid module isn't active for this tenant.
        if not sms_enabled:
            channels = [c for c in channels if c != "sms"]
        rows = (
            db.query(Animal, Client, MedicalRecord)
            .join(Client, Animal.client_id == Client.id)
            .join(MedicalRecord, MedicalRecord.animal_id == Animal.id)
            .filter(MedicalRecord.record_type == "vaccination")
            .order_by(MedicalRecord.created_at.desc())
            .limit(5000)
            .all()
        )
        seen = set()
        for animal, client, record in rows:
            if animal.id in seen:
                continue
            seen.add(animal.id)

            species = str(getattr(animal.species, "value", animal.species)) if animal.species else None
            if rule.species and species and species != rule.species:
                continue
            record_date = record.created_at.date() if record.created_at else None
            if not record_date:
                continue
            if record_date + timedelta(days=365) > today + timedelta(days=rule.days_before):
                continue
            if not client.accepts_reminders:
                counts["skipped"] += 1
                continue

            ctx = {
                "animal": animal.name or "",
                "client": f"{client.first_name} {client.last_name}".strip(),
                "clinic": clinic_name,
                "date": str(record_date + timedelta(days=365)),
            }

            for channel in channels:
                already = db.query(ReminderLog).filter(
                    ReminderLog.rule_id == rule.id,
                    ReminderLog.animal_id == animal.id,
                    ReminderLog.channel == channel,
                ).first()
                if already:
                    continue
                if channel == "email" and not client.email:
                    continue
                if channel == "sms" and not (client.mobile or client.phone):
                    continue

                status, error, body = "sent", None, ""
                try:
                    if channel == "email":
                        body = _render(
                            rule.email_template, ctx,
                            f"Bonjour {ctx['client']},\n\nUn rappel de vaccination pour "
                            f"{ctx['animal']} est dû (échéance {ctx['date']}). Merci de prendre "
                            f"rendez-vous.\n\n{clinic_name}",
                        )
                        if base_url:
                            token = _ensure_token(db, client)
                            body += (
                                f"\n\nPour ne plus recevoir ces rappels : "
                                f"{base_url.rstrip('/')}/api/v1/communications/unsubscribe/{token}"
                            )
                        send_email(
                            client.email, f"Rappel de vaccination — {ctx['animal']}", body,
                            from_email=clinic_email, from_name=clinic_name,
                        )
                    else:
                        body = _render(
                            rule.sms_template, ctx,
                            f"{clinic_name}: rappel de vaccination pour {ctx['animal']} "
                            f"(échéance {ctx['date']}).",
                        )
                        send_sms(client.mobile or client.phone, body)
                except (MailerError, SmsError) as exc:
                    status, error = "failed", str(exc)

                # Only successes are logged in ReminderLog -> failures retry later.
                if status == "sent":
                    db.add(ReminderLog(
                        rule_id=rule.id, animal_id=animal.id, client_id=client.id,
                        channel=channel, status="sent",
                        next_due_date=datetime.utcnow() + timedelta(days=365),
                    ))
                db.add(Communication(
                    client_id=client.id, channel=channel,
                    subject=f"Rappel vaccination {ctx['animal']}", body=body,
                    status=status, error_message=error,
                    sent_at=datetime.utcnow() if status == "sent" else None,
                ))
                counts["sent" if status == "sent" else "failed"] += 1

    db.commit()
    return counts


# Lead time before a due vaccination at which the reminder goes out.
VACCINE_REMINDER_LEAD_DAYS = 21


def send_due_vaccination_reminders(db: Session, base_url: str = "", modules=None):
    """Protocol-driven vaccination reminders (the ``vaccine_protocols`` module).

    Sends e-mail (and SMS when that module is on too) for each animal's live next
    dose due within the lead window or overdue, deduped to the latest
    administration per (animal, valence) and to one send via ``reminder_sent``.
    """
    from app.core.licensing import ALL_MODULES, MODULE_VACCINE_PROTOCOLS, MODULE_SMS
    from app.models.vaccination import Vaccination

    if modules is None:
        modules = ALL_MODULES
    counts = {"sent": 0, "failed": 0, "skipped": 0}
    if MODULE_VACCINE_PROTOCOLS not in modules:
        return counts
    sms_enabled = MODULE_SMS in modules

    clinic = db.query(ClinicSettings).first()
    clinic_name = (clinic.clinic_name if clinic else None) or settings.APP_NAME
    clinic_email = clinic.email if clinic else None
    cutoff = datetime.utcnow().date() + timedelta(days=VACCINE_REMINDER_LEAD_DAYS)

    rows = (
        db.query(Vaccination)
        .filter(Vaccination.next_due_date.isnot(None))
        .order_by(Vaccination.date_administered.desc(), Vaccination.id.desc())
        .limit(5000).all()
    )
    latest = {}
    for v in rows:
        latest.setdefault((v.animal_id, (v.valence or "").lower()), v)

    for v in latest.values():
        if v.reminder_sent or not v.next_due_date or v.next_due_date > cutoff:
            continue
        animal = db.query(Animal).filter(Animal.id == v.animal_id).first()
        if not animal:
            continue
        client = db.query(Client).filter(Client.id == animal.client_id).first()
        if not client or not client.accepts_reminders:
            counts["skipped"] += 1
            continue

        who = f"{client.first_name} {client.last_name}".strip()
        due = v.next_due_date.strftime("%d/%m/%Y")
        sent_any = False

        if client.email:
            body = (
                f"Bonjour {who},\n\nLe rappel de vaccination « {v.valence} » de {animal.name} "
                f"est prévu pour le {due}. Merci de prendre rendez-vous.\n\n{clinic_name}"
            )
            if base_url:
                token = _ensure_token(db, client)
                body += (
                    f"\n\nPour ne plus recevoir ces rappels : "
                    f"{base_url.rstrip('/')}/api/v1/communications/unsubscribe/{token}"
                )
            try:
                send_email(client.email, f"Rappel de vaccination — {animal.name}", body,
                           from_email=clinic_email, from_name=clinic_name)
                db.add(Communication(client_id=client.id, channel="email",
                                     subject=f"Rappel vaccination {animal.name}", body=body,
                                     status="sent", sent_at=datetime.utcnow()))
                sent_any = True
            except MailerError as exc:
                db.add(Communication(client_id=client.id, channel="email",
                                     subject="Rappel vaccination", body=body,
                                     status="failed", error_message=str(exc)))
                counts["failed"] += 1

        if sms_enabled and (client.mobile or client.phone):
            sbody = f"{clinic_name}: rappel vaccination {v.valence} pour {animal.name} (échéance {due})."
            try:
                send_sms(client.mobile or client.phone, sbody)
                db.add(Communication(client_id=client.id, channel="sms",
                                     subject=f"Rappel vaccination {animal.name}", body=sbody,
                                     status="sent", sent_at=datetime.utcnow()))
                sent_any = True
            except SmsError as exc:
                db.add(Communication(client_id=client.id, channel="sms",
                                     subject="Rappel vaccination", body=sbody,
                                     status="failed", error_message=str(exc)))
                counts["failed"] += 1

        if sent_any:
            v.reminder_sent = True
            counts["sent"] += 1

    db.commit()
    return counts
