"""Tests for medical record weight recording and latest weight endpoint."""


def _create_client_and_animal(client, auth_headers):
    """Helper to create a client and an animal."""
    c = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Jean", "last_name": "Dupont",
    })
    client_id = c.json()["id"]
    a = client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": client_id, "name": "Rex", "species": "dog",
    })
    return client_id, a.json()["id"]


def test_create_record_with_weight(client, auth_headers):
    """Creating a medical record with weight_kg should also create a weight record."""
    _, animal_id = _create_client_and_animal(client, auth_headers)
    response = client.post("/api/v1/medical/records", headers=auth_headers, json={
        "animal_id": animal_id,
        "record_type": "consultation",
        "subjective": "Visite de routine",
        "weight_kg": 12.5,
    })
    assert response.status_code == 201

    # Check weight was recorded
    weights = client.get(f"/api/v1/animals/{animal_id}/weights", headers=auth_headers)
    assert weights.status_code == 200
    assert len(weights.json()) == 1
    assert float(weights.json()[0]["weight_kg"]) == 12.5


def test_create_record_without_weight(client, auth_headers):
    """Creating a medical record without weight_kg should not create a weight record."""
    _, animal_id = _create_client_and_animal(client, auth_headers)
    response = client.post("/api/v1/medical/records", headers=auth_headers, json={
        "animal_id": animal_id,
        "record_type": "consultation",
        "subjective": "Visite de routine",
    })
    assert response.status_code == 201

    weights = client.get(f"/api/v1/animals/{animal_id}/weights", headers=auth_headers)
    assert weights.status_code == 200
    assert len(weights.json()) == 0


def test_latest_weight_endpoint(client, auth_headers):
    """GET /animals/{id}/weights/latest should return the most recent weight."""
    _, animal_id = _create_client_and_animal(client, auth_headers)

    # Add two weights
    client.post(f"/api/v1/animals/{animal_id}/weights", headers=auth_headers, json={
        "weight_kg": 10.0,
    })
    client.post(f"/api/v1/animals/{animal_id}/weights", headers=auth_headers, json={
        "weight_kg": 12.5,
    })

    response = client.get(f"/api/v1/animals/{animal_id}/weights/latest", headers=auth_headers)
    assert response.status_code == 200
    assert float(response.json()["weight_kg"]) == 12.5


def test_latest_weight_no_records(client, auth_headers):
    """GET /animals/{id}/weights/latest should return 404 if no weights exist."""
    _, animal_id = _create_client_and_animal(client, auth_headers)
    response = client.get(f"/api/v1/animals/{animal_id}/weights/latest", headers=auth_headers)
    assert response.status_code == 404
