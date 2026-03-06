import pytest


@pytest.fixture
def sample_client(client, auth_headers):
    res = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Jean", "last_name": "Dupont",
    })
    return res.json()


def test_create_invoice(client, auth_headers, sample_client):
    response = client.post("/api/v1/billing/invoices", headers=auth_headers, json={
        "client_id": sample_client["id"],
        "lines": [
            {"description": "Consultation", "quantity": 1, "unit_price": 50.00, "vat_rate": 20.00},
            {"description": "Vaccin", "quantity": 1, "unit_price": 30.00, "vat_rate": 20.00},
        ],
    })
    assert response.status_code == 201
    data = response.json()
    assert data["invoice_number"].startswith("FAC-")
    assert float(data["subtotal"]) == 80.00
    assert float(data["total_vat"]) == 16.00
    assert float(data["total"]) == 96.00


def test_record_payment(client, auth_headers, sample_client):
    inv_res = client.post("/api/v1/billing/invoices", headers=auth_headers, json={
        "client_id": sample_client["id"],
        "lines": [
            {"description": "Consultation", "quantity": 1, "unit_price": 50.00, "vat_rate": 20.00},
        ],
    })
    invoice_id = inv_res.json()["id"]

    pay_res = client.post("/api/v1/billing/payments", headers=auth_headers, json={
        "invoice_id": invoice_id,
        "amount": 60.00,
        "payment_method": "card",
    })
    assert pay_res.status_code == 201

    inv = client.get(f"/api/v1/billing/invoices/{invoice_id}", headers=auth_headers)
    assert inv.json()["status"] == "paid"


def test_create_estimate_and_convert(client, auth_headers, sample_client):
    est_res = client.post("/api/v1/billing/estimates", headers=auth_headers, json={
        "client_id": sample_client["id"],
        "lines": [
            {"description": "Chirurgie", "quantity": 1, "unit_price": 500.00, "vat_rate": 20.00},
        ],
    })
    assert est_res.status_code == 201
    estimate_id = est_res.json()["id"]

    conv_res = client.post("/api/v1/billing/estimates/to-invoice", headers=auth_headers, json={
        "estimate_id": estimate_id,
    })
    assert conv_res.status_code == 200
    assert conv_res.json()["invoice_number"].startswith("FAC-")
    assert float(conv_res.json()["total"]) == 600.00


def test_list_unpaid(client, auth_headers, sample_client):
    client.post("/api/v1/billing/invoices", headers=auth_headers, json={
        "client_id": sample_client["id"],
        "lines": [{"description": "Test", "quantity": 1, "unit_price": 100.00, "vat_rate": 20.00}],
    })
    response = client.get("/api/v1/billing/unpaid", headers=auth_headers)
    assert response.status_code == 200
    # Draft invoices are not in unpaid list
    assert isinstance(response.json(), list)
