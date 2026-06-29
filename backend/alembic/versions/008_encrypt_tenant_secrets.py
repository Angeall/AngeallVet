"""Encrypt tenant secrets at rest with pgcrypto; drop stored auth_jwt_secret.

Encrypts `tenants.database_url` and `tenants.pb_admin_password` using pgcrypto
(pgp_sym_encrypt, base64-encoded into TEXT columns), keyed by ENCRYPTION_KEY.
The per-tenant JWT secret is no longer stored (always derived), so its column
is dropped.

Revision ID: 008_encrypt_tenant_secrets
Revises: 007_pocketbase_auth
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa

from app.core.config import settings

revision = "008_encrypt_tenant_secrets"
down_revision = "007_pocketbase_auth"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Widen secret columns to TEXT so they can hold base64(pgp) ciphertext.
    op.execute("ALTER TABLE tenants ALTER COLUMN database_url TYPE TEXT")
    op.execute("ALTER TABLE tenants ALTER COLUMN pb_admin_password TYPE TEXT")

    # Encrypt any pre-existing plaintext rows (no-op on an empty table).
    key = settings.ENCRYPTION_KEY
    if key:
        op.execute(
            sa.text(
                "UPDATE tenants SET database_url = encode(pgp_sym_encrypt(database_url, :k), 'base64') "
                "WHERE database_url IS NOT NULL"
            ).bindparams(k=key)
        )
        op.execute(
            sa.text(
                "UPDATE tenants SET pb_admin_password = encode(pgp_sym_encrypt(pb_admin_password, :k), 'base64') "
                "WHERE pb_admin_password IS NOT NULL"
            ).bindparams(k=key)
        )

    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS auth_jwt_secret")


def downgrade():
    key = settings.ENCRYPTION_KEY
    if key:
        op.execute(
            sa.text(
                "UPDATE tenants SET database_url = pgp_sym_decrypt(decode(database_url, 'base64'), :k) "
                "WHERE database_url IS NOT NULL"
            ).bindparams(k=key)
        )
        op.execute(
            sa.text(
                "UPDATE tenants SET pb_admin_password = pgp_sym_decrypt(decode(pb_admin_password, 'base64'), :k) "
                "WHERE pb_admin_password IS NOT NULL"
            ).bindparams(k=key)
        )
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS auth_jwt_secret VARCHAR(255)")
