"""Two-way Google Calendar sync engine (polling).

Per vet, on each run (scheduler or manual):
  1. ``pull_changes`` — incremental delta from Google. Events WE created that were
     changed/deleted on Google raise a CONFLICT (we never auto-overwrite); events
     the vet owns are imported as read-only busy blocks.
  2. ``push_appointments`` — create/delete the vet's clinic appointments on Google.
     Appointments with an OPEN conflict are skipped (no overwrite until resolved).
  3. ``detect_double_bookings`` — clinic appointments overlapping an imported block
     raise a double-booking conflict.

Conflict policy is "signal, never overwrite": divergences become
:class:`CalendarSyncConflict` rows + notifications for manual resolution.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core import google_calendar as gcal
from app.models.appointment import Appointment, AppointmentStatus, AppointmentType
from app.models.user import User, Notification
from app.models.client import Client
from app.models.animal import Animal
from app.models.google_calendar import (
    GoogleCalendarAccount, ExternalCalendarEvent, CalendarSyncConflict,
)

logger = logging.getLogger(__name__)

SYNC_PAST_DAYS = 1
SYNC_FUTURE_DAYS = 60
_REMOVED_STATUSES = {AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW}
_TYPE_LABELS = {
    AppointmentType.CONSULTATION: "Consultation",
    AppointmentType.SURGERY: "Chirurgie",
    AppointmentType.EMERGENCY: "Urgence",
    AppointmentType.VACCINATION: "Vaccination",
    AppointmentType.CHECKUP: "Contrôle",
    AppointmentType.GROOMING: "Toilettage",
    AppointmentType.OTHER: "Rendez-vous",
}


# ─── datetime helpers ────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc(dt: datetime) -> datetime:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _same_instant(a: datetime, b: datetime) -> bool:
    a, b = _to_utc(a), _to_utc(b)
    if a is None or b is None:
        return a is b
    return a.replace(microsecond=0) == b.replace(microsecond=0)


def _parse_dt(node: dict):
    if not node:
        return None, False
    if node.get("dateTime"):
        return _iso(node["dateTime"]), False
    if node.get("date"):
        return _iso(node["date"] + "T00:00:00+00:00"), True
    return None, False


def _iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# ─── token / client ──────────────────────────────────────────────────────────

def ensure_access_token(db: Session, account: GoogleCalendarAccount) -> str:
    """Return a valid access token, refreshing via the refresh token if needed."""
    if not account.refresh_token:
        raise gcal.GoogleCalendarError("Compte Google non connecté (refresh token manquant)")
    if account.access_token and account.token_expiry and _to_utc(account.token_expiry) > _now():
        return account.access_token
    data = gcal.refresh_access_token(account.refresh_token)
    account.access_token = data.get("access_token")
    account.token_expiry = gcal.expiry_from(data)
    db.commit()
    return account.access_token


def make_client(db: Session, account: GoogleCalendarAccount) -> gcal.GoogleCalendarClient:
    return gcal.GoogleCalendarClient(ensure_access_token(db, account), account.calendar_id or "primary")


# ─── conflict signalling ─────────────────────────────────────────────────────

_CONFLICT_TITLES = {
    "modified_on_google": "RDV modifié dans Google Agenda",
    "deleted_on_google": "RDV supprimé dans Google Agenda",
    "double_booking": "Conflit d'horaire avec ton agenda Google",
}


def _signal_conflict(db, user_id, conflict_type, *, appointment_id=None,
                     google_event_id=None, details=None, message=""):
    """Create a conflict + notification, unless an equivalent one is already open."""
    q = db.query(CalendarSyncConflict).filter(
        CalendarSyncConflict.user_id == user_id,
        CalendarSyncConflict.conflict_type == conflict_type,
        CalendarSyncConflict.status == "open",
    )
    if appointment_id is not None:
        q = q.filter(CalendarSyncConflict.appointment_id == appointment_id)
    if google_event_id is not None:
        q = q.filter(CalendarSyncConflict.google_event_id == google_event_id)
    if q.first():
        return None

    conflict = CalendarSyncConflict(
        user_id=user_id, appointment_id=appointment_id,
        google_event_id=google_event_id, conflict_type=conflict_type,
        details=details or {}, status="open",
    )
    db.add(conflict)
    db.add(Notification(
        user_id=user_id,
        title=_CONFLICT_TITLES.get(conflict_type, "Conflit de synchronisation"),
        message=message or "À vérifier dans l'agenda.",
        notification_type="alert",
        link="/agenda?conflicts=1",
    ))
    return conflict


# ─── push (app → Google) ─────────────────────────────────────────────────────

def _summary(appt, client, animal) -> str:
    label = _TYPE_LABELS.get(appt.appointment_type, "Rendez-vous")
    who = animal.name if animal else None
    cli = f"{client.first_name} {client.last_name}".strip() if client else None
    return " — ".join(p for p in [label, who, f"({cli})" if cli else None] if p)


def _event_payload(appt, summary) -> dict:
    return {
        "summary": summary,
        "description": appt.reason or "",
        "start": {"dateTime": _to_utc(appt.start_time).isoformat()},
        "end": {"dateTime": _to_utc(appt.end_time).isoformat()},
        "extendedProperties": {"private": {"angeallvet_appointment_id": str(appt.id)}},
    }


def _conflicted_appointment_ids(db, user_id) -> set:
    rows = db.query(CalendarSyncConflict.appointment_id).filter(
        CalendarSyncConflict.user_id == user_id,
        CalendarSyncConflict.status == "open",
        CalendarSyncConflict.appointment_id.isnot(None),
    ).all()
    return {r[0] for r in rows}


def push_appointments(db: Session, account: GoogleCalendarAccount, client: gcal.GoogleCalendarClient) -> dict:
    lo = _now() - timedelta(days=SYNC_PAST_DAYS)
    hi = _now() + timedelta(days=SYNC_FUTURE_DAYS)
    rows = (
        db.query(Appointment, Client, Animal)
        .outerjoin(Client, Appointment.client_id == Client.id)
        .outerjoin(Animal, Appointment.animal_id == Animal.id)
        .filter(
            Appointment.veterinarian_id == account.user_id,
            Appointment.start_time >= lo,
            Appointment.start_time <= hi,
        )
        .all()
    )
    skip = _conflicted_appointment_ids(db, account.user_id)
    counts = {"created": 0, "updated": 0, "deleted": 0}
    for appt, cli, animal in rows:
        if appt.id in skip:
            continue  # divergent — wait for manual resolution, never overwrite
        if appt.status in _REMOVED_STATUSES:
            if appt.google_event_id:
                client.delete_event(appt.google_event_id)
                appt.google_event_id = None
                counts["deleted"] += 1
            continue
        payload = _event_payload(appt, _summary(appt, cli, animal))
        if not appt.google_event_id:
            ev = client.insert_event(payload)
            appt.google_event_id = ev.get("id")
            counts["created"] += 1
        elif account.last_sync_at is None or (appt.updated_at and _to_utc(appt.updated_at) > _to_utc(account.last_sync_at)):
            client.update_event(appt.google_event_id, payload)
            counts["updated"] += 1
    db.commit()
    return counts


# ─── pull (Google → app) ─────────────────────────────────────────────────────

def pull_changes(db: Session, account: GoogleCalendarAccount, client: gcal.GoogleCalendarClient) -> dict:
    time_min = _now() - timedelta(days=SYNC_PAST_DAYS)
    try:
        events, next_token = client.list_events(sync_token=account.sync_token, time_min=time_min)
    except gcal.SyncTokenExpired:
        account.sync_token = None
        events, next_token = client.list_events(sync_token=None, time_min=time_min)

    counts = {"imported": 0, "removed": 0, "conflicts": 0}
    for ev in events:
        gid = ev.get("id")
        status = ev.get("status")  # confirmed | tentative | cancelled
        appt_id = (
            (ev.get("extendedProperties") or {}).get("private", {}).get("angeallvet_appointment_id")
        )

        if appt_id:  # an event WE created → look for divergence (signal only)
            appt = db.query(Appointment).filter(Appointment.id == int(appt_id)).first()
            if not appt:
                continue
            if status == "cancelled":
                if appt.status not in _REMOVED_STATUSES and _signal_conflict(
                    db, account.user_id, "deleted_on_google",
                    appointment_id=appt.id, google_event_id=gid,
                    message=f"Le RDV du {_to_utc(appt.start_time):%d/%m %H:%M} a été supprimé côté Google.",
                ):
                    counts["conflicts"] += 1
            else:
                g_start, _ = _parse_dt(ev.get("start"))
                g_end, _ = _parse_dt(ev.get("end"))
                if g_start and (not _same_instant(g_start, appt.start_time) or not _same_instant(g_end, appt.end_time)):
                    if _signal_conflict(
                        db, account.user_id, "modified_on_google",
                        appointment_id=appt.id, google_event_id=gid,
                        details={
                            "app": {"start": _to_utc(appt.start_time).isoformat(),
                                    "end": _to_utc(appt.end_time).isoformat()},
                            "google": {"start": g_start.isoformat(), "end": g_end.isoformat() if g_end else None},
                        },
                        message=f"Le RDV du {_to_utc(appt.start_time):%d/%m %H:%M} a été déplacé côté Google.",
                    ):
                        counts["conflicts"] += 1
            continue

        # otherwise: the vet's own Google event → import as a busy block
        block = db.query(ExternalCalendarEvent).filter(
            ExternalCalendarEvent.user_id == account.user_id,
            ExternalCalendarEvent.external_id == gid,
        ).first()
        if status == "cancelled":
            if block:
                db.delete(block)
                counts["removed"] += 1
            continue
        start, all_day = _parse_dt(ev.get("start"))
        end, _ = _parse_dt(ev.get("end"))
        if not start or not end:
            continue
        if not block:
            block = ExternalCalendarEvent(user_id=account.user_id, source="google", external_id=gid)
            db.add(block)
            counts["imported"] += 1
        block.title = ev.get("summary") or "(occupé)"
        block.start_time = start
        block.end_time = end
        block.all_day = all_day
        block.status = "confirmed"

    account.sync_token = next_token
    db.commit()
    return counts


# ─── double-booking ──────────────────────────────────────────────────────────

def detect_double_bookings(db: Session, account: GoogleCalendarAccount) -> dict:
    now = _now()
    hi = now + timedelta(days=SYNC_FUTURE_DAYS)
    appts = (
        db.query(Appointment)
        .filter(
            Appointment.veterinarian_id == account.user_id,
            Appointment.start_time >= now,
            Appointment.start_time <= hi,
            Appointment.status.notin_(list(_REMOVED_STATUSES)),
        )
        .all()
    )
    blocks = (
        db.query(ExternalCalendarEvent)
        .filter(
            ExternalCalendarEvent.user_id == account.user_id,
            ExternalCalendarEvent.status == "confirmed",
            ExternalCalendarEvent.end_time >= now,
        )
        .all()
    )
    counts = {"conflicts": 0}
    for appt in appts:
        a_start, a_end = _to_utc(appt.start_time), _to_utc(appt.end_time)
        for b in blocks:
            if a_start < _to_utc(b.end_time) and _to_utc(b.start_time) < a_end:
                if _signal_conflict(
                    db, account.user_id, "double_booking",
                    appointment_id=appt.id, google_event_id=b.external_id,
                    details={
                        "appointment": {"start": a_start.isoformat(), "end": a_end.isoformat()},
                        "external": {"title": b.title,
                                     "start": _to_utc(b.start_time).isoformat(),
                                     "end": _to_utc(b.end_time).isoformat()},
                    },
                    message=f"Le RDV du {a_start:%d/%m %H:%M} chevauche « {b.title} » dans ton agenda Google.",
                ):
                    counts["conflicts"] += 1
                break
    db.commit()
    return counts


# ─── orchestration ───────────────────────────────────────────────────────────

def sync_user(db: Session, account: GoogleCalendarAccount) -> dict:
    """Run a full sync cycle for one connected vet. Never raises on API errors."""
    summary = {"pull": {}, "push": {}, "double_booking": {}}
    try:
        client = make_client(db, account)
        summary["pull"] = pull_changes(db, account, client)
        summary["push"] = push_appointments(db, account, client)
        summary["double_booking"] = detect_double_bookings(db, account)
        account.last_sync_at = _now()
        account.last_error = None
    except gcal.GoogleCalendarError as exc:
        account.last_error = str(exc)[:500]
        summary["error"] = account.last_error
        logger.warning("Google sync failed for user %s: %s", account.user_id, exc)
    db.commit()
    return summary


def sync_all_accounts(db: Session) -> dict:
    """Sync every active connected vet in this tenant DB."""
    accounts = db.query(GoogleCalendarAccount).filter(GoogleCalendarAccount.is_active == True).all()
    totals = {"users": 0, "errors": 0}
    for account in accounts:
        res = sync_user(db, account)
        totals["users"] += 1
        if res.get("error"):
            totals["errors"] += 1
    return totals
