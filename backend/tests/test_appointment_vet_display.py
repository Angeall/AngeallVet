"""Tests for appointment vet/client/animal name display and vet filter."""


def _setup_data(client, auth_headers):
    """Create client + animal + appointment."""
    c = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Jean", "last_name": "Dupont",
    })
    client_id = c.json()["id"]

    a = client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": client_id, "name": "Rex", "species": "dog",
    })
    animal_id = a.json()["id"]

    return client_id, animal_id


def test_appointment_has_names(client, auth_headers, admin_user):
    """Appointment response includes vet, client and animal names."""
    client_id, animal_id = _setup_data(client, auth_headers)
    r = client.post("/api/v1/appointments", headers=auth_headers, json={
        "client_id": client_id,
        "animal_id": animal_id,
        "veterinarian_id": admin_user.id,
        "start_time": "2026-03-20T10:00:00",
        "end_time": "2026-03-20T10:30:00",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["veterinarian_name"] is not None
    assert data["client_name"] == "Dupont Jean"
    assert data["animal_name"] == "Rex"


def test_list_appointments_has_names(client, auth_headers, admin_user):
    """GET /appointments returns appointments with names."""
    client_id, animal_id = _setup_data(client, auth_headers)
    client.post("/api/v1/appointments", headers=auth_headers, json={
        "client_id": client_id,
        "animal_id": animal_id,
        "veterinarian_id": admin_user.id,
        "start_time": "2026-03-20T10:00:00",
        "end_time": "2026-03-20T10:30:00",
    })
    r = client.get("/api/v1/appointments", headers=auth_headers)
    assert r.status_code == 200
    appts = r.json()
    assert len(appts) >= 1
    assert appts[0]["client_name"] == "Dupont Jean"


def test_waiting_room_vet_filter(client, auth_headers, admin_user, vet_user):
    """GET /appointments/waiting-room?veterinarian_id=X filters by vet."""
    client_id, animal_id = _setup_data(client, auth_headers)

    # Create appointment for admin_user (acting as vet)
    client.post("/api/v1/appointments", headers=auth_headers, json={
        "client_id": client_id,
        "animal_id": animal_id,
        "veterinarian_id": admin_user.id,
        "start_time": "2026-03-20T10:00:00",
        "end_time": "2026-03-20T10:30:00",
        "status": "arrived",
    })

    # Create appointment for vet_user
    client.post("/api/v1/appointments", headers=auth_headers, json={
        "client_id": client_id,
        "animal_id": animal_id,
        "veterinarian_id": vet_user.id,
        "start_time": "2026-03-20T11:00:00",
        "end_time": "2026-03-20T11:30:00",
        "status": "arrived",
    })

    # Filter by vet_user
    r = client.get(
        f"/api/v1/appointments/waiting-room?veterinarian_id={vet_user.id}",
        headers=auth_headers,
    )
    assert r.status_code == 200
    results = r.json()
    for appt in results:
        assert appt["veterinarian_id"] == vet_user.id
