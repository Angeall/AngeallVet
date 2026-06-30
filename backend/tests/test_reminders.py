"""Tests for real e-mail/SMS sending, the reminder run, and opt-out (providers mocked)."""

from datetime import datetime, timedelta

import app.api.endpoints.communication as comm_mod
import app.core.reminders as rem_mod
from app.models.client import Client
from app.models.animal import Animal
from app.models.medical import MedicalRecord
from app.models.communication import ReminderRule, ReminderLog


def test_send_email_success(client, auth_headers, monkeypatch):
    sent = []
    monkeypatch.setattr(comm_mod, "send_email", lambda *a, **k: sent.append((a, k)))
    c = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Jean", "last_name": "Dupont", "email": "jean@test.com",
    })
    cid = c.json()["id"]
    r = client.post("/api/v1/communications", headers=auth_headers, json={
        "client_id": cid, "channel": "email", "subject": "Bonjour", "body": "Test",
    })
    assert r.status_code == 201
    assert r.json()["status"] == "sent"
    assert len(sent) == 1


def test_send_email_failure_returns_502(client, auth_headers, monkeypatch):
    def boom(*a, **k):
        raise comm_mod.MailerError("smtp down")
    monkeypatch.setattr(comm_mod, "send_email", boom)
    c = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "A", "last_name": "B", "email": "a@b.com",
    })
    cid = c.json()["id"]
    r = client.post("/api/v1/communications", headers=auth_headers, json={
        "client_id": cid, "channel": "email", "body": "x",
    })
    assert r.status_code == 502


def test_send_email_without_address_fails(client, auth_headers, monkeypatch):
    monkeypatch.setattr(comm_mod, "send_email", lambda *a, **k: None)
    c = client.post("/api/v1/clients", headers=auth_headers, json={"first_name": "A", "last_name": "B"})
    cid = c.json()["id"]
    r = client.post("/api/v1/communications", headers=auth_headers, json={
        "client_id": cid, "channel": "email", "body": "x",
    })
    assert r.status_code == 502  # no e-mail on file


def test_unsubscribe_opts_out(client, db, auth_headers):
    c = client.post("/api/v1/clients", headers=auth_headers, json={"first_name": "A", "last_name": "B"})
    cid = c.json()["id"]
    cli = db.query(Client).filter_by(id=cid).first()
    cli.unsubscribe_token = "tok123"
    db.commit()

    r = client.get("/api/v1/communications/unsubscribe/tok123")  # no auth
    assert r.status_code == 200
    db.refresh(cli)
    assert cli.accepts_reminders is False


def _due_vaccine_setup(db, vet_id, email="jean@test.com"):
    cli = Client(first_name="Jean", last_name="Dupont", email=email)
    db.add(cli)
    db.flush()
    animal = Animal(client_id=cli.id, name="Rex", species="dog")
    db.add(animal)
    db.flush()
    rec = MedicalRecord(animal_id=animal.id, record_type="vaccination", veterinarian_id=vet_id)
    db.add(rec)
    db.flush()
    rec.created_at = datetime.utcnow() - timedelta(days=400)  # last vaccine > 1 year ago
    db.add(ReminderRule(name="Vaccin annuel", reminder_type="vaccine", channel="email", days_before=30, is_active=True))
    db.commit()
    return cli


def test_run_reminders_sends_and_dedupes(client, db, auth_headers, admin_user, monkeypatch):
    sent = []
    monkeypatch.setattr(rem_mod, "send_email", lambda *a, **k: sent.append(a))
    _due_vaccine_setup(db, admin_user.id)

    r = client.post("/api/v1/communications/reminders/run", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["sent"] == 1
    assert len(sent) == 1
    assert db.query(ReminderLog).count() == 1

    sent.clear()
    r2 = client.post("/api/v1/communications/reminders/run", headers=auth_headers)
    assert r2.json()["sent"] == 0  # already logged -> deduped
    assert len(sent) == 0


def test_run_reminders_respects_optout(client, db, auth_headers, admin_user, monkeypatch):
    sent = []
    monkeypatch.setattr(rem_mod, "send_email", lambda *a, **k: sent.append(a))
    cli = _due_vaccine_setup(db, admin_user.id, email="opt@test.com")
    cli.accepts_reminders = False
    db.commit()

    r = client.post("/api/v1/communications/reminders/run", headers=auth_headers)
    assert r.json()["sent"] == 0
    assert r.json()["skipped"] == 1
    assert len(sent) == 0
