"""Per-tenant paid-module entitlements, delivered as a cryptographically signed
license.

Why signed, and not a plain ``MODULE_SMS=true`` env flag: each clinic runs its
own Docker stack with its own ``.env``. A boolean flag in that file would be
trivially flippable by anyone with server access. Instead the *deployer* issues a
license — a token signed with an **Ed25519 private key that never leaves the
deployer's machine** — listing the modules the clinic paid for. The backend only
ever holds the matching **public** key, so it can *verify* a license but can
never *forge* one. Editing the ``.env`` to grant yourself a module is therefore
useless: without the private key you cannot produce a valid signature.

Configuration (per tenant ``.env``):
- ``LICENSE_PUBLIC_KEY`` — PEM of the Ed25519 public key. Safe to ship/commit
  (it only verifies). The same key is baked into every clinic's stack.
- ``LICENSE`` — the signed license token issued for *this* clinic.

Key generation and signing live in the CLI (``python -m app.licensing``) and use
the *private* key, which you keep off the deployed servers.

    python -m app.licensing keygen                       # once: make a key pair
    python -m app.licensing sign --key private.pem \\
        --tenant clinique-martin --modules sms,invoice_ninja --days 365
    python -m app.licensing inspect --token <token>      # decode (no verify)
"""
from __future__ import annotations

import logging
import time
from typing import Iterable, Optional

import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── Canonical module keys + French labels (single source of truth) ──────────
MODULE_INVOICE_NINJA = "invoice_ninja"
MODULE_SMS = "sms"
MODULE_GOOGLE_CALENDAR = "google_calendar"

MODULE_LABELS = {
    MODULE_INVOICE_NINJA: "Facturation avancée (Invoice Ninja / Peppol)",
    MODULE_SMS: "Rappels par SMS",
    MODULE_GOOGLE_CALENDAR: "Synchronisation Google Agenda",
}
ALL_MODULES = frozenset(MODULE_LABELS)

_ALG = "EdDSA"  # Ed25519 — asymmetric, so the verifier cannot re-sign.


class LicenseError(Exception):
    """Raised by the signing helpers (CLI side), never by verification."""


def _clean(modules: Iterable[str]) -> frozenset:
    """Keep only known module keys (drop unknown / mistyped entries)."""
    return frozenset(m for m in modules if m in ALL_MODULES)


def _normalize_pem(value: str) -> str:
    """Accept a PEM pasted into a .env with escaped newlines or quotes."""
    if not value:
        return ""
    value = value.strip().strip('"').strip("'")
    if "\\n" in value and "\n" not in value:
        value = value.replace("\\n", "\n")
    return value


# ─── Verification (runs in the app; PUBLIC key only) ─────────────────────────

def verify_license(token: str, *, expected_slug: Optional[str] = None) -> frozenset:
    """Verify a signed license and return the modules it grants.

    Fails **closed**: any signature / format / expiry / tenant-binding problem
    yields an empty set (no modules) rather than raising, so a tampered or
    missing license simply unlocks nothing.
    """
    public_key = _normalize_pem(settings.LICENSE_PUBLIC_KEY)
    if not token or not public_key:
        return frozenset()
    try:
        payload = jwt.decode(token, public_key, algorithms=[_ALG])
    except jwt.InvalidTokenError as exc:
        logger.warning("Licence refusée (signature/format/expiration): %s", exc)
        return frozenset()

    # Anti-copy: a license bound to a tenant (``sub``) is valid only for that
    # tenant, so clinic A's paid license can't be dropped into clinic B's .env.
    sub = payload.get("sub")
    if sub and expected_slug and sub != expected_slug:
        logger.warning("Licence refusée : liée au tenant %r, pas %r", sub, expected_slug)
        return frozenset()

    return _clean(payload.get("modules") or [])


def resolve_modules(slug: str, license_token: str) -> frozenset:
    """Resolve the effective module set for a tenant.

    - A valid signed license is the ONLY way to enable modules in production.
    - In a dev/test environment with **no public key configured**, all modules
      are enabled so local development and the test-suite see the full app
      (optionally narrowed by ``DEV_MODULES``).
    """
    if settings.LICENSE_PUBLIC_KEY:
        # A verification key is configured → modules come strictly from a valid
        # signed license, in every environment.
        return verify_license(license_token, expected_slug=slug)
    if settings.is_dev_env:
        if settings.DEV_MODULES:
            return _clean(m.strip() for m in settings.DEV_MODULES.split(",") if m.strip())
        return ALL_MODULES
    # Production with no public key set: nothing is unlocked (fail closed).
    return frozenset()


# ─── Signing & key generation (deployer side — needs the PRIVATE key) ────────

def generate_keypair() -> tuple:
    """Return ``(private_pem, public_pem)`` for a fresh Ed25519 key pair."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    priv = Ed25519PrivateKey.generate()
    private_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


def sign_license(
    private_key_pem: str,
    modules: Iterable[str],
    *,
    tenant: Optional[str] = None,
    days: Optional[int] = None,
) -> str:
    """Sign a license token. Run on the deployer's machine with the private key."""
    mods = sorted(_clean(modules))
    if not mods:
        raise LicenseError("Aucun module valide. Connus : " + ", ".join(sorted(ALL_MODULES)))
    now = int(time.time())
    payload = {"modules": mods, "iat": now}
    if tenant:
        payload["sub"] = tenant
    if days:
        payload["exp"] = now + days * 86400
    return jwt.encode(payload, _normalize_pem(private_key_pem), algorithm=_ALG)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def _main() -> None:  # pragma: no cover - operational tooling
    import argparse
    import sys

    parser = argparse.ArgumentParser(prog="python -m app.licensing")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("keygen", help="Generate a new Ed25519 key pair")

    sign = sub.add_parser("sign", help="Sign a license (needs the private key)")
    sign.add_argument("--key", required=True, help="Path to the private key PEM, or '-' for stdin")
    sign.add_argument("--modules", required=True, help="Comma list, e.g. sms,invoice_ninja,google_calendar")
    sign.add_argument("--tenant", help="Bind the license to this tenant slug (recommended)")
    sign.add_argument("--days", type=int, help="Validity in days (omit = perpetual)")

    inspect = sub.add_parser("inspect", help="Decode a token WITHOUT verifying")
    inspect.add_argument("--token", required=True)

    args = parser.parse_args()

    if args.cmd == "keygen":
        private_pem, public_pem = generate_keypair()
        escaped = public_pem.strip().replace("\n", "\\n")
        print("─" * 70)
        print("PRIVATE KEY — keep OFF the servers, this is what signs licenses:\n")
        print(private_pem)
        print("─" * 70)
        print("PUBLIC KEY — ship this in every clinic's .env (LICENSE_PUBLIC_KEY):\n")
        print(public_pem)
        print("One-line form for .env:\n")
        print(f'LICENSE_PUBLIC_KEY="{escaped}"')
        return

    if args.cmd == "sign":
        key = sys.stdin.read() if args.key == "-" else open(args.key, "r", encoding="utf-8").read()
        modules = [m.strip() for m in args.modules.split(",") if m.strip()]
        token = sign_license(key, modules, tenant=args.tenant, days=args.days)
        print(token)
        return

    if args.cmd == "inspect":
        claims = jwt.decode(args.token, options={"verify_signature": False})
        import json
        print(json.dumps(claims, indent=2, ensure_ascii=False))


if __name__ == "__main__":  # pragma: no cover
    _main()
