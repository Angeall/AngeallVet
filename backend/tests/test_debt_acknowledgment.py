"""Tests for debt acknowledgment endpoint."""


def _setup_invoice(client, auth_headers, paid=False):
    """Create a client with an unpaid invoice."""
    c = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Jean", "last_name": "Dupont",
        "address": "12 Rue de la Paix", "city": "Paris", "postal_code": "75001",
    })
    client_id = c.json()["id"]

    # Create clinic settings
    client.put("/api/v1/settings/clinic", headers=auth_headers, json={
        "clinic_name": "Clinique AngeallVet",
        "address": "5 Avenue des Animaux",
        "city": "Lyon",
        "postal_code": "69001",
        "siret": "12345678901234",
    })

    inv = client.post("/api/v1/billing/invoices", headers=auth_headers, json={
        "client_id": client_id,
        "lines": [{"description": "Consultation", "quantity": 1, "unit_price": 50.00, "vat_rate": 20.00}],
    })
    invoice_id = inv.json()["id"]

    if paid:
        client.post("/api/v1/billing/payments", headers=auth_headers, json={
            "invoice_id": invoice_id, "amount": 60.00, "payment_method": "cash",
        })

    return invoice_id, client_id


def test_debt_acknowledgment_endpoint(client, auth_headers):
    """GET /billing/invoices/{id}/debt-acknowledgment returns correct data."""
    invoice_id, _ = _setup_invoice(client, auth_headers)
    response = client.get(f"/api/v1/billing/invoices/{invoice_id}/debt-acknowledgment", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["clinic"]["clinic_name"] == "Clinique AngeallVet"
    assert data["client"]["last_name"] == "Dupont"
    assert data["invoice"]["invoice_number"].startswith("FAC-")
    assert data["invoice"]["remaining"] == 60.0  # 50 * 1.2 = 60 TTC

    # Verify invoice lines are included (top-level key)
    assert "lines" in data
    lines = data["lines"]
    assert len(lines) == 1
    assert lines[0]["description"] == "Consultation"
    assert lines[0]["unit_price"] == 50.0
    assert lines[0]["quantity"] == 1.0


def test_debt_acknowledgment_paid_invoice_error(client, auth_headers):
    """Debt acknowledgment should fail for a fully paid invoice."""
    invoice_id, _ = _setup_invoice(client, auth_headers, paid=True)
    response = client.get(f"/api/v1/billing/invoices/{invoice_id}/debt-acknowledgment", headers=auth_headers)
    assert response.status_code == 400


def test_debt_acknowledgment_not_found(client, auth_headers):
    """Debt acknowledgment should return 404 for non-existent invoice."""
    response = client.get("/api/v1/billing/invoices/9999/debt-acknowledgment", headers=auth_headers)
    assert response.status_code == 404
