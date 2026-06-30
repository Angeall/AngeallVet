"""
Tests for auth endpoints.

register / login / session talk to PocketBase over HTTP, so we patch the
PocketBase helper functions. The /me and /users endpoints exercise the real
application-JWT verification (signed with the default tenant secret).
"""
import uuid
from unittest.mock import patch

from app.core.config import settings
from app.models.user import UserRole


def test_get_me(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "admin@test.com"
    assert response.json()["pb_user_id"] is not None


def test_get_me_unauthenticated(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401  # No credentials (FastAPI HTTPBearer)


def test_get_me_invalid_token(client):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401


def test_list_users_admin(client, auth_headers, vet_user):
    response = client.get("/api/v1/auth/users", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_list_users_non_admin(client, vet_headers):
    response = client.get("/api/v1/auth/users", headers=vet_headers)
    assert response.status_code == 403


def test_update_user_admin(client, auth_headers, vet_user):
    response = client.put(
        f"/api/v1/auth/users/{vet_user.id}",
        headers=auth_headers,
        json={"first_name": "Updated", "phone": "0600000000"},
    )
    assert response.status_code == 200
    assert response.json()["first_name"] == "Updated"
    assert response.json()["phone"] == "0600000000"


def test_update_user_non_admin(client, vet_headers, admin_user):
    response = client.put(
        f"/api/v1/auth/users/{admin_user.id}",
        headers=vet_headers,
        json={"first_name": "Hacked"},
    )
    assert response.status_code == 403


def test_register_with_mocked_pocketbase(client, auth_headers):
    """Register (admin only) creates a PocketBase record + local profile."""
    fake_uid = str(uuid.uuid4())

    with patch("app.api.endpoints.auth.pb_admin_token", return_value="admin-token"), patch(
        "app.api.endpoints.auth.pb_create_user",
        return_value={"id": fake_uid, "email": "new@test.com"},
    ):
        response = client.post(
            "/api/v1/auth/register",
            headers=auth_headers,
            json={
                "email": "new@test.com",
                "password": "password123",
                "first_name": "New",
                "last_name": "User",
                "role": "assistant",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@test.com"
    assert data["role"] == "assistant"
    assert data["pb_user_id"] == fake_uid


def test_register_blocked_at_seat_cap(client, auth_headers, monkeypatch):
    """At the seat cap, register is refused before any PocketBase side effect."""
    monkeypatch.setattr(settings, "MAX_USERS", 1)  # only the admin fits
    called = {"pb": False}
    with patch("app.api.endpoints.auth.pb_admin_token", side_effect=lambda *a, **k: called.__setitem__("pb", True)):
        response = client.post(
            "/api/v1/auth/register",
            headers=auth_headers,
            json={"email": "extra@test.com", "password": "password123", "first_name": "E", "last_name": "X"},
        )
    assert response.status_code == 403
    assert "Limite" in response.json()["detail"]
    assert called["pb"] is False  # never reached PocketBase


def test_register_allowed_under_seat_cap(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "MAX_USERS", 10)
    with patch("app.api.endpoints.auth.pb_admin_token", return_value="t"), patch(
        "app.api.endpoints.auth.pb_create_user",
        return_value={"id": str(uuid.uuid4()), "email": "ok@test.com"},
    ):
        response = client.post(
            "/api/v1/auth/register",
            headers=auth_headers,
            json={"email": "ok@test.com", "password": "password123", "first_name": "O", "last_name": "K"},
        )
    assert response.status_code == 201


def test_register_requires_admin(client, vet_headers):
    """A non-admin cannot create users."""
    response = client.post(
        "/api/v1/auth/register",
        headers=vet_headers,
        json={"email": "x@test.com", "password": "password123", "first_name": "X", "last_name": "Y"},
    )
    assert response.status_code == 403


def test_register_duplicate_email(client, auth_headers, admin_user):
    """Registering an existing email fails before hitting PocketBase."""
    response = client.post(
        "/api/v1/auth/register",
        headers=auth_headers,
        json={
            "email": "admin@test.com",
            "password": "password123",
            "first_name": "Dup",
            "last_name": "User",
        },
    )
    assert response.status_code == 400


def test_login_with_mocked_pocketbase(client, admin_user):
    """Login exchanges PocketBase credentials for an application JWT."""
    pb_record = {"id": admin_user.pb_user_id, "email": "admin@test.com"}

    with patch(
        "app.api.endpoints.auth.pb_auth_with_password",
        return_value=("pb-token", pb_record),
    ):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "admin123"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]  # application JWT
    assert data["refresh_token"] == "pb-token"
    assert data["user"]["email"] == "admin@test.com"


def test_session_exchange_with_mocked_pocketbase(client, admin_user):
    """POST /auth/session verifies a PB token and returns an application JWT
    that is then accepted by a protected endpoint."""
    pb_record = {"id": admin_user.pb_user_id, "email": "admin@test.com"}

    with patch(
        "app.api.endpoints.auth.pb_verify_token",
        return_value=("fresh-pb-token", pb_record),
    ):
        response = client.post("/api/v1/auth/session", json={"pb_token": "browser-pb-token"})

    assert response.status_code == 200
    app_token = response.json()["access_token"]
    assert app_token

    # The minted application JWT must authenticate against a protected route.
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {app_token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "admin@test.com"


def test_session_invalid_pb_token(client):
    """An invalid PocketBase token yields 401 from the exchange endpoint."""
    from fastapi import HTTPException

    with patch(
        "app.api.endpoints.auth.pb_verify_token",
        side_effect=HTTPException(status_code=401, detail="Jeton PocketBase invalide ou expiré"),
    ):
        response = client.post("/api/v1/auth/session", json={"pb_token": "bad"})
    assert response.status_code == 401
