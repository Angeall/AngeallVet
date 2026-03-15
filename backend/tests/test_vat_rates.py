import pytest


def test_create_vat_rate(client, auth_headers):
    """Admin can create a VAT rate."""
    response = client.post("/api/v1/settings/vat-rates", headers=auth_headers, json={
        "rate": "20.00",
        "label": "TVA 20%",
        "is_default": True,
    })
    assert response.status_code == 201
    data = response.json()
    assert data["rate"] == "20.00"
    assert data["label"] == "TVA 20%"
    assert data["is_default"] is True


def test_list_vat_rates(client, auth_headers):
    """List active VAT rates sorted by rate."""
    client.post("/api/v1/settings/vat-rates", headers=auth_headers, json={
        "rate": "20.00", "label": "TVA 20%",
    })
    client.post("/api/v1/settings/vat-rates", headers=auth_headers, json={
        "rate": "5.50", "label": "TVA 5.5%",
    })
    client.post("/api/v1/settings/vat-rates", headers=auth_headers, json={
        "rate": "10.00", "label": "TVA 10%",
    })
    response = client.get("/api/v1/settings/vat-rates", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # Sorted by rate ascending
    rates = [float(r["rate"]) for r in data]
    assert rates == sorted(rates)


def test_default_vat_rate_uniqueness(client, auth_headers):
    """Setting a new default unsets the previous default."""
    r1 = client.post("/api/v1/settings/vat-rates", headers=auth_headers, json={
        "rate": "20.00", "label": "TVA 20%", "is_default": True,
    })
    r2 = client.post("/api/v1/settings/vat-rates", headers=auth_headers, json={
        "rate": "10.00", "label": "TVA 10%", "is_default": True,
    })
    # Now only the second should be default
    response = client.get("/api/v1/settings/vat-rates", headers=auth_headers)
    data = response.json()
    defaults = [r for r in data if r["is_default"]]
    assert len(defaults) == 1
    assert float(defaults[0]["rate"]) == 10.00


def test_update_vat_rate(client, auth_headers):
    """Admin can update a VAT rate."""
    r = client.post("/api/v1/settings/vat-rates", headers=auth_headers, json={
        "rate": "20.00", "label": "TVA 20%",
    })
    rate_id = r.json()["id"]
    response = client.put(f"/api/v1/settings/vat-rates/{rate_id}", headers=auth_headers, json={
        "label": "TVA normale (20%)",
    })
    assert response.status_code == 200
    assert response.json()["label"] == "TVA normale (20%)"


def test_delete_vat_rate(client, auth_headers):
    """Deleting a VAT rate soft-deletes it (is_active=False)."""
    r = client.post("/api/v1/settings/vat-rates", headers=auth_headers, json={
        "rate": "2.10", "label": "TVA 2.1%",
    })
    rate_id = r.json()["id"]
    response = client.delete(f"/api/v1/settings/vat-rates/{rate_id}", headers=auth_headers)
    assert response.status_code == 204
    # Should not appear in list anymore
    response = client.get("/api/v1/settings/vat-rates", headers=auth_headers)
    assert all(r["id"] != rate_id for r in response.json())


def test_create_vat_rate_forbidden_non_admin(client, vet_headers):
    """Non-admin cannot create VAT rates."""
    response = client.post("/api/v1/settings/vat-rates", headers=vet_headers, json={
        "rate": "20.00", "label": "TVA 20%",
    })
    assert response.status_code == 403
