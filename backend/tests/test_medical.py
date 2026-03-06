import pytest


@pytest.fixture
def sample_animal(client, auth_headers):
    cl_res = client.post("/api/v1/clients", headers=auth_headers, json={
        "first_name": "Jean", "last_name": "Dupont",
    })
    an_res = client.post("/api/v1/animals", headers=auth_headers, json={
        "client_id": cl_res.json()["id"], "name": "Rex", "species": "dog",
    })
    return an_res.json()


def test_create_medical_record(client, vet_headers, sample_animal):
    response = client.post("/api/v1/medical/records", headers=vet_headers, json={
        "animal_id": sample_animal["id"],
        "record_type": "consultation",
        "subjective": "Propriétaire rapporte vomissements depuis 2 jours",
        "objective": "T: 38.5°C, Abdomen sensible à la palpation",
        "assessment": "Gastro-entérite aiguë",
        "plan": "Diète 24h, anti-émétique, contrôle J+3",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["record_type"] == "consultation"
    assert data["assessment"] == "Gastro-entérite aiguë"


def test_create_record_with_prescription(client, vet_headers, sample_animal):
    response = client.post("/api/v1/medical/records", headers=vet_headers, json={
        "animal_id": sample_animal["id"],
        "record_type": "consultation",
        "subjective": "Infection urinaire",
        "assessment": "Cystite bactérienne",
        "prescriptions": [{
            "notes": "Traitement antibiotique",
            "items": [{
                "medication_name": "Amoxicilline",
                "dosage": "250mg",
                "dosage_per_kg": 12.5,
                "frequency": "2x/jour",
                "duration": "7 jours",
                "quantity": 14,
            }],
        }],
    })
    assert response.status_code == 201
    assert len(response.json()["prescriptions"]) == 1
    assert len(response.json()["prescriptions"][0]["items"]) == 1


def test_create_consultation_template(client, vet_headers):
    response = client.post("/api/v1/medical/templates", headers=vet_headers, json={
        "name": "Vaccin annuel chien",
        "category": "vaccination",
        "species": "dog",
        "subjective": "Rappel vaccin annuel",
        "objective": "Examen clinique normal, T: 38.5°C",
        "assessment": "Animal en bonne santé, apte à la vaccination",
        "plan": "Injection CHPPiL + Rage. Rappel dans 1 an.",
    })
    assert response.status_code == 201
    assert response.json()["name"] == "Vaccin annuel chien"


def test_list_templates(client, vet_headers):
    client.post("/api/v1/medical/templates", headers=vet_headers, json={
        "name": "Template 1", "category": "vaccination",
    })
    client.post("/api/v1/medical/templates", headers=vet_headers, json={
        "name": "Template 2", "category": "surgery",
    })
    response = client.get("/api/v1/medical/templates", headers=vet_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2
