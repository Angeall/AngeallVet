"""Tests for the Excel export endpoints."""

XLSX = "spreadsheetml"


def test_generic_xlsx_export(client, auth_headers):
    r = client.post("/api/v1/export/xlsx", headers=auth_headers, json={
        "filename": "stats",
        "sheets": [{"title": "Synthese", "headers": ["A", "B"], "rows": [[1, "x"], [2, "y"]]}],
    })
    assert r.status_code == 200
    assert XLSX in r.headers["content-type"]
    assert r.headers["content-disposition"].endswith('.xlsx"')
    assert len(r.content) > 0


def test_generic_xlsx_requires_auth(client):
    r = client.post("/api/v1/export/xlsx", json={"sheets": []})
    assert r.status_code == 401


def test_backup_returns_xlsx(client, auth_headers):
    r = client.get("/api/v1/export/backup", headers=auth_headers)
    assert r.status_code == 200
    assert XLSX in r.headers["content-type"]
    assert len(r.content) > 0


def test_backup_is_admin_only(client, vet_headers):
    r = client.get("/api/v1/export/backup", headers=vet_headers)
    assert r.status_code == 403
