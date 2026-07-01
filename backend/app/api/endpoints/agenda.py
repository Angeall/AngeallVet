"""Agenda — live iCal feed (the ``google_calendar`` paid module).

The in-app calendar is the free default. This module lets a vet subscribe their
own Google Calendar (one click) to a read-only ``.ics`` feed of their
appointments; Google then re-polls it on its own, so it stays in sync without
any OAuth round-trip.

Security model:
- The feed endpoint is **public** (Google fetches it with no JWT) but keyed by a
  per-user secret token, so the URL is unguessable.
- It is still gated by the tenant's ``google_calendar`` module: revoke the module
  and every subscribed feed stops returning data. The management endpoints that
  hand out / rotate the token are gated the same way.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_tenant_db
from app.core.config import settings
from app.core.database import get_request_db
from app.core.security import (
    get_current_user, require_module, tenant_has_module,
    create_app_token, verify_app_token,
)
from app.core.tenancy import tenant_from_request
from app.core.licensing import MODULE_GOOGLE_CALENDAR
from app.core.ical import build_calendar, ICalEvent
from app.core import google_calendar as gcal
from app.core import google_sync
from app.models.user import User
from app.models.appointment import Appointment, AppointmentStatus, AppointmentType
from app.models.client import Client
from app.models.animal import Animal
from app.models.settings import ClinicSettings
from app.models.google_calendar import (
    GoogleCalendarAccount, ExternalCalendarEvent, CalendarSyncConflict,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agenda", tags=["Agenda / iCal"])

# Map our appointment status to an iCal event status.
_ICS_STATUS = {
    AppointmentStatus.CANCELLED: "CANCELLED",
    AppointmentStatus.NO_SHOW: "CANCELLED",
    AppointmentStatus.SCHEDULED: "TENTATIVE",
}
_TYPE_LABELS = {
    AppointmentType.CONSULTATION: "Consultation",
    AppointmentType.SURGERY: "Chirurgie",
    AppointmentType.EMERGENCY: "Urgence",
    AppointmentType.VACCINATION: "Vaccination",
    AppointmentType.CHECKUP: "Contrôle",
    AppointmentType.GROOMING: "Toilettage",
    AppointmentType.OTHER: "Rendez-vous",
}


def _feed_base_url(request: Request) -> str:
    """Public base URL, honouring the reverse proxy (Caddy) forwarded headers."""
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or request.url.netloc
    )
    return f"{proto}://{host}"


def _feed_urls(request: Request, token: str) -> dict:
    feed = f"{_feed_base_url(request)}/api/v1/agenda/ical/{token}.ics"
    webcal = feed.replace("https://", "webcal://").replace("http://", "webcal://")
    # Google Calendar "add by URL" deep link — opens the confirm dialog prefilled.
    google = "https://calendar.google.com/calendar/r?cid=" + quote(webcal, safe="")
    return {"feed_url": feed, "webcal_url": webcal, "google_url": google}


def _ensure_token(db: Session, user: User) -> str:
    if not user.ical_token:
        user.ical_token = secrets.token_urlsafe(32)
        db.commit()
        db.refresh(user)
    return user.ical_token


# ─── Management (authenticated, gated by the module) ─────────────────────────

@router.get("/ical")
def ical_status(
    request: Request,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Current user's feed status + URLs (if a feed has been enabled)."""
    data = {
        "enabled": bool(current_user.ical_token),
        "module": tenant_has_module(request, MODULE_GOOGLE_CALENDAR),
    }
    if current_user.ical_token:
        data.update(_feed_urls(request, current_user.ical_token))
    return data


@router.post("/ical/enable")
def ical_enable(
    request: Request,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
    _module: bool = Depends(require_module(MODULE_GOOGLE_CALENDAR)),
):
    """Enable (or return) the current vet's personal iCal feed."""
    token = _ensure_token(db, current_user)
    return {"enabled": True, **_feed_urls(request, token)}


