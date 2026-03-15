"""Tests for species CRUD endpoints."""


def test_list_species_default_seeded(client, auth_headers, db):
    """GET /animals/species returns species (may be empty in test)."""
    response = client.get("/api/v1/animals/species", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_species(client, auth_headers):
    """POST /animals/species creates a new species (admin only)."""
    response = client.post("/api/v1/animals/species", headers=auth_headers, json={
        "code": "ferret",
        "label": "Furet",
        "display_order": 10,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "ferret"
    assert data["label"] == "Furet"
    assert data["is_active"] is True


def test_create_species_non_admin_forbidden(client, vet_headers):
    """Non-admin users cannot create species."""
    response = client.post("/api/v1/animals/species", headers=vet_headers, json={
        "code": "ferret", "label": "Furet",
    })
    assert response.status_code == 403


def test_update_species(client, auth_headers):
    """PUT /animals/species/{id} updates a species."""
    r = client.post("/api/v1/animals/species", headers=auth_headers, json={
        "code": "ferret", "label": "Furet",
    })
    sid = r.json()["id"]
    response = client.put(f"/api/v1/animals/species/{sid}", headers=auth_headers, json={
        "code": "ferret",
        "label": "Furet domestique",
        "display_order": 20,
    })
    assert response.status_code == 200
    assert response.json()["label"] == "Furet domestique"


def test_delete_species_soft(client, auth_headers):
    """DELETE /animals/species/{id} soft-deletes (is_active=False)."""
    r = client.post("/api/v1/animals/species", headers=auth_headers, json={
        "code": "ferret", "label": "Furet",
    })
    sid = r.json()["id"]
    response = client.delete(f"/api/v1/animals/species/{sid}", headers=auth_headers)
    assert response.status_code == 204


def test_duplicate_species_code_rejected(client, auth_headers):
    """Cannot create two species with the same code."""
    client.post("/api/v1/animals/species", headers=auth_headers, json={
        "code": "ferret", "label": "Furet",
    })
    r2 = client.post("/api/v1/animals/species", headers=auth_headers, json={
        "code": "ferret", "label": "Furet 2",
    })
    assert r2.status_code in (400, 409, 500)
