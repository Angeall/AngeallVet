"""Server-side enforcement of paid modules — the real, un-bypassable lock.

These exercise the full HTTP path with a configured public key, so module access
is driven strictly by a signed license (no dev all-on).
"""
import pytest

import app.core.licensing as lic
from app.core.config import settings
import app.api.endpoints.communication as comm_mod
from app.models.settings import ClinicSettings


@pytest.fixture
def set_modules(monkeypatch):
    """Configure a public key; the returned setter chooses the unlocked modules."""
    priv, pub = lic.generate_keypair()
    monkeypatch.setattr(settings, "LICENSE_PUBLIC_KEY", pub)

    def _set(modules):
        token = lic.sign_license(priv, modules) if modules else ""
        monkeypatch.setattr(settings, "LICENSE", token)

    return _set


def _make_client(client, auth_headers, **extra):
    payload = {"first_name": "Jean", "last_name": "Dupont"}
    payload.update(extra)
    return client.post("/api/v1/clients", headers=auth_headers, json=payload).json()["id"]


def _make_invoice(client, auth_headers, client_id):
    return client.post("/api/v1/billing/invoices", headers=auth_headers, json={
        "client_id": client_id,
        "lines": [{"description": "Consultation", "quantity": 1, "unit_price": 50, "vat_rate": 21}],
    }).json()


def test_sms_blocked_without_module(client, auth_headers, set_modules, monkeypatch):
    set_modules([])  # free tier
    called = {"n": 0}
    monkeypatch.setattr(comm_mod, "send_sms", lambda *a, **k: called.__setitem__("n", 1))
    cid = _make_client(client, auth_headers, mobile="+32470000000")
    r = client.post("/api/v1/communications", headers=auth_headers, json={
        "client_id": cid, "channel": "sms", "body": "Rappel",
    })
    assert r.status_code == 403
    assert "SMS" in r.json()["detail"]
    assert called["n"] == 0  # the provider is never even reached


def test_sms_allowed_with_module(client, auth_headers, set_modules, monkeypatch):
    set_modules(["sms"])
    monkeypatch.setattr(comm_mod, "send_sms", lambda *a, **k: None)  # provider OK
    cid = _make_client(client, auth_headers, mobile="+32470000000")
    r = client.post("/api/v1/communications", headers=auth_headers, json={
        "client_id": cid, "channel": "sms", "body": "Rappel",
    })
    assert r.status_code == 201
    assert r.json()["status"] == "sent"


def test_email_is_free(client, auth_headers, set_modules, monkeypatch):
    set_modules([])  # nothing unlocked
    monkeypatch.setattr(comm_mod, "send_email", lambda *a, **k: None)
    cid = _make_client(client, auth_headers, email="eva@test.com")
    r = client.post("/api/v1/communications", headers=auth_headers, json={
        "client_id": cid, "channel": "email", "subject": "Bonjour", "body": "Test",
    })
    assert r.status_code == 201


def test_invoice_ninja_send_blocked_without_module(client, db, auth_headers, set_modules):
    set_modules([])
    db.add(ClinicSettings(invoice_ninja_url="https://in.test", invoice_ninja_token="tok"))
    db.commit()
    cid = _make_client(client, auth_headers)
    inv = _make_invoice(client, auth_headers, cid)
    r = client.post(f"/api/v1/billing/invoices/{inv['id']}/send", headers=auth_headers)
    assert r.status_code == 403
    assert "Facturation" in r.json()["detail"]


def test_invoice_pdf_is_free(client, auth_headers, set_modules):
    set_modules([])  # no invoice_ninja module
    cid = _make_client(client, auth_headers)
    inv = _make_invoice(client, auth_headers, cid)
    r = client.get(f"/api/v1/billing/invoices/{inv['id']}/pdf", headers=auth_headers)
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")


def test_modules_endpoint_reports_unlocked(client, auth_headers, set_modules):
    set_modules(["sms"])
    r = client.get("/api/v1/auth/modules", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["modules"] == ["sms"]
    assert "invoice_ninja" in body["available"]
    assert "google_calendar" in body["available"]
