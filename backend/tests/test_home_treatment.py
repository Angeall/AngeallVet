"""Tests for home treatment products and invoice creation from medical records."""


def _setup(client, auth_headers):
    """Create client, animal, and a product for testing."""
    c = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Marie", "last_name": "Martin",
    })
    client_id = c.json()["id"]
    a = client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": client_id, "name": "Minou", "species": "cat",
    })
    animal_id = a.json()["id"]
    p = client.post("/api/v1/inventory/products", headers=auth_headers, json={
        "name": "Amoxicilline 250mg",
        "product_type": "medication",
        "selling_price": 15.50,
        "vat_rate": 20.00,
    })
    product_id = p.json()["id"]
    return client_id, animal_id, product_id


def test_create_record_with_home_treatment(client, auth_headers):
    """Medical record can include home treatment products."""
    _, animal_id, product_id = _setup(client, auth_headers)
    response = client.post("/api/v1/medical/records", headers=auth_headers, json={
        "animal_id": animal_id,
        "record_type": "consultation",
        "home_treatment": "Donner 1 comprime matin et soir pendant 5 jours",
        "home_treatment_products": [
            {"product_id": product_id, "quantity": 10},
        ],
    })
    assert response.status_code == 201
    data = response.json()
    assert len(data["home_treatment_products"]) == 1
    assert data["home_treatment_products"][0]["product_id"] == product_id
    assert float(data["home_treatment_products"][0]["quantity"]) == 10


def test_create_invoice_from_record(client, auth_headers):
    """POST /medical/records/{id}/create-invoice creates a draft invoice."""
    _, animal_id, product_id = _setup(client, auth_headers)
    rec = client.post("/api/v1/medical/records", headers=auth_headers, json={
        "animal_id": animal_id,
        "record_type": "consultation",
        "home_treatment_products": [
            {"product_id": product_id, "quantity": 2},
        ],
    })
    record_id = rec.json()["id"]

    response = client.post(f"/api/v1/medical/records/{record_id}/create-invoice", headers=auth_headers)
    assert response.status_code == 201
    invoice = response.json()
    assert invoice["status"] == "draft"
    assert float(invoice["subtotal"]) == 31.00  # 2 * 15.50


def test_create_invoice_no_products(client, auth_headers):
    """Creating invoice from a record with no home treatment products should fail."""
    c = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Test", "last_name": "Client",
    })
    a = client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": c.json()["id"], "name": "Fido", "species": "dog",
    })
    rec = client.post("/api/v1/medical/records", headers=auth_headers, json={
        "animal_id": a.json()["id"],
        "record_type": "consultation",
    })
    record_id = rec.json()["id"]

    response = client.post(f"/api/v1/medical/records/{record_id}/create-invoice", headers=auth_headers)
    assert response.status_code == 400
