"""Tests for consultation template CRUD endpoints."""


def _create_product(client, auth_headers, name="Metacam 1.5mg"):
    r = client.post("/api/v1/inventory/products", headers=auth_headers, json={
        "name": name, "product_type": "medication",
        "selling_price": 18.90, "vat_rate": 20.00,
    })
    assert r.status_code == 201
    return r.json()["id"]


def test_create_template(client, auth_headers):
    """POST /medical/templates creates a template."""
    r = client.post("/api/v1/medical/templates", headers=auth_headers, json={
        "name": "Consultation generale",
        "category": "general",
        "subjective": "Motif",
        "objective": "Examen clinique",
        "assessment": "RAS",
        "plan": "Suivi",
        "home_treatment": "Repos",
        "products": [],
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Consultation generale"
    assert data["home_treatment"] == "Repos"


def test_create_template_with_products(client, auth_headers):
    """POST /medical/templates with products saves them."""
    pid = _create_product(client, auth_headers)
    r = client.post("/api/v1/medical/templates", headers=auth_headers, json={
        "name": "Vaccination",
        "category": "vaccination",
        "products": [
            {"product_id": pid, "quantity": 1, "treatment_location": "onsite"},
        ],
    })
    assert r.status_code == 201
    data = r.json()
    assert len(data["products"]) == 1
    assert data["products"][0]["product_id"] == pid
    assert data["products"][0]["treatment_location"] == "onsite"


def test_get_template_detail(client, auth_headers):
    """GET /medical/templates/{id} returns template with products."""
    pid = _create_product(client, auth_headers)
    r = client.post("/api/v1/medical/templates", headers=auth_headers, json={
        "name": "Dermatologie",
        "products": [{"product_id": pid, "quantity": 2, "treatment_location": "home"}],
    })
    tid = r.json()["id"]
    detail = client.get(f"/api/v1/medical/templates/{tid}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["name"] == "Dermatologie"
    assert len(detail.json()["products"]) == 1


def test_update_template(client, auth_headers):
    """PUT /medical/templates/{id} updates template fields and products."""
    pid1 = _create_product(client, auth_headers, "Produit A")
    pid2 = _create_product(client, auth_headers, "Produit B")

    r = client.post("/api/v1/medical/templates", headers=auth_headers, json={
        "name": "Original",
        "products": [{"product_id": pid1, "quantity": 1, "treatment_location": "onsite"}],
    })
    tid = r.json()["id"]

    updated = client.put(f"/api/v1/medical/templates/{tid}", headers=auth_headers, json={
        "name": "Updated",
        "assessment": "Nouveau diagnostic",
        "products": [{"product_id": pid2, "quantity": 3, "treatment_location": "home"}],
    })
    assert updated.status_code == 200
    data = updated.json()
    assert data["name"] == "Updated"
    assert data["assessment"] == "Nouveau diagnostic"
    assert len(data["products"]) == 1
    assert data["products"][0]["product_id"] == pid2


def test_delete_template(client, auth_headers):
    """DELETE /medical/templates/{id} soft-deletes the template."""
    r = client.post("/api/v1/medical/templates", headers=auth_headers, json={
        "name": "A supprimer", "products": [],
    })
    tid = r.json()["id"]
    d = client.delete(f"/api/v1/medical/templates/{tid}", headers=auth_headers)
    assert d.status_code in (200, 204)

    # Listing should not return deleted template
    listing = client.get("/api/v1/medical/templates", headers=auth_headers)
    ids = [t["id"] for t in listing.json()]
    assert tid not in ids


def test_list_templates(client, auth_headers):
    """GET /medical/templates returns active templates."""
    client.post("/api/v1/medical/templates", headers=auth_headers, json={
        "name": "Template 1", "products": [],
    })
    client.post("/api/v1/medical/templates", headers=auth_headers, json={
        "name": "Template 2", "products": [],
    })
    listing = client.get("/api/v1/medical/templates", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) >= 2
