from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.api.deps import get_tenant_db
from app.core.database import get_request_db
from app.core.security import get_current_user, require_roles, require_permission, tenant_has_module
from app.core.licensing import MODULE_SMS, MODULE_LABELS
from app.core.tenancy import tenant_from_request
from app.core.mailer import send_email, MailerError
from app.core.sms import send_sms, SmsError
from app.core.reminders import send_due_reminders
from app.models.user import User, UserRole
from app.models.communication import Communication, ReminderRule, ReminderLog
from app.models.medical import MedicalRecord
from app.models.animal import Animal
from app.models.client import Client
from app.models.settings import ClinicSettings
from app.schemas.communication import (
    CommunicationCreate, CommunicationResponse,
    ReminderRuleCreate, ReminderRuleResponse,
)

router = APIRouter(prefix="/communications", tags=["Communications & Reminders"])


@router.get("", response_model=list[CommunicationResponse])
def list_communications(
    client_id: Optional[int] = Query(None),
    channel: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Communication)
    if client_id:
        query = query.filter(Communication.client_id == client_id)
    if channel:
        query = query.filter(Communication.channel == channel)
    return query.order_by(Communication.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=CommunicationResponse, status_code=201,
             dependencies=[Depends(require_permission("communications"))])
def send_communication(
    data: CommunicationCreate,
    request: Request,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    # SMS is a paid module: gate it server-side (the real lock). E-mail is free.
    if data.channel == "sms" and not tenant_has_module(request, MODULE_SMS):
        raise HTTPException(
            status_code=403,
            detail=f"Module « {MODULE_LABELS[MODULE_SMS]} » non activé pour votre clinique.",
        )

    client = db.query(Client).filter(Client.id == data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouve")

    clinic = db.query(ClinicSettings).first()
    comm = Communication(**data.model_dump())
    status, error = "sent", None
    try:
        if data.channel == "email":
            if not client.email:
                raise MailerError("Le client n'a pas d'adresse e-mail")
            send_email(
                client.email, data.subject or "", data.body,
                from_email=(clinic.email if clinic else None),
                from_name=(clinic.clinic_name if clinic else None),
            )
        elif data.channel == "sms":
            recipient = client.mobile or client.phone
            if not recipient:
                raise SmsError("Le client n'a pas de numéro de téléphone")
            send_sms(recipient, data.body)
        else:
            raise HTTPException(status_code=400, detail="Canal non supporté (email ou sms)")
    except (MailerError, SmsError) as exc:
        status, error = "failed", str(exc)

    comm.status = status
    comm.error_message = error
    if status == "sent":
        comm.sent_at = datetime.utcnow()
    db.add(comm)
    db.commit()
    db.refresh(comm)
    if status == "failed":
        raise HTTPException(status_code=502, detail=f"Envoi échoué: {error}")
    return comm


# --- Reminder Rules ---
@router.get("/reminders", response_model=list[ReminderRuleResponse])
def list_reminder_rules(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(ReminderRule).order_by(ReminderRule.name).all()


@router.post("/reminders", response_model=ReminderRuleResponse, status_code=201,
             dependencies=[Depends(require_permission("communications"))])
def create_reminder_rule(
    data: ReminderRuleCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    rule = ReminderRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/reminders/{rule_id}", response_model=ReminderRuleResponse,
            dependencies=[Depends(require_permission("communications"))])
def update_reminder_rule(
    rule_id: int,
    data: ReminderRuleCreate,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    rule = db.query(ReminderRule).filter(ReminderRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Règle non trouvée")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/reminders/{rule_id}", status_code=204,
               dependencies=[Depends(require_permission("communications"))])
def delete_reminder_rule(
    rule_id: int,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    rule = db.query(ReminderRule).filter(ReminderRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Règle non trouvée")
    rule.is_active = False
    db.commit()


@router.get("/reminders/postal-due")
def get_postal_due_reminders(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Return animals with vaccine reminders due via postal channel.

    Looks for active postal reminder rules and finds animals with
    vaccination records older than 1 year (annual recall logic).
    """
    from datetime import datetime, timedelta

    rules = db.query(ReminderRule).filter(
        ReminderRule.is_active == True,
        ReminderRule.channel.in_(["postal", "both"]),
        ReminderRule.reminder_type == "vaccine",
    ).all()

    if not rules:
        return []

    results = []
    today = datetime.utcnow().date()

    for rule in rules:
        # Find animals with vaccination records
        vaccine_animals = (
            db.query(Animal, Client, MedicalRecord)
            .join(Client, Animal.client_id == Client.id)
            .join(MedicalRecord, MedicalRecord.animal_id == Animal.id)
            .filter(MedicalRecord.record_type == "vaccination")
            .order_by(MedicalRecord.created_at.desc())
            .limit(5000)
            .all()
        )

        seen_animals = set()
        for animal, client, record in vaccine_animals:
            if animal.id in seen_animals:
                continue
            seen_animals.add(animal.id)

            # Consider due if last vaccine > (365 - days_before) days ago
            record_date = record.created_at.date() if record.created_at else None
            if not record_date:
                continue
            due_date = record_date + timedelta(days=365)
            if due_date > today + timedelta(days=rule.days_before):
                continue

            # Check if already sent
            already_sent = db.query(ReminderLog).filter(
                ReminderLog.rule_id == rule.id,
                ReminderLog.animal_id == animal.id,
                ReminderLog.channel == "postal",
            ).first()
            if already_sent:
                continue

            results.append({
                "rule_id": rule.id,
                "rule_name": rule.name,
                "animal_id": animal.id,
                "animal_name": animal.name,
                "species": animal.species.value if animal.species else None,
                "client_id": client.id,
                "client_name": f"{client.first_name} {client.last_name}",
                "client_address": client.address or "",
                "client_postal_code": client.postal_code or "",
                "client_city": client.city or "",
                "vaccine_name": record.assessment or record.subjective or "Vaccination",
                "due_date": str(due_date),
                "postal_template": rule.postal_template or "",
            })

    return results


@router.post("/reminders/run",
             dependencies=[Depends(require_permission("communications"))])
def run_reminders(
    request: Request,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Manually trigger the due-reminder send for this tenant (also runs daily)."""
    base = str(request.base_url).rstrip("/")
    return send_due_reminders(db, base, modules=tenant_from_request(request).modules)


@router.get("/unsubscribe/{token}")
def unsubscribe(token: str, db: Session = Depends(get_request_db)):
    """Public opt-out link embedded in reminder e-mails (no authentication)."""
    client = db.query(Client).filter(Client.unsubscribe_token == token).first()
    if not client:
        return HTMLResponse(
            "<html><body style='font-family:sans-serif;padding:2rem'>"
            "<h3>Lien invalide ou expiré.</h3></body></html>",
            status_code=404,
        )
    client.accepts_reminders = False
    db.commit()
    return HTMLResponse(
        "<html><body style='font-family:sans-serif;padding:2rem'>"
        "<h3>Désinscription confirmée.</h3>"
        "<p>Vous ne recevrez plus de rappels automatiques de la clinique.</p></body></html>"
    )