@router.post("/ical/rotate")
def ical_rotate(
    request: Request,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
    _module: bool = Depends(require_module(MODULE_GOOGLE_CALENDAR)),
):
    """Rotate the token — invalidates any previously subscribed feed."""
    current_user.ical_token = secrets.token_urlsafe(32)
    db.commit()
    db.refresh(current_user)
    return {"enabled": True, **_feed_urls(request, current_user.ical_token)}


@router.delete("/ical", status_code=204)
def ical_disable(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """Disable the feed (clients that were subscribed stop receiving data)."""
    current_user.ical_token = None
    db.commit()


# ─── Public feed (no JWT — fetched by Google; secured by the token) ──────────

@router.get("/ical/{token}.ics")
def ical_feed(token: str, request: Request, db: Session = Depends(get_request_db)):
    # Gate at the tenant level: the feed dies if the module is revoked.
    if not tenant_has_module(request, MODULE_GOOGLE_CALENDAR):
        raise HTTPException(status_code=403, detail="Module Google Agenda non activé")
    user = db.query(User).filter(User.ical_token == token).first() if token else None
    if not user:
        raise HTTPException(status_code=404, detail="Flux introuvable")

    rows = (
        db.query(Appointment, Client, Animal)
        .outerjoin(Client, Appointment.client_id == Client.id)
        .outerjoin(Animal, Appointment.animal_id == Animal.id)
        .filter(Appointment.veterinarian_id == user.id)
        .order_by(Appointment.start_time.desc())
        .limit(2000)
        .all()
    )

    clinic = db.query(ClinicSettings).first()
    clinic_name = (clinic.clinic_name if clinic else None) or "AngeallVet"
    location = ""
    if clinic:
        location = ", ".join(p for p in [clinic.address, clinic.city] if p)
    cal_name = f"{clinic_name} — {user.first_name} {user.last_name}".strip(" —")

    events = []
    for appt, client, animal in rows:
        label = _TYPE_LABELS.get(appt.appointment_type, "Rendez-vous")
        who = animal.name if animal else None
        client_name = f"{client.first_name} {client.last_name}".strip() if client else None
        summary = " — ".join(p for p in [label, who, f"({client_name})" if client_name else None] if p)
        events.append(ICalEvent(
            uid=f"appointment-{appt.id}@angeallvet",
            start=appt.start_time,
            end=appt.end_time,
            summary=summary,
            description=appt.reason or "",
            location=location,
            status=_ICS_STATUS.get(appt.status, "CONFIRMED"),
        ))

    body = build_calendar(cal_name, events)
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'inline; filename="agenda.ics"',
            "Cache-Control": "no-cache",
        },
    )


# ─── Google Calendar OAuth (two-way sync) ────────────────────────────────────

def _front_base() -> str:
    return (settings.FRONTEND_URL or "").rstrip("/")


