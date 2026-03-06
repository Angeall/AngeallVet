def test_register(client):
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


def test_register_duplicate_email(client, admin_user):
    response = client.post("/api/v1/auth/register", json={
        "email": "admin@test.com",
        "password": "password123",
        "first_name": "Dup",
        "last_name": "User",
    })
    assert response.status_code == 400


def test_login_success(client, admin_user):
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "admin123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "admin@test.com"


def test_login_wrong_password(client, admin_user):
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "wrong",
    })
    assert response.status_code == 401


def test_get_me(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "admin@test.com"


def test_list_users_admin(client, auth_headers, vet_user):
    response = client.get("/api/v1/auth/users", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_list_users_non_admin(client, vet_headers):
    response = client.get("/api/v1/auth/users", headers=vet_headers)
    assert response.status_code == 403
