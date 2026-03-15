"""Tests for associations (foster families) CRUD and animal linking."""


def test_create_association(client, auth_headers):
    """Creating an association works."""
    response = client.post("/api/v1/associations", headers=auth_headers, json={
        "name": "SPA Paris",
        "contact_name": "Marie Dupont",
        "email": "spa@example.com",
        "phone": "0123456789",
        "discount_percent": 15.0,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "SPA Paris"
    assert data["contact_name"] == "Marie Dupont"
    assert float(data["discount_percent"]) == 15.0
    assert data["is_active"] is True


def test_list_associations(client, auth_headers):
    """Listing associations returns created entries."""
    client.post("/api/v1/associations", headers=auth_headers, json={
        "name": "SPA Paris",
    })
    client.post("/api/v1/associations", headers=auth_headers, json={
        "name": "Refuge du Coeur",
    })
    response = client.get("/api/v1/associations", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_association(client, auth_headers):
    """Updating an association works."""
    r = client.post("/api/v1/associations", headers=auth_headers, json={
        "name": "SPA Paris",
    })
    assoc_id = r.json()["id"]
    response = client.put(f"/api/v1/associations/{assoc_id}", headers=auth_headers, json={
        "name": "SPA Paris 75",
        "discount_percent": 20.0,
    })
    assert response.status_code == 200
    assert response.json()["name"] == "SPA Paris 75"
    assert float(response.json()["discount_percent"]) == 20.0


def test_animal_with_association(client, auth_headers):
    """Creating an animal linked to an association works."""
    # Create association
    a = client.post("/api/v1/associations", headers=auth_headers, json={
        "name": "SPA Paris",
    })
    assoc_id = a.json()["id"]

    # Create client
    c = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Jean",
        "last_name": "Martin",
    })
    client_id = c.json()["id"]

    # Create animal with association
    r = client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": client_id,
        "name": "Rex",
        "species": "dog",
        "association_id": assoc_id,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["association_id"] == assoc_id
    assert data["association_name"] == "SPA Paris"


def test_animal_without_association(client, auth_headers):
    """Creating an animal without association has null association_name."""
    c = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Jean",
        "last_name": "Martin",
    })
    client_id = c.json()["id"]

    r = client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": client_id,
        "name": "Minou",
        "species": "cat",
    })
    assert r.status_code == 201
    assert r.json()["association_id"] is None
    assert r.json()["association_name"] is None
