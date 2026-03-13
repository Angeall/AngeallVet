"""Tests for inventory shortcuts and service product behaviour."""
import pytest


@pytest.fixture
def sample_service(client, auth_headers):
    """Create a service-type product (medical act)."""
    res = client.post("/api/v1/inventory/products", headers=auth_headers, json={
        "name": "Consultation",
        "product_type": "service",
        "selling_price": 40.00,
        "vat_rate": 20.00,
    })
    assert res.status_code == 201
    return res.json()


@pytest.fixture
def sample_medication(client, auth_headers):
    """Create a medication product."""
    res = client.post("/api/v1/inventory/products", headers=auth_headers, json={
        "name": "Amoxicilline 250mg",
        "product_type": "medication",
        "selling_price": 12.50,
        "vat_rate": 20.00,
        "unit": "comprimé",
        "stock_alert_threshold": 10,
    })
    assert res.status_code == 201
    return res.json()


def test_shortcut_default_false(sample_medication):
    """New products should not be shortcuts by default."""
    assert sample_medication["is_shortcut"] is False


def test_toggle_shortcut_on(client, auth_headers, sample_service):
    """Mark a product as a shortcut."""
    res = client.put(
        f"/api/v1/inventory/products/{sample_service['id']}",
        headers=auth_headers,
        json={"is_shortcut": True},
    )
    assert res.status_code == 200
    assert res.json()["is_shortcut"] is True


def test_toggle_shortcut_off(client, auth_headers, sample_service):
    """Unmark a shortcut product."""
    client.put(
        f"/api/v1/inventory/products/{sample_service['id']}",
        headers=auth_headers,
        json={"is_shortcut": True},
    )
    res = client.put(
        f"/api/v1/inventory/products/{sample_service['id']}",
        headers=auth_headers,
        json={"is_shortcut": False},
    )
    assert res.status_code == 200
    assert res.json()["is_shortcut"] is False


def test_get_shortcuts_empty(client, auth_headers, sample_service):
    """No shortcuts when none are flagged."""
    res = client.get("/api/v1/inventory/shortcuts", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_get_shortcuts_returns_flagged(client, auth_headers, sample_service, sample_medication):
    """Only shortcut-flagged products should appear in /shortcuts."""
    # Flag the service as shortcut
    client.put(
        f"/api/v1/inventory/products/{sample_service['id']}",
        headers=auth_headers,
        json={"is_shortcut": True},
    )
    res = client.get("/api/v1/inventory/shortcuts", headers=auth_headers)
    assert res.status_code == 200
    shortcuts = res.json()
    assert len(shortcuts) == 1
    assert shortcuts[0]["id"] == sample_service["id"]
    assert shortcuts[0]["name"] == "Consultation"


def test_get_shortcuts_multiple(client, auth_headers, sample_service, sample_medication):
    """Multiple products can be shortcuts."""
    client.put(f"/api/v1/inventory/products/{sample_service['id']}", headers=auth_headers, json={"is_shortcut": True})
    client.put(f"/api/v1/inventory/products/{sample_medication['id']}", headers=auth_headers, json={"is_shortcut": True})

    res = client.get("/api/v1/inventory/shortcuts", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_inactive_shortcut_not_returned(client, auth_headers, sample_service):
    """Deactivated products should not appear in shortcuts."""
    client.put(f"/api/v1/inventory/products/{sample_service['id']}", headers=auth_headers, json={"is_shortcut": True})
    # Deactivate
    client.put(f"/api/v1/inventory/products/{sample_service['id']}", headers=auth_headers, json={"is_active": False})

    res = client.get("/api/v1/inventory/shortcuts", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 0


def test_service_not_in_stock_alerts(client, auth_headers, sample_service):
    """Services (medical acts) should never appear in stock alerts."""
    res = client.get("/api/v1/inventory/alerts", headers=auth_headers)
    assert res.status_code == 200
    service_ids = [p["id"] for p in res.json()]
    assert sample_service["id"] not in service_ids


def test_medication_low_stock_in_alerts(client, auth_headers, sample_medication):
    """Medications with zero stock below threshold should appear in alerts."""
    res = client.get("/api/v1/inventory/alerts", headers=auth_headers)
    assert res.status_code == 200
    alert_ids = [p["id"] for p in res.json()]
    assert sample_medication["id"] in alert_ids


def test_create_product_with_shortcut_flag(client, auth_headers):
    """Create a product directly with is_shortcut=True."""
    res = client.post("/api/v1/inventory/products", headers=auth_headers, json={
        "name": "Vaccin rage",
        "product_type": "service",
        "selling_price": 55.00,
        "vat_rate": 20.00,
        "is_shortcut": True,
    })
    assert res.status_code == 201
    assert res.json()["is_shortcut"] is True

    shortcuts = client.get("/api/v1/inventory/shortcuts", headers=auth_headers)
    assert any(s["name"] == "Vaccin rage" for s in shortcuts.json())
