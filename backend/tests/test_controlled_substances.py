"""Tests for controlled substances register."""


def _setup(client, auth_headers):
    """Create a controlled substance product."""
    p = client.post("/api/v1/inventory/products", headers=auth_headers, json={
        "name": "Ketamine 100mg",
        "product_type": "medication",
        "selling_price": 25.00,
        "vat_rate": 20.00,
        "is_controlled_substance": True,
    })
    return p.json()["id"]


def test_create_entry(client, auth_headers):
    """Creating a controlled substance register entry works."""
    product_id = _setup(client, auth_headers)
    response = client.post("/api/v1/controlled-substances/entries", headers=auth_headers, json={
        "product_id": product_id,
        "movement_type": "in",
        "quantity": 10,
        "lot_number": "LOT-2025-001",
        "reason": "Reception fournisseur",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["product_name"] == "Ketamine 100mg"
    assert float(data["remaining_stock"]) == 10.0
    assert data["lot_number"] == "LOT-2025-001"


def test_remaining_stock_calculation(client, auth_headers):
    """Remaining stock is computed correctly across entries."""
    product_id = _setup(client, auth_headers)

    # Entry 1: +10
    client.post("/api/v1/controlled-substances/entries", headers=auth_headers, json={
        "product_id": product_id, "movement_type": "in", "quantity": 10,
    })

    # Entry 2: -3
    r2 = client.post("/api/v1/controlled-substances/entries", headers=auth_headers, json={
        "product_id": product_id, "movement_type": "prescription", "quantity": 3,
        "patient_owner_name": "M. Martin",
    })
    assert r2.status_code == 201
    assert float(r2.json()["remaining_stock"]) == 7.0

    # Entry 3: -2
    r3 = client.post("/api/v1/controlled-substances/entries", headers=auth_headers, json={
        "product_id": product_id, "movement_type": "out", "quantity": 2,
    })
    assert float(r3.json()["remaining_stock"]) == 5.0


def test_list_register(client, auth_headers):
    """Listing the register returns entries."""
    product_id = _setup(client, auth_headers)
    client.post("/api/v1/controlled-substances/entries", headers=auth_headers, json={
        "product_id": product_id, "movement_type": "in", "quantity": 5,
    })
    client.post("/api/v1/controlled-substances/entries", headers=auth_headers, json={
        "product_id": product_id, "movement_type": "out", "quantity": 2,
    })
    response = client.get("/api/v1/controlled-substances/register", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_register_filter_by_product(client, auth_headers):
    """Filtering by product_id returns only that product's entries."""
    pid1 = _setup(client, auth_headers)
    p2 = client.post("/api/v1/inventory/products", headers=auth_headers, json={
        "name": "Morphine 10mg", "product_type": "medication",
        "selling_price": 30.00, "vat_rate": 20.00, "is_controlled_substance": True,
    })
    pid2 = p2.json()["id"]

    client.post("/api/v1/controlled-substances/entries", headers=auth_headers, json={
        "product_id": pid1, "movement_type": "in", "quantity": 5,
    })
    client.post("/api/v1/controlled-substances/entries", headers=auth_headers, json={
        "product_id": pid2, "movement_type": "in", "quantity": 3,
    })

    response = client.get(f"/api/v1/controlled-substances/register?product_id={pid1}", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["product_name"] == "Ketamine 100mg"


def test_non_controlled_product_rejected(client, auth_headers):
    """Creating an entry for a non-controlled product should fail."""
    p = client.post("/api/v1/inventory/products", headers=auth_headers, json={
        "name": "Paracetamol 500mg", "product_type": "medication",
        "selling_price": 5.00, "vat_rate": 20.00,
        "is_controlled_substance": False,
    })
    product_id = p.json()["id"]
    response = client.post("/api/v1/controlled-substances/entries", headers=auth_headers, json={
        "product_id": product_id, "movement_type": "in", "quantity": 10,
    })
    assert response.status_code == 400


def test_entry_with_animal_shows_names(client, auth_headers):
    """Entry with patient_animal_id includes animal and client names."""
    product_id = _setup(client, auth_headers)

    # Stock in first
    client.post("/api/v1/controlled-substances/entries", headers=auth_headers, json={
        "product_id": product_id, "movement_type": "in", "quantity": 50,
    })

    # Create client + animal
    c = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Marie", "last_name": "Martin",
    })
    client_id = c.json()["id"]
    a = client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": client_id, "name": "Rex", "species": "dog",
    })
    animal_id = a.json()["id"]

    # Prescription entry with animal
    r = client.post("/api/v1/controlled-substances/entries", headers=auth_headers, json={
        "product_id": product_id,
        "movement_type": "prescription",
        "quantity": 2,
        "patient_animal_id": animal_id,
        "dosage": "0.5 mg/kg",
        "total_delivered": 3.5,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["patient_animal_name"] == "Rex"
    assert data["patient_client_name"] == "Martin Marie"
    assert data["dosage"] == "0.5 mg/kg"
    assert float(data["total_delivered"]) == 3.5


def test_export_register(client, auth_headers):
    """CSV export returns data with correct content type."""
    product_id = _setup(client, auth_headers)
    client.post("/api/v1/controlled-substances/entries", headers=auth_headers, json={
        "product_id": product_id, "movement_type": "in", "quantity": 5,
    })
    response = client.get("/api/v1/controlled-substances/register/export", headers=auth_headers)
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    content = response.text
    assert "Ketamine 100mg" in content
    assert "Entree" in content or "Entr" in content
