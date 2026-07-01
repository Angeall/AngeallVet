"""Cash register closing + accounting export (the `accounting` module)."""
import pytest

import app.core.licensing as lic
from app.core.config import settings


def _client(client, auth_headers):
    return client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Jean", "last_name": "Dupont",
    }).json()["id"]


def _invoice(client, auth_headers, cid, unit_price=100, vat_rate=21):
    return client.post("/api/v1/billing/invoices", headers=auth_headers, json={
        "client_id": cid,
        "lines": [{"description": "Consultation", "quantity": 1, "unit_price": unit_price, "vat_rate": vat_rate}],
    }).json()


def _pay(client, auth_headers, invoice_id, amount, method="cash"):
    return client.post("/api/v1/billing/payments", headers=auth_headers, json={
        "invoice_id": invoice_id, "amount": amount, "payment_method": method,
    })


@pytest.fixture
def set_modules(monkeypatch):
    priv, pub = lic.generate_keypair()
    monkeypatch.setattr(settings, "LICENSE_PUBLIC_KEY", pub)

    def _set(modules):
        monkeypatch.setattr(settings, "LICENSE", lic.sign_license(priv, modules) if modules else "")
    return _set


def test_cash_day_aggregates_payments(client, auth_headers):
    cid = _client(client, auth_headers)
    inv = _invoice(client, auth_headers, cid, unit_price=100)
    _pay(client, auth_headers, inv["id"], 60, "cash")
    _pay(client, auth_headers, inv["id"], 40, "card")
    r = client.get("/api/v1/accounting/cash/day", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["totals_by_method"] == {"cash": 60.0, "card": 40.0}
    assert body["total"] == 100.0
    assert body["cash_payments"] == 60.0
    assert body["closed"] is False


def test_close_computes_discrepancy_and_locks_day(client, auth_headers):
    cid = _client(client, auth_headers)
    inv = _invoice(client, auth_headers, cid, unit_price=100)
    _pay(client, auth_headers, inv["id"], 60, "cash")
    # opening fund 50 + cash takings 60 = 110 expected; counted 105 -> -5
    r = client.post("/api/v1/accounting/cash/close", headers=auth_headers,
                    json={"opening_amount": 50, "counted_amount": 105})
    assert r.status_code == 200
    c = r.json()
    assert c["expected_amount"] == 110.0
    assert c["discrepancy"] == -5.0
    assert c["total_amount"] == 60.0

    # The day is now locked: no further payment, no second close.
    assert _pay(client, auth_headers, inv["id"], 10, "cash").status_code == 403
    assert client.post("/api/v1/accounting/cash/close", headers=auth_headers,
                       json={"opening_amount": 0, "counted_amount": 0}).status_code == 409


def test_cash_movements_affect_expected(client, auth_headers):
    cid = _client(client, auth_headers)
    inv = _invoice(client, auth_headers, cid, unit_price=100)
    _pay(client, auth_headers, inv["id"], 80, "cash")
    client.post("/api/v1/accounting/cash/movements", headers=auth_headers,
                json={"direction": "out", "amount": 30, "reason": "Versement banque"})
    day = client.get("/api/v1/accounting/cash/day", headers=auth_headers).json()
    assert day["cash_out"] == 30.0
    assert day["cash_movement_net"] == 50.0  # 80 cash - 30 out
    # expected = opening 0 + 80 - 30 = 50
    c = client.post("/api/v1/accounting/cash/close", headers=auth_headers,
                    json={"opening_amount": 0, "counted_amount": 50}).json()
    assert c["expected_amount"] == 50.0
    assert c["discrepancy"] == 0.0


def test_export_journal_xlsx(client, auth_headers):
    from datetime import date
    cid = _client(client, auth_headers)
    inv = _invoice(client, auth_headers, cid, unit_price=100, vat_rate=21)
    _pay(client, auth_headers, inv["id"], 121, "cash")
    today = date.today().isoformat()
    r = client.get("/api/v1/accounting/export/journal", headers=auth_headers,
                   params={"date_from": today, "date_to": today})
    assert r.status_code == 200
    assert r.content[:2] == b"PK"  # xlsx is a zip


def test_export_fec(client, auth_headers):
    from datetime import date
    cid = _client(client, auth_headers)
    inv = _invoice(client, auth_headers, cid, unit_price=100, vat_rate=21)
    _pay(client, auth_headers, inv["id"], 121, "cash")
    today = date.today().isoformat()
    r = client.get("/api/v1/accounting/export/fec", headers=auth_headers,
                   params={"date_from": today, "date_to": today})
    assert r.status_code == 200
    text = r.text
    assert text.startswith("JournalCode\t")
    assert "\tVentes\t" in text       # a sales entry
    assert "Caisse" in text           # a cash payment entry
    assert "121,00" in text           # FEC decimal comma


def test_accounting_gated_by_module(client, auth_headers, set_modules):
    set_modules([])  # no accounting module
    assert client.get("/api/v1/accounting/cash/day", headers=auth_headers).status_code == 403
