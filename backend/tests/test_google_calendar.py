"""Two-way Google Calendar sync: OAuth, engine (push/pull/conflicts), resolution."""
from datetime import datetime, timedelta, timezone

import pytest

import app.core.licensing as lic
import app.core.google_sync as gsync
import app.core.google_calendar as gcal
from app.core.config import settings
from app.core.security import create_app_token
from app.core.tenancy import derive_tenant_secret
from app.models.client import Client
from app.models.appointment import Appointment, AppointmentType, AppointmentStatus
from app.models.user import Notification
from app.models.google_calendar import (
    GoogleCalendarAccount, ExternalCalendarEvent, CalendarSyncConflict,
)


def _utc(dt):
    # Match production (_to_utc): SQLite drops tzinfo on round-trip, so a naive
    # value is treated as UTC rather than as local time.
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


NOW = datetime.now(timezone.utc)


# ─── Fakes / fixtures ────────────────────────────────────────────────────────

class FakeClient:
    """Stand-in for GoogleCalendarClient — records writes, returns canned reads."""
    def __init__(self, events=None, next_token="tok-2"):
        self.events = events or []
        self.next_token = next_token
        self.inserted, self.updated, self.deleted = [], [], []
        self._seq = 0

    def list_events(self, *, sync_token=None, time_min=None):
        return self.events, self.next_token

    def insert_event(self, payload):
        self._seq += 1
        gid = f"new-{self._seq}"
        self.inserted.append((gid, payload))
        return {"id": gid}

    def update_event(self, event_id, payload):
        self.updated.append((event_id, payload))
        return {"id": event_id}

    def delete_event(self, event_id):
        self.deleted.append(event_id)


