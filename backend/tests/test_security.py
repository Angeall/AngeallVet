"""Security regression tests for the multi-tenant auth hardening."""
import uuid
from unittest.mock import patch

import pytest


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


def test_resolve_tenant_context_strict_rejects_unknown_subdomain():
    """A central multi-tenant stack must not fail-open onto the central DB: an
    unknown sub-domain resolves to None (rejected), never the default tenant."""
    from app.core.tenancy import resolve_tenant_context

    # Bare/default host = single-clinic default tenant, even in strict mode.
    assert resolve_tenant_context("angeallvet.localhost", strict=True).is_default
    assert resolve_tenant_context("", strict=True).is_default
    # Unknown sub-domain: rejected in strict mode, lenient fallback otherwise.
    assert resolve_tenant_context("ghost.angeallvet.localhost", strict=True) is None
    assert resolve_tenant_context("ghost.angeallvet.localhost", strict=False).is_default


def _token_for(db, role):
    """Mint an app token for a freshly created user of the given role."""
    from app.models.user import User, UserRole
    from app.core.security import create_app_token
    from app.core.tenancy import derive_tenant_secret
    from app.core.config import settings

    u = User(pb_user_id=str(uuid.uuid4()), email=f"{role}@test.com",
             first_name="T", last_name=role.title(), role=UserRole(role), is_active=True)
    db.add(u)
    db.commit()
    return create_app_token(u.pb_user_id, derive_tenant_secret(settings.DEFAULT_TENANT_SLUG))


def test_section_permission_gates_writes_not_reads(client, db):
    """H1: the role/section matrix is enforced server-side for writes. A `guest`
    (clients=False, animals=False) is refused writes but reads stay open so
    cross-section lookups keep working."""
    h = {"Authorization": f"Bearer {_token_for(db, 'guest')}"}
    # Write in a forbidden section → 403 (was silently accepted before).
    assert client.delete("/api/v1/clients/999999", headers=h).status_code == 403
    # Reads remain open (needed for dropdowns / invoicing lookups).
    assert client.get("/api/v1/clients", headers=h).status_code == 200
    assert client.get("/api/v1/animals", headers=h).status_code == 200


def test_admin_bypasses_section_matrix(client, auth_headers):
    """ADMIN always passes the section gate — a write reaches the handler
    (404 for a missing id), i.e. it is not blocked by the matrix (403)."""
    assert client.get("/api/v1/clients", headers=auth_headers).status_code == 200
    assert client.delete("/api/v1/clients/999999", headers=auth_headers).status_code == 404


def test_payment_amount_must_be_positive(client, auth_headers):
    """H2: negative/zero monetary amounts are rejected (schema validation)."""
    for amount in (-5, 0):
        r = client.post("/api/v1/billing/payments", headers=auth_headers,
                        json={"invoice_id": 1, "amount": amount, "payment_method": "cash"})
        assert r.status_code == 422, amount


def test_vaccination_record_requires_vet(client, db):
    """M2: recording a vaccination is a veterinary act — an assistant is refused
    (has the 'animals' section, but not the vet role floor)."""
    h = {"Authorization": f"Bearer {_token_for(db, 'assistant')}"}
    r = client.post("/api/v1/vaccinations", headers=h,
                    json={"animal_id": 1, "date_administered": "2026-07-01"})
    assert r.status_code == 403


def test_cash_close_rejects_future_date(client, auth_headers):
    """M3: the cash ledger cannot be written in the future."""
    r = client.post("/api/v1/accounting/cash/close", headers=auth_headers,
                    json={"business_date": "2099-01-01", "opening_amount": 0, "counted_amount": 0})
    assert r.status_code == 400


def test_cross_vet_invoice_edit_setting(client, db):
    """M1: editing another vet's invoice attribution is a clinic setting (default
    allowed = trusted). When disabled, a non-admin may only touch their own."""
    from app.api.endpoints.billing import _guard_cross_vet_edit
    from app.models.settings import ClinicSettings
    from app.models.user import User, UserRole

    vet = User(pb_user_id=str(uuid.uuid4()), email="v@test.com", first_name="V",
               last_name="T", role=UserRole.VETERINARIAN, is_active=True)
    db.add(vet)
    db.commit()

    # Default (no settings row) → trusted: editing a colleague's attribution is fine.
    _guard_cross_vet_edit(db, vet, 99999)

    # Disabled → a vet may only (de)associate themselves.
    db.add(ClinicSettings(allow_cross_vet_invoice_edit=False))
    db.commit()
    with pytest.raises(Exception):
        _guard_cross_vet_edit(db, vet, 99999)
    _guard_cross_vet_edit(db, vet, vet.id)  # self is always allowed


def test_unknown_tenant_rejected_in_strict_multitenant(client, monkeypatch):
    """In production + MULTI_TENANT, a request for an unknown tenant sub-domain is
    rejected (404) rather than silently served the default/central database."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "MULTI_TENANT", True)
    r = client.get("/api/v1/animals", headers={"host": "ghost.angeallvet.localhost"})
    assert r.status_code == 404
    assert r.json()["detail"] == "Tenant inconnu"
