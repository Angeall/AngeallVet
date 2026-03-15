"""Tests for sidenav color per user."""


def test_update_me_sidenav_color(client, auth_headers, admin_user):
    """PUT /auth/me updates sidenav_color."""
    r = client.put("/api/v1/auth/me", headers=auth_headers, json={
        "sidenav_color": "#1e3a5f",
    })
    assert r.status_code == 200
    assert r.json()["sidenav_color"] == "#1e3a5f"


def test_update_me_resets_color(client, auth_headers, admin_user):
    """PUT /auth/me can reset sidenav_color to null."""
    client.put("/api/v1/auth/me", headers=auth_headers, json={
        "sidenav_color": "#1e3a5f",
    })
    r = client.put("/api/v1/auth/me", headers=auth_headers, json={
        "sidenav_color": None,
    })
    assert r.status_code == 200
    assert r.json()["sidenav_color"] is None


def test_update_me_ignores_role_change(client, auth_headers, admin_user):
    """PUT /auth/me does NOT allow changing role (restricted field)."""
    r = client.put("/api/v1/auth/me", headers=auth_headers, json={
        "role": "guest",
        "sidenav_color": "#713f12",
    })
    assert r.status_code == 200
    # Color should be updated
    assert r.json()["sidenav_color"] == "#713f12"
    # Role should NOT have changed
    assert r.json()["role"] == "admin"


def test_get_me_includes_color(client, auth_headers, admin_user):
    """GET /auth/me includes sidenav_color field."""
    client.put("/api/v1/auth/me", headers=auth_headers, json={
        "sidenav_color": "#14532d",
    })
    r = client.get("/api/v1/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["sidenav_color"] == "#14532d"
