"""Tests for the /auth/staff endpoint."""
import uuid
from app.models.user import User, UserRole


def test_list_staff_as_vet(client, vet_headers, admin_user, vet_user, db):
    """Vets should be able to list staff members."""
    response = client.get("/api/v1/auth/staff", headers=vet_headers)
    assert response.status_code == 200
    staff = response.json()
    emails = [s["email"] for s in staff]
    assert "admin@test.com" in emails
    assert "vet@test.com" in emails


def test_list_staff_excludes_inactive(client, auth_headers, db):
    """Inactive users should not appear in staff list."""
    uid = str(uuid.uuid4())
    inactive = User(
        supabase_uid=uid, email="inactive@test.com",
        first_name="Gone", last_name="User",
        role=UserRole.VETERINARIAN, is_active=False,
    )
    db.add(inactive)
    db.commit()

    response = client.get("/api/v1/auth/staff", headers=auth_headers)
    assert response.status_code == 200
    emails = [s["email"] for s in response.json()]
    assert "inactive@test.com" not in emails


def test_list_staff_excludes_accountant_and_guest(client, auth_headers, db):
    """Only admin, vet, and assistant roles should appear in staff."""
    for role, email in [
        (UserRole.ACCOUNTANT, "accountant@test.com"),
        (UserRole.GUEST, "guest@test.com"),
    ]:
        uid = str(uuid.uuid4())
        user = User(
            supabase_uid=uid, email=email,
            first_name="Test", last_name=role.value,
            role=role, is_active=True,
        )
        db.add(user)
    db.commit()

    response = client.get("/api/v1/auth/staff", headers=auth_headers)
    assert response.status_code == 200
    emails = [s["email"] for s in response.json()]
    assert "accountant@test.com" not in emails
    assert "guest@test.com" not in emails


def test_list_staff_includes_assistant(client, auth_headers, db):
    """Assistants should appear in the staff list."""
    uid = str(uuid.uuid4())
    assistant = User(
        supabase_uid=uid, email="assistant@test.com",
        first_name="Test", last_name="Assistant",
        role=UserRole.ASSISTANT, is_active=True,
    )
    db.add(assistant)
    db.commit()

    response = client.get("/api/v1/auth/staff", headers=auth_headers)
    assert response.status_code == 200
    emails = [s["email"] for s in response.json()]
    assert "assistant@test.com" in emails


def test_list_staff_unauthenticated(client):
    """Unauthenticated requests should be rejected."""
    response = client.get("/api/v1/auth/staff")
    assert response.status_code == 403
