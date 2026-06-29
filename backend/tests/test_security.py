"""Security regression tests for the multi-tenant auth hardening."""
from unittest.mock import patch


def test_tenants_endpoint_requires_platform_token(client, auth_headers):
    """A tenant ADMIN must NOT reach the cross-tenant registry. PLATFORM_ADMIN_TOKEN
    is unset in tests, so the guard fails closed (403)."""
    assert client.get("/api/v1/auth/tenants", headers=auth_headers).status_code == 403
    assert client.get(
        "/api/v1/auth/tenants",
        headers={**auth_headers, "X-Platform-Admin-Token": "wrong"},
    ).status_code == 403


def test_session_does_not_relink_unverified_email(client, admin_user):
    """An unverified PocketBase account sharing a known email must NOT be linked
    to the existing profile (blocks public-signup account takeover)."""
    record = {"id": "attacker-pb-id", "email": "admin@test.com", "verified": False}
    with patch("app.api.endpoints.auth.pb_verify_token", return_value=("tok", record)):
        r = client.post("/api/v1/auth/session", json={"pb_token": "x"})
    assert r.status_code == 401


def test_session_relinks_verified_email(client, admin_user):
    """A verified PocketBase account (admin-provisioned) relinks the profile by
    email — the supported migration path."""
    record = {"id": "verified-pb-id", "email": "admin@test.com", "verified": True}
    with patch("app.api.endpoints.auth.pb_verify_token", return_value=("tok", record)):
        r = client.post("/api/v1/auth/session", json={"pb_token": "x"})
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "admin@test.com"


def test_uploads_not_publicly_served(client):
    """The public /uploads static mount has been removed; medical attachments are
    only reachable through the authenticated download endpoint."""
    assert client.get("/uploads/medical/1/secret.pdf").status_code == 404