def _account(db, user):
    acc = GoogleCalendarAccount(
        user_id=user.id, google_email="vet@gmail.com",
        refresh_token="rt", access_token="at",
        token_expiry=NOW + timedelta(hours=1), is_active=True,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


def _appt(db, vet, *, start, minutes=30, status=AppointmentStatus.CONFIRMED, google_event_id=None):
    client = Client(first_name="Jean", last_name="Dupont")
    db.add(client)
    db.flush()
    appt = Appointment(
        client_id=client.id, veterinarian_id=vet.id,
        appointment_type=AppointmentType.CONSULTATION, status=status,
        start_time=start, end_time=start + timedelta(minutes=minutes),
        google_event_id=google_event_id,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


# ─── Engine: push ────────────────────────────────────────────────────────────

def test_push_creates_event_and_stores_id(db, vet_user):
    acc = _account(db, vet_user)
    appt = _appt(db, vet_user, start=NOW + timedelta(days=1))
    fake = FakeClient()
    counts = gsync.push_appointments(db, acc, fake)
    assert counts["created"] == 1
    assert len(fake.inserted) == 1
    db.refresh(appt)
    assert appt.google_event_id == "new-1"


def test_push_deletes_cancelled(db, vet_user):
    acc = _account(db, vet_user)
    appt = _appt(db, vet_user, start=NOW + timedelta(days=1),
                 status=AppointmentStatus.CANCELLED, google_event_id="g-1")
    fake = FakeClient()
    counts = gsync.push_appointments(db, acc, fake)
    assert counts["deleted"] == 1
    assert fake.deleted == ["g-1"]
    db.refresh(appt)
    assert appt.google_event_id is None


def test_push_skips_conflicted_appointment(db, vet_user):
    acc = _account(db, vet_user)
    appt = _appt(db, vet_user, start=NOW + timedelta(days=1))
    db.add(CalendarSyncConflict(user_id=vet_user.id, appointment_id=appt.id,
                                conflict_type="modified_on_google", status="open"))
    db.commit()
    fake = FakeClient()
    counts = gsync.push_appointments(db, acc, fake)
    assert counts["created"] == 0
    assert fake.inserted == []  # never overwrite a divergent appointment


# ─── Engine: pull ────────────────────────────────────────────────────────────

def test_pull_imports_external_event_as_block(db, vet_user):
    acc = _account(db, vet_user)
    start = NOW + timedelta(days=2)
    fake = FakeClient(events=[{
        "id": "ext-1", "status": "confirmed", "summary": "Dentiste",
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": (start + timedelta(hours=1)).isoformat()},
    }])
    counts = gsync.pull_changes(db, acc, fake)
    assert counts["imported"] == 1
    block = db.query(ExternalCalendarEvent).filter_by(external_id="ext-1").first()
    assert block and block.title == "Dentiste"
    db.refresh(acc)
    assert acc.sync_token == "tok-2"


def test_pull_flags_modified_event_as_conflict(db, vet_user):
    acc = _account(db, vet_user)
    appt = _appt(db, vet_user, start=NOW + timedelta(days=1), google_event_id="g-9")
    moved = _utc(appt.start_time) + timedelta(hours=2)
    fake = FakeClient(events=[{
        "id": "g-9", "status": "confirmed",
        "start": {"dateTime": moved.isoformat()},
        "end": {"dateTime": (moved + timedelta(minutes=30)).isoformat()},
        "extendedProperties": {"private": {"angeallvet_appointment_id": str(appt.id)}},
    }])
    counts = gsync.pull_changes(db, acc, fake)
    assert counts["conflicts"] == 1
    c = db.query(CalendarSyncConflict).filter_by(appointment_id=appt.id).first()
    assert c.conflict_type == "modified_on_google" and c.status == "open"
    # a notification was raised for the vet
    assert db.query(Notification).filter_by(user_id=vet_user.id).count() == 1


def test_pull_flags_deleted_event_as_conflict(db, vet_user):
    acc = _account(db, vet_user)
    appt = _appt(db, vet_user, start=NOW + timedelta(days=1), google_event_id="g-7")
    fake = FakeClient(events=[{
        "id": "g-7", "status": "cancelled",
        "extendedProperties": {"private": {"angeallvet_appointment_id": str(appt.id)}},
    }])
    counts = gsync.pull_changes(db, acc, fake)
    assert counts["conflicts"] == 1
    assert db.query(CalendarSyncConflict).filter_by(
        appointment_id=appt.id, conflict_type="deleted_on_google").count() == 1


def test_pull_is_idempotent_for_conflicts(db, vet_user):
    acc = _account(db, vet_user)
    appt = _appt(db, vet_user, start=NOW + timedelta(days=1), google_event_id="g-9")
    moved = _utc(appt.start_time) + timedelta(hours=2)
    ev = {
        "id": "g-9", "status": "confirmed",
        "start": {"dateTime": moved.isoformat()},
        "end": {"dateTime": (moved + timedelta(minutes=30)).isoformat()},
        "extendedProperties": {"private": {"angeallvet_appointment_id": str(appt.id)}},
    }
    gsync.pull_changes(db, acc, FakeClient(events=[ev]))
    gsync.pull_changes(db, acc, FakeClient(events=[ev]))  # second run
    assert db.query(CalendarSyncConflict).filter_by(appointment_id=appt.id).count() == 1


# ─── Engine: double-booking ──────────────────────────────────────────────────

def test_detect_double_booking(db, vet_user):
    acc = _account(db, vet_user)
    start = NOW + timedelta(days=1)
    _appt(db, vet_user, start=start, minutes=60)
    db.add(ExternalCalendarEvent(
        user_id=vet_user.id, source="google", external_id="ext-5", title="Perso",
        start_time=start + timedelta(minutes=30), end_time=start + timedelta(minutes=90),
        status="confirmed",
    ))
    db.commit()
    counts = gsync.detect_double_bookings(db, acc)
    assert counts["conflicts"] == 1
    assert db.query(CalendarSyncConflict).filter_by(
        user_id=vet_user.id, conflict_type="double_booking").count() == 1


# ─── OAuth + endpoints ───────────────────────────────────────────────────────

def _vet_state(vet_user):
    return create_app_token(
        str(vet_user.id), derive_tenant_secret(settings.DEFAULT_TENANT_SLUG),
        extra={"scope": "google_oauth"},
    )


def test_oauth_callback_stores_tokens(client, db, vet_user, monkeypatch):
    monkeypatch.setattr(gcal, "exchange_code",
                        lambda code: {"access_token": "AT", "refresh_token": "RT", "expires_in": 3600})
    r = client.get(
        "/api/v1/agenda/google/callback",
        params={"code": "abc", "state": _vet_state(vet_user)},
        follow_redirects=False,
    )
    assert r.status_code in (302, 307)
    assert "google=connected" in r.headers["location"]
    acc = db.query(GoogleCalendarAccount).filter_by(user_id=vet_user.id).first()
    assert acc and acc.refresh_token == "RT"


def test_oauth_callback_rejects_bad_state(client, db, vet_user):
    r = client.get(
        "/api/v1/agenda/google/callback",
        params={"code": "abc", "state": "not-a-valid-token"},
        follow_redirects=False,
    )
    assert "google=error" in r.headers["location"]
    assert db.query(GoogleCalendarAccount).count() == 0


def test_connect_requires_module(client, vet_headers, monkeypatch):
    priv, pub = lic.generate_keypair()
    monkeypatch.setattr(settings, "LICENSE_PUBLIC_KEY", pub)
    monkeypatch.setattr(settings, "LICENSE", "")  # no modules
    assert client.get("/api/v1/agenda/google/connect", headers=vet_headers).status_code == 403


def test_connect_returns_auth_url(client, vet_headers, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setattr(settings, "GOOGLE_REDIRECT_URI", "http://x/cb")
    r = client.get("/api/v1/agenda/google/connect", headers=vet_headers)
    assert r.status_code == 200
    assert "accounts.google.com" in r.json()["auth_url"]


def test_resolve_conflict_keep_google_moves_appointment(client, db, vet_user, vet_headers):
    appt = _appt(db, vet_user, start=NOW + timedelta(days=1), google_event_id="g-3")
    # Naive datetime so the SQLite round-trip preserves the exact wall clock.
    new_start = (datetime.now() + timedelta(days=1, hours=3)).replace(microsecond=0)
    c = CalendarSyncConflict(
        user_id=vet_user.id, appointment_id=appt.id, google_event_id="g-3",
        conflict_type="modified_on_google", status="open",
        details={"google": {"start": new_start.isoformat(),
                             "end": (new_start + timedelta(minutes=30)).isoformat()}},
    )
    db.add(c)
    db.commit()
    r = client.post(f"/api/v1/agenda/conflicts/{c.id}/resolve",
                    headers=vet_headers, json={"resolution": "keep_google"})
    assert r.status_code == 200
    db.refresh(appt)
    assert appt.start_time.replace(tzinfo=None) == new_start
    db.refresh(c)
    assert c.status == "resolved" and c.resolution == "keep_google"


def test_disconnect_removes_account(client, db, vet_user, vet_headers):
    _account(db, vet_user)
    db.add(ExternalCalendarEvent(user_id=vet_user.id, external_id="x", title="t",
                                 start_time=NOW, end_time=NOW + timedelta(hours=1)))
    db.commit()
    r = client.delete("/api/v1/agenda/google", headers=vet_headers)
    assert r.status_code == 204
    assert db.query(GoogleCalendarAccount).filter_by(user_id=vet_user.id).count() == 0
    assert db.query(ExternalCalendarEvent).filter_by(user_id=vet_user.id).count() == 0


def test_external_events_endpoint_lists_blocks(client, db, vet_user, vet_headers):
    start = NOW + timedelta(days=1)
    db.add(ExternalCalendarEvent(
        user_id=vet_user.id, source="google", external_id="ext-9", title="Congrès",
        start_time=start, end_time=start + timedelta(hours=2), status="confirmed",
    ))
    db.commit()
    r = client.get(
        "/api/v1/agenda/external-events", headers=vet_headers,
        params={"start": (NOW - timedelta(days=1)).isoformat(),
                "end": (NOW + timedelta(days=5)).isoformat()},
    )
    assert r.status_code == 200
    assert "Congrès" in [e["title"] for e in r.json()]
