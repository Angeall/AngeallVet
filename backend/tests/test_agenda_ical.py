"""iCal feed + the google_calendar module gate."""
from datetime import datetime, timezone, timedelta

import pytest

import app.core.licensing as lic
from app.core.config import settings
from app.core.ical import build_calendar, ICalEvent, _fold, _esc, _utc
from app.models.client import Client
from app.models.appointment import Appointment, AppointmentType, AppointmentStatus


# ─── iCal generator (unit) ───────────────────────────────────────────────────

def test_escaping_and_utc():
    assert _esc("a;b,c\\d\ne") == "a\\;b\\,c\\\\d\\ne"
    assert _utc(datetime(2026, 6, 30, 14, 0, 0, tzinfo=timezone.utc)) == "20260630T140000Z"
    # tz-aware non-UTC is converted
    tz2 = timezone(timedelta(hours=2))
    assert _utc(datetime(2026, 6, 30, 16, 0, 0, tzinfo=tz2)) == "20260630T140000Z"


def test_long_line_is_folded():
    folded = _fold("SUMMARY:" + "x" * 200)
    assert all(len(seg.encode("utf-8")) <= 75 for seg in folded.split("\r\n "))


def test_build_calendar_structure():
    ev = ICalEvent(
        uid="appointment-1@angeallvet",
        start=datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc),
        end=datetime(2026, 7, 1, 9, 30, tzinfo=timezone.utc),
        summary="Consultation — Rex",
        status="TENTATIVE",
    )
    out = build_calendar("Cabinet", [ev], now=datetime(2026, 6, 30, tzinfo=timezone.utc))
    assert out.startswith("BEGIN:VCALENDAR\r\n")
    assert out.strip().endswith("END:VCALENDAR")
    assert "BEGIN:VEVENT\r\n" in out
    assert "UID:appointment-1@angeallvet" in out
    assert "DTSTART:20260701T090000Z" in out
    assert "STATUS:TENTATIVE" in out


# ─── Feed + module gate (HTTP) ───────────────────────────────────────────────

@pytest.fixture
def set_modules(monkeypatch):
    priv, pub = lic.generate_keypair()
    monkeypatch.setattr(settings, "LICENSE_PUBLIC_KEY", pub)

    def _set(modules):
        token = lic.sign_license(priv, modules) if modules else ""
        monkeypatch.setattr(settings, "LICENSE", token)

    return _set


def _appointment_for(db, vet, *, token="vet-feed-token-123"):
    client = Client(first_name="Jean", last_name="Dupont")
    db.add(client)
    db.flush()
    db.add(Appointment(
        client_id=client.id,
        veterinarian_id=vet.id,
        appointment_type=AppointmentType.CONSULTATION,
        status=AppointmentStatus.CONFIRMED,
        start_time=datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 7, 1, 9, 30, tzinfo=timezone.utc),
        reason="Vaccination annuelle",
    ))
    vet.ical_token = token
    db.commit()
    return token


def test_feed_serves_vet_appointments(client, db, vet_user):
    token = _appointment_for(db, vet_user)
    r = client.get(f"/api/v1/agenda/ical/{token}.ics")
    assert r.status_code == 200
    assert "text/calendar" in r.headers["content-type"]
    assert r.content.startswith(b"BEGIN:VCALENDAR")
    assert b"BEGIN:VEVENT" in r.content
    assert b"Consultation" in r.content
    assert b"Dupont" in r.content


def test_feed_unknown_token_404(client, db, vet_user):
    _appointment_for(db, vet_user)
    assert client.get("/api/v1/agenda/ical/nope.ics").status_code == 404


def test_feed_blocked_without_module(client, db, vet_user, set_modules):
    token = _appointment_for(db, vet_user)
    set_modules([])  # google_calendar not unlocked
    assert client.get(f"/api/v1/agenda/ical/{token}.ics").status_code == 403


def test_enable_requires_module(client, vet_headers, set_modules):
    set_modules([])
    assert client.post("/api/v1/agenda/ical/enable", headers=vet_headers).status_code == 403


def test_enable_returns_feed_and_google_links(client, vet_headers, set_modules):
    set_modules(["google_calendar"])
    r = client.post("/api/v1/agenda/ical/enable", headers=vet_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["feed_url"].endswith(".ics")
    assert body["webcal_url"].startswith("webcal://")
    assert "calendar.google.com" in body["google_url"]


def test_rotate_changes_token(client, vet_headers, set_modules):
    set_modules(["google_calendar"])
    first = client.post("/api/v1/agenda/ical/enable", headers=vet_headers).json()["feed_url"]
    second = client.post("/api/v1/agenda/ical/rotate", headers=vet_headers).json()["feed_url"]
    assert first != second
