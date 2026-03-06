import pytest


def test_create_product(client, auth_headers):
    response = client.post("/api/v1/inventory/products", headers=auth_headers, json={
        "name": "Amoxicilline 250mg",
        "product_type": "medication",
        "selling_price": 12.50,
        "vat_rate": 20.00,
        "unit": "comprimé",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Amoxicilline 250mg"
    assert data["reference"] is not None


def test_add_lot_and_stock(client, auth_headers):
    prod_res = client.post("/api/v1/inventory/products", headers=auth_headers, json={
        "name": "Test Med", "product_type": "medication", "selling_price": 10.00,
    })
    product_id = prod_res.json()["id"]

    lot_res = client.post(f"/api/v1/inventory/products/{product_id}/lots", headers=auth_headers, json={
        "lot_number": "LOT-2024-001",
        "expiry_date": "2026-12-31",
        "quantity": 100,
    })
    assert lot_res.status_code == 201

    # Check stock increased
    products = client.get("/api/v1/inventory/products", headers=auth_headers)
    prod = next(p for p in products.json() if p["id"] == product_id)
    assert float(prod["stock_quantity"]) == 100


def test_stock_movement_out(client, auth_headers):
    prod_res = client.post("/api/v1/inventory/products", headers=auth_headers, json={
        "name": "Test Med", "product_type": "medication", "selling_price": 10.00,
    })
    product_id = prod_res.json()["id"]

    # Add stock
    client.post(f"/api/v1/inventory/products/{product_id}/lots", headers=auth_headers, json={
        "lot_number": "LOT-001", "expiry_date": "2026-12-31", "quantity": 50,
    })

    # Remove stock
    mov_res = client.post("/api/v1/inventory/movements", headers=auth_headers, json={
        "product_id": product_id, "movement_type": "out", "quantity": 10, "reason": "Test",
    })
    assert mov_res.status_code == 201

    products = client.get("/api/v1/inventory/products", headers=auth_headers)
    prod = next(p for p in products.json() if p["id"] == product_id)
    assert float(prod["stock_quantity"]) == 40


def test_stock_alerts(client, auth_headers):
    client.post("/api/v1/inventory/products", headers=auth_headers, json={
        "name": "Low Stock Med",
        "product_type": "medication",
        "selling_price": 10.00,
        "stock_alert_threshold": 10,
    })
    response = client.get("/api/v1/inventory/alerts", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_create_supplier(client, auth_headers):
    response = client.post("/api/v1/inventory/suppliers", headers=auth_headers, json={
        "name": "Centravet",
        "contact_name": "Jean Fournisseur",
        "email": "contact@centravet.fr",
    })
    assert response.status_code == 201
    assert response.json()["name"] == "Centravet"
