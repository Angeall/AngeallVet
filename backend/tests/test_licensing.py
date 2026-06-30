"""Tests for the signed paid-module license (Ed25519)."""
import pytest

import app.core.licensing as lic
from app.core.config import settings


@pytest.fixture
def keys(monkeypatch):
    """Generate a key pair and configure its public key on the app."""
    priv, pub = lic.generate_keypair()
    monkeypatch.setattr(settings, "LICENSE_PUBLIC_KEY", pub)
    return priv, pub


def test_sign_and_verify_roundtrip(keys):
    priv, _ = keys
    token = lic.sign_license(priv, ["sms", "invoice_ninja"])
    assert lic.verify_license(token) == frozenset({"sms", "invoice_ninja"})


def test_unknown_modules_are_dropped(keys):
    priv, _ = keys
    token = lic.sign_license(priv, ["sms", "telepathy"])
    assert lic.verify_license(token) == frozenset({"sms"})


def test_tampered_token_unlocks_nothing(keys):
    priv, _ = keys
    token = lic.sign_license(priv, ["sms", "invoice_ninja"])
    assert lic.verify_license(token[:-4] + "AAAA") == frozenset()


def test_token_signed_by_a_different_key_is_rejected(keys):
    # Anyone editing the .env can paste a token, but only the deployer's private
    # key produces one the configured public key accepts.
    other_priv, _ = lic.generate_keypair()
    forged = lic.sign_license(other_priv, ["sms", "invoice_ninja"])
    assert lic.verify_license(forged) == frozenset()


def test_tenant_binding(keys):
    priv, _ = keys
    token = lic.sign_license(priv, ["sms"], tenant="clinique-a")
    assert lic.verify_license(token, expected_slug="clinique-a") == frozenset({"sms"})
    # Same token dropped into clinique-b's stack unlocks nothing.
    assert lic.verify_license(token, expected_slug="clinique-b") == frozenset()


def test_expired_license_rejected(keys):
    priv, _ = keys
    token = lic.sign_license(priv, ["sms"], days=-1)  # exp in the past
    assert lic.verify_license(token) == frozenset()


def test_no_token_unlocks_nothing(keys):
    assert lic.verify_license("") == frozenset()


def test_production_without_public_key_is_empty(monkeypatch):
    monkeypatch.setattr(settings, "LICENSE_PUBLIC_KEY", "")
    monkeypatch.setattr(settings, "APP_ENV", "production")
    assert lic.resolve_modules("default", "") == frozenset()


def test_dev_without_public_key_unlocks_all(monkeypatch):
    monkeypatch.setattr(settings, "LICENSE_PUBLIC_KEY", "")
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "DEV_MODULES", "")
    assert lic.resolve_modules("default", "") == lic.ALL_MODULES


def test_dev_modules_override(monkeypatch):
    monkeypatch.setattr(settings, "LICENSE_PUBLIC_KEY", "")
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "DEV_MODULES", "sms, invoice_ninja")
    assert lic.resolve_modules("default", "") == frozenset({"sms", "invoice_ninja"})


def test_configured_key_ignores_dev_default(monkeypatch):
    # As soon as a public key is set, modules come strictly from a valid license
    # even in dev — no implicit all-on.
    priv, pub = lic.generate_keypair()
    monkeypatch.setattr(settings, "LICENSE_PUBLIC_KEY", pub)
    monkeypatch.setattr(settings, "APP_ENV", "development")
    assert lic.resolve_modules("default", "") == frozenset()
    token = lic.sign_license(priv, ["sms"])
    assert lic.resolve_modules("default", token) == frozenset({"sms"})


# ─── Seat cap (max_users) ────────────────────────────────────────────────────

def test_license_grants_max_users(keys):
    priv, _ = keys
    token = lic.sign_license(priv, ["sms"], max_users=5)
    assert lic.resolve_max_users("default", token) == 5


def test_license_cap_only_no_modules(keys):
    priv, _ = keys
    token = lic.sign_license(priv, [], max_users=3)  # a cap-only license is valid
    assert lic.resolve_max_users("default", token) == 3
    assert lic.verify_license(token) == frozenset()


def test_max_users_unlimited_when_absent(keys):
    priv, _ = keys
    token = lic.sign_license(priv, ["sms"])  # no max_users claim → unlimited
    assert lic.resolve_max_users("default", token) == 0


def test_max_users_tampered_is_zero(keys):
    priv, _ = keys
    token = lic.sign_license(priv, ["sms"], max_users=5)
    assert lic.resolve_max_users("default", token[:-4] + "AAAA") == 0


def test_max_users_env_fallback_without_key(monkeypatch):
    monkeypatch.setattr(settings, "LICENSE_PUBLIC_KEY", "")
    monkeypatch.setattr(settings, "MAX_USERS", 4)
    assert lic.resolve_max_users("default", "") == 4


def test_sign_rejects_empty_license(keys):
    priv, _ = keys
    with pytest.raises(lic.LicenseError):
        lic.sign_license(priv, [])  # no modules and no cap = pointless
