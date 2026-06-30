"""The free local invoice / quote PDF (default tier, no Invoice Ninja)."""
from app.models.settings import ClinicSettings


def _client_id(client, auth_headers):
    return client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Marie", "last_name": "Curie",
        "address": "1 rue de la Science", "postal_code": "1000", "city": "Bruxelles",
    }).json()["id"]


def test_invoice_pdf_renders(client, db, auth_headers):
    db.add(ClinicSettings(clinic_name="Clinique des Acacias", city="Bruxelles", vat_number="BE0123456789"))
    db.commit()
    cid = _client_id(client, auth_headers)
    inv = client.post("/api/v1/billing/invoices", headers=auth_headers, json={
        "client_id": cid,
        "lines": [
            {"description": "Consultation", "quantity": 1, "unit_price": 45, "vat_rate": 21},
            {"description": "Vaccin", "quantity": 2, "unit_price": 20, "vat_rate": 21},
        ],
    }).json()
    r = client.get(f"/api/v1/billing/invoices/{inv['id']}/pdf", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert len(r.content) > 800


def test_invoice_pdf_without_clinic_settings(client, auth_headers):
    """A clinic that hasn't filled its settings still gets a valid PDF."""
    cid = _client_id(client, auth_headers)
    inv = client.post("/api/v1/billing/invoices", headers=auth_headers, json={
        "client_id": cid,
        "lines": [{"description": "Consultation", "quantity": 1, "unit_price": 45, "vat_rate": 21}],
    }).json()
    r = client.get(f"/api/v1/billing/invoices/{inv['id']}/pdf", headers=auth_headers)
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF")


def test_estimate_pdf_renders(client, auth_headers):
    cid = _client_id(client, auth_headers)
    est = client.post("/api/v1/billing/estimates", headers=auth_headers, json={
        "client_id": cid,
        "lines": [{"description": "Détartrage", "quantity": 1, "unit_price": 120, "vat_rate": 21}],
    }).json()
    r = client.get(f"/api/v1/billing/estimates/{est['id']}/pdf", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
