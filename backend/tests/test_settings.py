import pytest


def test_get_clinic_settings(client, auth_headers):
    """GET /settings/clinic returns default settings."""
    response = client.get("/api/v1/settings/clinic", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["default_appointment_duration_minutes"] == 30


def test_update_clinic_settings(client, auth_headers):
    """Admin can update clinic settings."""
    response = client.put("/api/v1/settings/clinic", headers=auth_headers, json={
        "clinic_name": "Clinique AngeallVet",
        "siret": "12345678901234",
        "phone": "0123456789",
        "address": "10 Rue des Veterinaires",
        "city": "Paris",
        "postal_code": "75001",
        "default_appointment_duration_minutes": 45,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["clinic_name"] == "Clinique AngeallVet"
    assert data["siret"] == "12345678901234"
    assert data["default_appointment_duration_minutes"] == 45


def test_update_clinic_settings_forbidden_non_admin(client, vet_headers):
    """Non-admin cannot update clinic settings."""
    response = client.put("/api/v1/settings/clinic", headers=vet_headers, json={
        "clinic_name": "Hacked",
    })
    assert response.status_code == 403


def test_update_clinic_settings_partial(client, auth_headers):
    """Partial update only changes specified fields."""
    # First set name
    client.put("/api/v1/settings/clinic", headers=auth_headers, json={
        "clinic_name": "Ma Clinique",
    })
    # Then update only phone
    response = client.put("/api/v1/settings/clinic", headers=auth_headers, json={
        "phone": "0987654321",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["clinic_name"] == "Ma Clinique"
    assert data["phone"] == "0987654321"