@router.get("/google/connect")
def google_connect(
    request: Request,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
    _module: bool = Depends(require_module(MODULE_GOOGLE_CALENDAR)),
):
    """Return the Google consent URL. ``state`` is a short-lived, tenant-signed
    token identifying the vet, so the public callback can trust who connected."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="Google OAuth non configuré côté serveur")
    tenant = tenant_from_request(request)
    state = create_app_token(
        str(current_user.id), tenant.jwt_secret,
        expires_minutes=15, extra={"scope": "google_oauth"},
    )
    return {"auth_url": gcal.build_auth_url(state)}


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
    db: Session = Depends(get_request_db),
):
    """Public OAuth redirect target. Validates the signed state, exchanges the
    code, and stores the (encrypted) tokens for the vet."""
    front = _front_base()
    if error or not code or not state:
        return RedirectResponse(f"{front}/agenda?google=error")
    tenant = tenant_from_request(request)
    try:
        payload = verify_app_token(state, tenant.jwt_secret)
    except HTTPException:
        return RedirectResponse(f"{front}/agenda?google=error")
    if payload.get("scope") != "google_oauth":
        return RedirectResponse(f"{front}/agenda?google=error")
    if not tenant_has_module(request, MODULE_GOOGLE_CALENDAR):
        return RedirectResponse(f"{front}/agenda?google=error")

    user = db.query(User).filter(User.id == int(payload.get("sub", 0))).first()
    if not user:
        return RedirectResponse(f"{front}/agenda?google=error")
    try:
        tokens = gcal.exchange_code(code)
    except gcal.GoogleCalendarError as exc:
        logger.warning("Google code exchange failed: %s", exc)
        return RedirectResponse(f"{front}/agenda?google=error")

    account = db.query(GoogleCalendarAccount).filter(GoogleCalendarAccount.user_id == user.id).first()
    if not account:
        account = GoogleCalendarAccount(user_id=user.id)
        db.add(account)
    # Google only returns a refresh_token on first consent; keep the old one if absent.
    if tokens.get("refresh_token"):
        account.refresh_token = tokens["refresh_token"]
    account.access_token = tokens.get("access_token")
    account.token_expiry = gcal.expiry_from(tokens)
    account.google_email = gcal.email_from_id_token(tokens.get("id_token")) or account.google_email
    account.is_active = True
    account.last_error = None
    account.sync_token = None  # force a full pull on first sync
    db.commit()
    return RedirectResponse(f"{front}/agenda?google=connected")


@router.get("/google/status")
def google_status(
    request: Request,
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    acc = db.query(GoogleCalendarAccount).filter(
        GoogleCalendarAccount.user_id == current_user.id,
        GoogleCalendarAccount.is_active == True,
    ).first()
    open_conflicts = db.query(CalendarSyncConflict).filter(
        CalendarSyncConflict.user_id == current_user.id,
        CalendarSyncConflict.status == "open",
    ).count()
    return {
        "module": tenant_has_module(request, MODULE_GOOGLE_CALENDAR),
        "connected": bool(acc),
        "email": acc.google_email if acc else None,
        "last_sync_at": acc.last_sync_at.isoformat() if acc and acc.last_sync_at else None,
        "last_error": acc.last_error if acc else None,
        "open_conflicts": open_conflicts,
    }


@router.post("/google/sync")
def google_sync_now(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
    _module: bool = Depends(require_module(MODULE_GOOGLE_CALENDAR)),
):
    """Trigger an immediate sync for the current vet (also runs on a schedule)."""
    acc = db.query(GoogleCalendarAccount).filter(
        GoogleCalendarAccount.user_id == current_user.id,
        GoogleCalendarAccount.is_active == True,
    ).first()
    if not acc:
        raise HTTPException(status_code=400, detail="Compte Google non connecté")
    return google_sync.sync_user(db, acc)


@router.delete("/google", status_code=204)
def google_disconnect(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    acc = db.query(GoogleCalendarAccount).filter(
        GoogleCalendarAccount.user_id == current_user.id,
    ).first()
    if acc:
        if acc.refresh_token:
            gcal.revoke(acc.refresh_token)
        db.delete(acc)
    db.query(ExternalCalendarEvent).filter(
        ExternalCalendarEvent.user_id == current_user.id,
    ).delete()
    # Clear our pushed event ids so a future reconnect re-pushes cleanly.
    db.query(Appointment).filter(
        Appointment.veterinarian_id == current_user.id,
        Appointment.google_event_id.isnot(None),
    ).update({"google_event_id": None})
    db.query(CalendarSyncConflict).filter(
        CalendarSyncConflict.user_id == current_user.id,
        CalendarSyncConflict.status == "open",
    ).update({"status": "resolved", "resolution": "dismissed",
              "resolved_at": datetime.now(timezone.utc)})
    db.commit()


# ─── External busy blocks + conflicts ────────────────────────────────────────

def _parse_q_dt(value: str, default: datetime) -> datetime:
    if not value:
        return default
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return default


@router.get("/external-events")
def external_events(
    start: str = Query(default=""),
    end: str = Query(default=""),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    """The current vet's imported Google busy blocks in a window (read-only)."""
    now = datetime.now(timezone.utc)
    lo = _parse_q_dt(start, now - timedelta(days=1))
    hi = _parse_q_dt(end, now + timedelta(days=60))
    rows = db.query(ExternalCalendarEvent).filter(
        ExternalCalendarEvent.user_id == current_user.id,
        ExternalCalendarEvent.status == "confirmed",
        ExternalCalendarEvent.end_time >= lo,
        ExternalCalendarEvent.start_time <= hi,
    ).order_by(ExternalCalendarEvent.start_time).all()
    return [
        {
            "id": r.id, "title": r.title, "all_day": r.all_day,
            "start_time": r.start_time.isoformat() if r.start_time else None,
            "end_time": r.end_time.isoformat() if r.end_time else None,
            "source": r.source,
        }
        for r in rows
    ]


