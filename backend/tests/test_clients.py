import pytest


def test_create_client(client, auth_headers):
    response = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "jean@example.com",
        "phone": "0123456789",
        "city": "Paris",
        "postal_code": "75001",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Jean"
    assert data["last_name"] == "Dupont"
    assert data["city"] == "Paris"


def test_list_clients(client, auth_headers):
    client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Alice", "last_name": "Martin",
    })
    client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Bob", "last_name": "Bernard",
    })
    response = client.get("/api/v1/clients", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_search_clients(client, auth_headers):
    client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Alice", "last_name": "Martin",
    })
    client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Bob", "last_name": "Bernard",
    })
    response = client.get("/api/v1/clients?search=Martin", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["last_name"] == "Martin"


def test_get_client(client, auth_headers):
    res = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Test", "last_name": "Client",
    })
    client_id = res.json()["id"]
    response = client.get(f"/api/v1/clients/{client_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == client_id


def test_update_client(client, auth_headers):
    res = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Test", "last_name": "Client",
    })
    client_id = res.json()["id"]
    response = client.put(f"/api/v1/clients/{client_id}", headers=auth_headers, json={
        "phone": "0987654321",
    })
    assert response.status_code == 200
    assert response.json()["phone"] == "0987654321"


def test_delete_client(client, auth_headers):
    res = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Test", "last_name": "ToDelete",
    })
    client_id = res.json()["id"]
    response = client.delete(f"/api/v1/clients/{client_id}", headers=auth_headers)
    assert response.status_code == 204

    # Should not appear in list anymore
    response = client.get("/api/v1/clients", headers=auth_headers)
    assert all(c["id"] != client_id for c in response.json())


def test_create_client_minimal(client, auth_headers):
    """Client can be created with only first_name and last_name."""
    response = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Pierre",
        "last_name": "Durand",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Pierre"
    assert data["email"] is None
    assert data["phone"] is None


def test_create_client_empty_email(client, auth_headers):
    """Empty email string should be converted to None, not rejected."""
    response = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Marie",
        "last_name": "Blanc",
        "email": "",
        "phone": "",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] is None
    assert data["phone"] is None


def test_create_client_with_vat_number(client, auth_headers):
    """Client can be created with a VAT number for B2B invoicing."""
    response = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Entreprise",
        "last_name": "SAS",
        "vat_number": "FR12345678901",
    })
    assert response.status_code == 201
    assert response.json()["vat_number"] == "FR12345678901"


def test_update_client_vat_number(client, auth_headers):
    """VAT number can be updated on an existing client."""
    res = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Test", "last_name": "Client",
    })
    client_id = res.json()["id"]
    response = client.put(f"/api/v1/clients/{client_id}", headers=auth_headers, json={
        "vat_number": "FR98765432109",
    })
    assert response.status_code == 200
    assert response.json()["vat_number"] == "FR98765432109"


def test_merge_clients(client, auth_headers):
    res1 = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Source", "last_name": "Client",
    })
    res2 = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Target", "last_name": "Client",
    })
    response = client.post("/api/v1/clients/merge", headers=auth_headers, json={
        "source_client_id": res1.json()["id"],
        "target_client_id": res2.json()["id"],
    })
    assert response.status_code == 200
    assert response.json()["id"] == res2.json()["id"]
