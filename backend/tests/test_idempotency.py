"""Tests for Idempotency-Key dedup on offline-queued writes.

A write replayed from the frontend's offline queue carries the same
Idempotency-Key as its first attempt and must NOT create a duplicate.
"""


def _client_and_animal(client, headers):
    c = client.post("/api/v1/clients", headers=headers, json={
        "first_name": "Jean", "last_name": "Dupont",
    })
    client_id = c.json()["id"]
    a = client.post("/api/v1/animals", headers=headers, json={
        "client_id": client_id, "name": "Rex", "species": "dog",
    })
    return client_id, a.json()["id"]


def test_medical_record_idempotent_replay(client, auth_headers):
    """Same key replayed -> one record, identical id returned both times."""
    _, animal_id = _client_and_animal(client, auth_headers)
    body = {"animal_id": animal_id, "record_type": "consultation", "subjective": "Toux"}
    headers = {**auth_headers, "Idempotency-Key": "rec-abc-123"}

    first = client.post("/api/v1/medical/records", headers=headers, json=body)
    second = client.post("/api/v1/medical/records", headers=headers, json=body)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    listing = client.get(f"/api/v1/medical/records?animal_id={animal_id}", headers=auth_headers)
    assert len(listing.json()) == 1


def test_medical_record_distinct_keys_create_two(client, auth_headers):
    """Different keys are independent writes."""
    _, animal_id = _client_and_animal(client, auth_headers)
    body = {"animal_id": animal_id, "record_type": "consultation", "subjective": "Toux"}

    client.post("/api/v1/medical/records", headers={**auth_headers, "Idempotency-Key": "k1"}, json=body)
    client.post("/api/v1/medical/records", headers={**auth_headers, "Idempotency-Key": "k2"}, json=body)

    listing = client.get(f"/api/v1/medical/records?animal_id={animal_id}", headers=auth_headers)
    assert len(listing.json()) == 2


def test_medical_record_without_key_not_deduped(client, auth_headers):
    """No key -> legacy behavior, each POST creates a record."""
    _, animal_id = _client_and_animal(client, auth_headers)
    body = {"animal_id": animal_id, "record_type": "consultation", "subjective": "Toux"}

    client.post("/api/v1/medical/records", headers=auth_headers, json=body)
    client.post("/api/v1/medical/records", headers=auth_headers, json=body)

    listing = client.get(f"/api/v1/medical/records?animal_id={animal_id}", headers=auth_headers)
    assert len(listing.json()) == 2


def test_weight_idempotent_replay(client, auth_headers):
    """Same key replayed on the weight endpoint -> one weight, same id."""
    _, animal_id = _client_and_animal(client, auth_headers)
    headers = {**auth_headers, "Idempotency-Key": "w-1"}

    first = client.post(f"/api/v1/animals/{animal_id}/weights", headers=headers, json={"weight_kg": 10.0})
    second = client.post(f"/api/v1/animals/{animal_id}/weights", headers=headers, json={"weight_kg": 10.0})
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    weights = client.get(f"/api/v1/animals/{animal_id}/weights", headers=auth_headers)
    assert len(weights.json()) == 1


def test_client_idempotent_replay(client, auth_headers):
    """Same key replayed on client creation -> one client, same id."""
    headers = {**auth_headers, "Idempotency-Key": "cli-1"}
    body = {"first_name": "Paul", "last_name": "Durand"}

    first = client.post("/api/v1/clients", headers=headers, json=body)
    second = client.post("/api/v1/clients", headers=headers, json=body)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    listing = client.get("/api/v1/clients?search=Durand", headers=auth_headers)
    assert len(listing.json()) == 1


def test_appointment_idempotent_replay(client, auth_headers, admin_user):
    """Same key replayed on appointment creation -> one appointment, same id."""
    client_id, animal_id = _client_and_animal(client, auth_headers)
    body = {
        "client_id": client_id,
        "animal_id": animal_id,
        "veterinarian_id": admin_user.id,
        "appointment_type": "consultation",
        "start_time": "2026-07-01T10:00:00",
        "end_time": "2026-07-01T10:30:00",
    }
    headers = {**auth_headers, "Idempotency-Key": "appt-1"}

    first = client.post("/api/v1/appointments", headers=headers, json=body)
    second = client.post("/api/v1/appointments", headers=headers, json=body)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    listing = client.get("/api/v1/appointments?date_from=2026-07-01&date_to=2026-07-01", headers=auth_headers)
    assert len(listing.json()) == 1
