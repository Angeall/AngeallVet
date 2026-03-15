"""Tests for treatment_location on MedicalRecordProduct (onsite vs home)."""


def _setup(client, auth_headers):
    """Create client, animal, and two products for testing."""
    c = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Luc", "last_name": "Dupont",
    })
    client_id = c.json()["id"]
    a = client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": client_id, "name": "Rex", "species": "dog",
    })
    animal_id = a.json()["id"]
    p1 = client.post("/api/v1/inventory/products", headers=auth_headers, json={
        "name": "Injection anti-douleur",
        "product_type": "service",
        "selling_price": 25.00,
        "vat_rate": 20.00,
    })
    p2 = client.post("/api/v1/inventory/products", headers=auth_headers, json={
        "name": "Metacam 1.5mg/ml",
        "product_type": "medication",
        "selling_price": 18.00,
        "vat_rate": 20.00,
    })
    return client_id, animal_id, p1.json()["id"], p2.json()["id"]


def test_create_record_with_onsite_products(client, auth_headers):
    """Medical record with onsite_treatment_products saves treatment_location=onsite."""
    _, animal_id, onsite_pid, _ = _setup(client, auth_headers)
    response = client.post("/api/v1/medical/records", headers=auth_headers, json={
        "animal_id": animal_id,
        "record_type": "consultation",
        "plan": "Injection anti-douleur sur place",
        "onsite_treatment_products": [
            {"product_id": onsite_pid, "quantity": 1},
        ],
    })
    assert response.status_code == 201
    data = response.json()
    # onsite products appear in home_treatment_products response list
    assert len(data["home_treatment_products"]) == 1
    prod = data["home_treatment_products"][0]
    assert prod["product_id"] == onsite_pid
    assert prod["treatment_location"] == "onsite"


def test_create_record_with_both_products(client, auth_headers):
    """Record with both onsite and home products; invoice includes all."""
    client_id, animal_id, onsite_pid, home_pid = _setup(client, auth_headers)
    rec = client.post("/api/v1/medical/records", headers=auth_headers, json={
        "animal_id": animal_id,
        "record_type": "consultation",
        "plan": "Injection sur place",
        "home_treatment": "Metacam 3 jours",
        "onsite_treatment_products": [
            {"product_id": onsite_pid, "quantity": 1},
        ],
        "home_treatment_products": [
            {"product_id": home_pid, "quantity": 3},
        ],
    })
    assert rec.status_code == 201
    data = rec.json()
    products = data["home_treatment_products"]
    assert len(products) == 2
    locations = {p["treatment_location"] for p in products}
    assert locations == {"onsite", "home"}

    # Create invoice — should include both onsite and home products
    record_id = data["id"]
    inv = client.post(f"/api/v1/medical/records/{record_id}/create-invoice", headers=auth_headers)
    assert inv.status_code == 201
    invoice = inv.json()
    assert invoice["status"] == "draft"
    # 1 * 25.00 (onsite) + 3 * 18.00 (home) = 79.00
    assert float(invoice["subtotal"]) == 79.00


def test_create_record_backward_compat(client, auth_headers):
    """Old-style request without onsite_treatment_products still works."""
    _, animal_id, _, home_pid = _setup(client, auth_headers)
    response = client.post("/api/v1/medical/records", headers=auth_headers, json={
        "animal_id": animal_id,
        "record_type": "consultation",
        "home_treatment_products": [
            {"product_id": home_pid, "quantity": 2},
        ],
    })
    assert response.status_code == 201
    data = response.json()
    assert len(data["home_treatment_products"]) == 1
    assert data["home_treatment_products"][0]["treatment_location"] == "home"
