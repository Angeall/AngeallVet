"""Tests for postal reminder channel and postal-due endpoint."""


def test_create_reminder_rule_postal(client, auth_headers):
    """Creating a reminder rule with postal channel works."""
    response = client.post("/api/v1/communications/reminders", headers=auth_headers, json={
        "name": "Rappel vaccin postal",
        "reminder_type": "vaccine",
        "channel": "postal",
        "days_before": 30,
        "days_before_second": 7,
        "days_after": 1,
        "postal_template": "Cher {client_name}, votre animal {animal_name} doit etre vaccine.",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["channel"] == "postal"
    assert data["postal_template"] is not None
    assert "{client_name}" in data["postal_template"]


def test_postal_due_reminders_empty(client, auth_headers):
    """Postal due endpoint returns empty when no rules exist."""
    response = client.get("/api/v1/communications/reminders/postal-due", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_postal_due_with_rule_no_records(client, auth_headers):
    """Postal due returns empty when rules exist but no vaccination records."""
    client.post("/api/v1/communications/reminders", headers=auth_headers, json={
        "name": "Rappel vaccin postal",
        "reminder_type": "vaccine",
        "channel": "postal",
        "days_before": 30,
    })
    response = client.get("/api/v1/communications/reminders/postal-due", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []
