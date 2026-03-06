"""
Tests for auth endpoints.

Note: register and login hit Supabase APIs directly, so we test them
with mocked Supabase calls. The /me and /users endpoints use JWT
verification which is fully testable with our test JWT secret.
"""
import uuid
from unittest.mock import patch, MagicMock

from app.models.user import UserRole


def test_get_me(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "admin@test.com"
    assert response.json()["supabase_uid"] is not None


def test_get_me_unauthenticated(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 403  # No credentials


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


def test_register_with_mocked_supabase(client, db):
    """Test register endpoint with mocked Supabase admin client."""
    fake_uid = str(uuid.uuid4())
    mock_user = MagicMock()
    mock_user.id = fake_uid

    mock_response = MagicMock()
    mock_response.user = mock_user

    mock_supabase = MagicMock()
    mock_supabase.auth.admin.create_user.return_value = mock_response

    with patch("app.api.endpoints.auth.get_supabase_admin", return_value=mock_supabase):
        response = client.post("/api/v1/auth/register", json={
            "email": "new@test.com",
            "password": "password123",
            "first_name": "New",
            "last_name": "User",
            "role": "assistant",
        })

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@test.com"
    assert data["role"] == "assistant"
    assert data["supabase_uid"] == fake_uid


def test_register_duplicate_email(client, admin_user):
    """Test that registering with an existing email fails before hitting Supabase."""
    response = client.post("/api/v1/auth/register", json={
        "email": "admin@test.com",
        "password": "password123",
        "first_name": "Dup",
        "last_name": "User",
    })
    assert response.status_code == 400


def test_login_with_mocked_supabase(client, admin_user):
    """Test login endpoint with mocked Supabase."""
    mock_session = MagicMock()
    mock_session.access_token = "fake-access-token"
    mock_session.refresh_token = "fake-refresh-token"

    mock_supabase_user = MagicMock()
    mock_supabase_user.id = admin_user.supabase_uid

    mock_response = MagicMock()
    mock_response.session = mock_session
    mock_response.user = mock_supabase_user

    mock_supabase = MagicMock()
    mock_supabase.auth.sign_in_with_password.return_value = mock_response

    with patch("app.api.endpoints.auth.get_supabase_admin", return_value=mock_supabase):
        response = client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123",
        })

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "fake-access-token"
    assert data["refresh_token"] == "fake-refresh-token"
    assert data["user"]["email"] == "admin@test.com"