@router.get("/conflicts")
def list_conflicts(
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(CalendarSyncConflict).filter(
        CalendarSyncConflict.user_id == current_user.id,
        CalendarSyncConflict.status == "open",
    ).order_by(CalendarSyncConflict.created_at.desc()).all()
    return [
        {
            "id": c.id, "type": c.conflict_type,
            "appointment_id": c.appointment_id, "google_event_id": c.google_event_id,
            "details": c.details or {},
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in rows
    ]


@router.post("/conflicts/{conflict_id}/resolve")
def resolve_conflict(
    conflict_id: int,
    resolution: str = Body(..., embed=True),
    db: Session = Depends(get_tenant_db),
    current_user: User = Depends(get_current_user),
    _module: bool = Depends(require_module(MODULE_GOOGLE_CALENDAR)),
):
    """Manually resolve a sync conflict.

    - ``keep_app``: re-assert our appointment on Google (recreate if it was
      deleted there, otherwise update it).
    - ``keep_google``: apply Google's version to our appointment (move it, or
      cancel it if the Google event was deleted).
    - ``dismiss``: just close the conflict (e.g. an accepted double-booking).
    """
    if resolution not in ("keep_app", "keep_google", "dismiss"):
        raise HTTPException(status_code=400, detail="Résolution invalide")
    c = db.query(CalendarSyncConflict).filter(
        CalendarSyncConflict.id == conflict_id,
        CalendarSyncConflict.user_id == current_user.id,
        CalendarSyncConflict.status == "open",
    ).first()
    if not c:
        raise HTTPException(status_code=404, detail="Conflit introuvable")

    appt = (
        db.query(Appointment).filter(Appointment.id == c.appointment_id).first()
        if c.appointment_id else None
    )

    if resolution == "keep_app" and appt:
        acc = db.query(GoogleCalendarAccount).filter(
            GoogleCalendarAccount.user_id == current_user.id,
            GoogleCalendarAccount.is_active == True,
        ).first()
        if acc:
            client = google_sync.make_client(db, acc)
            cli = db.query(Client).filter(Client.id == appt.client_id).first()
            animal = db.query(Animal).filter(Animal.id == appt.animal_id).first() if appt.animal_id else None
            payload = google_sync._event_payload(appt, google_sync._summary(appt, cli, animal))
            try:
                if c.conflict_type == "deleted_on_google" or not appt.google_event_id:
                    ev = client.insert_event(payload)
                    appt.google_event_id = ev.get("id")
                else:
                    client.update_event(appt.google_event_id, payload)
            except gcal.GoogleCalendarError as exc:
                logger.warning("Google push failed for appointment %s: %s", appt.id, exc)
                raise HTTPException(status_code=502, detail="Échec de la synchronisation Google.")

    elif resolution == "keep_google" and appt:
        if c.conflict_type == "deleted_on_google":
            appt.status = AppointmentStatus.CANCELLED
            appt.google_event_id = None
        elif c.conflict_type == "modified_on_google" and (c.details or {}).get("google"):
            g = c.details["google"]
            if g.get("start"):
                appt.start_time = datetime.fromisoformat(g["start"])
            if g.get("end"):
                appt.end_time = datetime.fromisoformat(g["end"])

    c.status = "resolved"
    c.resolution = resolution
    c.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "status": "resolved", "resolution": resolution}
