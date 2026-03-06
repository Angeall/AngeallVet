import pytest


@pytest.fixture
def sample_client(client, auth_headers):
    res = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Jean", "last_name": "Dupont",
    })
    return res.json()


def test_create_animal(client, auth_headers, sample_client):
    response = client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": sample_client["id"],
        "name": "Rex",
        "species": "dog",
        "breed": "Berger Allemand",
        "sex": "male",
        "is_neutered": False,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Rex"
    assert data["species"] == "dog"


def test_list_animals_by_client(client, auth_headers, sample_client):
    client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": sample_client["id"], "name": "Rex", "species": "dog",
    })
    client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": sample_client["id"], "name": "Minou", "species": "cat",
    })
    response = client.get(f"/api/v1/animals?client_id={sample_client['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_add_alert(client, auth_headers, sample_client):
    animal_res = client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": sample_client["id"], "name": "Rex", "species": "dog",
    })
    animal_id = animal_res.json()["id"]

    response = client.post(f"/api/v1/animals/{animal_id}/alerts", headers=auth_headers, json={
        "alert_type": "aggressive",
        "message": "Attention: animal agressif",
        "severity": "danger",
    })
    assert response.status_code == 201
    assert response.json()["alert_type"] == "aggressive"


def test_add_weight(client, auth_headers, sample_client):
    animal_res = client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": sample_client["id"], "name": "Rex", "species": "dog",
    })
    animal_id = animal_res.json()["id"]

    response = client.post(f"/api/v1/animals/{animal_id}/weights", headers=auth_headers, json={
        "weight_kg": 25.5,
    })
    assert response.status_code == 201

    weights = client.get(f"/api/v1/animals/{animal_id}/weights", headers=auth_headers)
    assert len(weights.json()) == 1
    assert float(weights.json()[0]["weight_kg"]) == 25.5


def test_search_by_microchip(client, auth_headers, sample_client):
    client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": sample_client["id"],
        "name": "Rex",
        "species": "dog",
        "microchip_number": "250269812345678",
    })
    response = client.get("/api/v1/animals?search=250269812345678", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Rex"
