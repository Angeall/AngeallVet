"""Vaccination protocols + automation (the `vaccine_protocols` module)."""
from datetime import date, timedelta

import pytest

import app.core.licensing as lic
from app.core.config import settings
from app.api.endpoints.vaccination import compute_next_due
from app.models.client import Client
from app.models.animal import Animal
from app.models.vaccination import VaccineProtocol, VaccineProtocolDose, Vaccination


@pytest.fixture
def set_modules(monkeypatch):
    priv, pub = lic.generate_keypair()
    monkeypatch.setattr(settings, "LICENSE_PUBLIC_KEY", pub)

    def _set(modules):
        monkeypatch.setattr(settings, "LICENSE", lic.sign_license(priv, modules) if modules else "")
    return _set


def _client_animal(db, email="jean@test.com"):
    cli = Client(first_name="Jean", last_name="Dupont", email=email)
    db.add(cli)
    db.flush()
    a = Animal(client_id=cli.id, name="Rex", species="dog")
    db.add(a)
    db.commit()
    return cli, a


# ─── next-due engine (unit) ──────────────────────────────────────────────────

def test_compute_next_due_series_and_booster():
    d1 = VaccineProtocolDose(id=1, sequence=0, label="Primo 1", valence="CHP", interval_days=0)
    d2 = VaccineProtocolDose(id=2, sequence=1, label="Primo 2", valence="CHP", interval_days=28)
    d3 = VaccineProtocolDose(id=3, sequence=2, label="Rappel", valence="CHP", interval_days=28, is_booster=True, booster_interval_days=365)
    proto = VaccineProtocol(name="Chiot", doses=[d1, d2, d3])

    assert compute_next_due(proto, d1, date(2026, 1, 1)) == (date(2026, 1, 29), "Primo 2")
    assert compute_next_due(proto, d3, date(2026, 1, 1)) == (date(2027, 1, 1), "Rappel CHP")


def test_compute_next_due_last_non_booster_is_none():
    d1 = VaccineProtocolDose(id=1, sequence=0, label="Unique", valence="X", interval_days=0)
    proto = VaccineProtocol(name="P", doses=[d1])
    assert compute_next_due(proto, d1, date(2026, 1, 1)) == (None, None)


# ─── protocols + recording (API) ─────────────────────────────────────────────

def test_protocol_crud_and_record_computes_due(client, auth_headers, db):
    _, a = _client_animal(db)
    proto = client.post("/api/v1/vaccinations/protocols", headers=auth_headers, json={
        "name": "Chiot CHP", "species": "dog", "doses": [
            {"sequence": 0, "label": "Primo 1", "valence": "CHPPiL", "interval_days": 0},
            {"sequence": 1, "label": "Primo 2", "valence": "CHPPiL", "interval_days": 28},
        ],
    }).json()
    assert len(proto["doses"]) == 2

    d1 = proto["doses"][0]["id"]
    r = client.post("/api/v1/vaccinations", headers=auth_headers, json={
        "animal_id": a.id, "protocol_id": proto["id"], "dose_id": d1, "date_administered": "2026-06-01",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["valence"] == "CHPPiL"          # taken from the dose
    assert body["next_due_date"] == "2026-06-29"  # +28 days
    assert "Primo 2" in (body["next_label"] or "")

    hist = client.get("/api/v1/vaccinations", headers=auth_headers, params={"animal_id": a.id}).json()
    assert len(hist) == 1


def test_due_list_keeps_latest_and_filters_window(client, auth_headers, db):
    _, a = _client_animal(db)
    db.add(Vaccination(animal_id=a.id, valence="CHP", date_administered=date.today() - timedelta(days=300), next_due_date=date.today() + timedelta(days=5)))
    db.add(Vaccination(animal_id=a.id, valence="Rage", date_administered=date.today() - timedelta(days=300), next_due_date=date.today() + timedelta(days=120)))
    db.commit()
    rows = client.get("/api/v1/vaccinations/due", headers=auth_headers, params={"within_days": 30}).json()
    valences = [x["valence"] for x in rows]
    assert "CHP" in valences          # due in 5 days
    assert "Rage" not in valences     # due in 120 days, outside the window
    assert rows[0]["animal_name"] == "Rex"


def test_vaccinations_gated_by_module(client, auth_headers, set_modules):
    set_modules([])
    assert client.get("/api/v1/vaccinations/protocols", headers=auth_headers).status_code == 403


# ─── automated reminder ──────────────────────────────────────────────────────

def test_vaccination_reminder_sends_once(db, monkeypatch):
    import app.core.reminders as rem
    sent = []
    monkeypatch.setattr(rem, "send_email", lambda *a, **k: sent.append(a))
    _, a = _client_animal(db)
    db.add(Vaccination(animal_id=a.id, valence="CHP", date_administered=date.today() - timedelta(days=350), next_due_date=date.today()))
    db.commit()

    c1 = rem.send_due_vaccination_reminders(db, "", lic.ALL_MODULES)
    assert c1["sent"] == 1
    assert len(sent) == 1
    # deduped on a second run
    assert rem.send_due_vaccination_reminders(db, "", lic.ALL_MODULES)["sent"] == 0


def test_vaccination_reminder_skipped_without_module(db):
    import app.core.reminders as rem
    _, a = _client_animal(db)
    db.add(Vaccination(animal_id=a.id, valence="CHP", date_administered=date.today(), next_due_date=date.today()))
    db.commit()
    assert rem.send_due_vaccination_reminders(db, "", frozenset())["sent"] == 0
