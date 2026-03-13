"""Tests for animal vital status (alive, lost, deceased)."""
import pytest


@pytest.fixture
def sample_client(client, auth_headers):
    res = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Jean", "last_name": "Dupont",
    })
    return res.json()


@pytest.fixture
def sample_animal(client, auth_headers, sample_client):
    res = client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": sample_client["id"],
        "name": "Rex",
        "species": "dog",
        "sex": "male",
    })
    assert res.status_code == 201
    return res.json()


def test_animal_default_vital_status(sample_animal):
    """New animals should default to 'alive' vital status."""
    assert sample_animal["vital_status"] == "alive"
    assert sample_animal["vital_status_date"] is None


def test_set_vital_status_deceased(client, auth_headers, sample_animal):
    """Mark an animal as deceased with a date."""
    res = client.put(
        f"/api/v1/animals/{sample_animal['id']}",
        headers=auth_headers,
        json={
            "vital_status": "deceased",
            "vital_status_date": "2026-03-10",
            "is_deceased": True,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["vital_status"] == "deceased"
    assert data["vital_status_date"] == "2026-03-10"
    assert data["is_deceased"] is True


def test_set_vital_status_lost(client, auth_headers, sample_animal):
    """Mark an animal as lost."""
    res = client.put(
        f"/api/v1/animals/{sample_animal['id']}",
        headers=auth_headers,
        json={
            "vital_status": "lost",
            "vital_status_date": "2026-03-01",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["vital_status"] == "lost"
    assert data["vital_status_date"] == "2026-03-01"


def test_revert_vital_status_to_alive(client, auth_headers, sample_animal):
    """Revert a lost animal back to alive."""
    # First mark as lost
    client.put(
        f"/api/v1/animals/{sample_animal['id']}",
        headers=auth_headers,
        json={"vital_status": "lost", "vital_status_date": "2026-03-01"},
    )
    # Revert to alive
    res = client.put(
        f"/api/v1/animals/{sample_animal['id']}",
        headers=auth_headers,
        json={"vital_status": "alive", "vital_status_date": None},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["vital_status"] == "alive"
    assert data["vital_status_date"] is None


def test_vital_status_persists_on_get(client, auth_headers, sample_animal):
    """Vital status should persist and be visible on GET."""
    client.put(
        f"/api/v1/animals/{sample_animal['id']}",
        headers=auth_headers,
        json={"vital_status": "deceased", "vital_status_date": "2026-03-13"},
    )
    res = client.get(f"/api/v1/animals/{sample_animal['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["vital_status"] == "deceased"
    assert res.json()["vital_status_date"] == "2026-03-13"


def test_client_animals_include_vital_status(client, auth_headers, sample_client):
    """Animals listed for a client should include vital_status."""
    # Create two animals with different statuses
    a1 = client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": sample_client["id"], "name": "Rex", "species": "dog",
    }).json()
    a2 = client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": sample_client["id"], "name": "Minou", "species": "cat",
    }).json()

    # Mark one as deceased
    client.put(f"/api/v1/animals/{a2['id']}", headers=auth_headers, json={
        "vital_status": "deceased", "vital_status_date": "2026-01-15",
    })

    res = client.get(f"/api/v1/animals?client_id={sample_client['id']}", headers=auth_headers)
    assert res.status_code == 200
    animals = res.json()
    statuses = {a["name"]: a["vital_status"] for a in animals}
    assert statuses["Rex"] == "alive"
    assert statuses["Minou"] == "deceased"
