"""Tests for the Invoice Ninja integration (HTTP calls mocked)."""

import app.core.invoice_ninja as inj_mod
from app.models.settings import ClinicSettings
from app.models.billing import Invoice
from app.models.client import Client


class _FakeResp:
    def __init__(self, status_code=200, json_data=None, content=b""):
        self.status_code = status_code
        self._json = json_data or {}
        self.content = content
        self.text = ""

    def json(self):
        return self._json


def _fake_request(method, url, **kwargs):
    if url.endswith("/clients") and method == "POST":
        return _FakeResp(json_data={"data": {"id": "CL-1"}})
    if url.endswith("/invoices") and method == "POST":
        return _FakeResp(json_data={"data": {"id": "INV-1"}})
    if url.endswith("/invoices/bulk") and method == "POST":
        return _FakeResp(json_data={"data": []})
    if url.endswith("/download") and method == "GET":
        return _FakeResp(content=b"%PDF-1.4 fake")
    return _FakeResp(status_code=404, json_data={})


def _make_invoice(client, auth_headers, vat_number=None):
    c = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Jean", "last_name": "Dupont", "vat_number": vat_number,
    })
    client_id = c.json()["id"]
    inv = client.post("/api/v1/billing/invoices", headers=auth_headers, json={
        "client_id": client_id,
        "lines": [{"description": "Consultation", "quantity": 1, "unit_price": 50, "vat_rate": 21}],
    })
    return client_id, inv.json()["id"]


def _configure(db):
    db.add(ClinicSettings(invoice_ninja_url="https://in.test", invoice_ninja_token="tok"))
    db.commit()


def test_send_requires_config(client, auth_headers):
    _, invoice_id = _make_invoice(client, auth_headers)
    r = client.post(f"/api/v1/billing/invoices/{invoice_id}/send", headers=auth_headers)
    assert r.status_code == 400


def test_send_pushes_and_stores_ids(client, db, auth_headers, monkeypatch):
    _configure(db)
    monkeypatch.setattr(inj_mod.httpx, "request", _fake_request)

    client_id, invoice_id = _make_invoice(client, auth_headers, vat_number="BE0123456789")
    r = client.post(f"/api/v1/billing/invoices/{invoice_id}/send", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["invoice_ninja_invoice_id"] == "INV-1"
    assert body["channel"] == "peppol"  # has a VAT number -> B2B Peppol

    assert db.query(Invoice).filter_by(id=invoice_id).first().invoice_ninja_invoice_id == "INV-1"
    assert db.query(Client).filter_by(id=client_id).first().invoice_ninja_client_id == "CL-1"


def test_send_b2c_channel_is_email(client, db, auth_headers, monkeypatch):
    _configure(db)
    monkeypatch.setattr(inj_mod.httpx, "request", _fake_request)
    _, invoice_id = _make_invoice(client, auth_headers)  # no VAT number
    r = client.post(f"/api/v1/billing/invoices/{invoice_id}/send", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["channel"] == "email"


def test_pdf_proxy(client, db, auth_headers, monkeypatch):
    _configure(db)
    monkeypatch.setattr(inj_mod.httpx, "request", _fake_request)
    _, invoice_id = _make_invoice(client, auth_headers)
    # Before any Invoice Ninja push, the free local PDF is served (not a 400).
    r0 = client.get(f"/api/v1/billing/invoices/{invoice_id}/pdf", headers=auth_headers)
    assert r0.status_code == 200
    assert r0.content.startswith(b"%PDF")
    assert b"fake" not in r0.content  # locally rendered, not the IN proxy
    # After pushing, the compliant Invoice Ninja PDF is proxied instead.
    client.post(f"/api/v1/billing/invoices/{invoice_id}/send", headers=auth_headers)
    r = client.get(f"/api/v1/billing/invoices/{invoice_id}/pdf", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert b"fake" in r.content  # the Invoice Ninja-proxied PDF
