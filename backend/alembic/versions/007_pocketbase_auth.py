"""Switch auth from Supabase to tenant-local PocketBase.

* Adds PocketBase / sub-domain columns to the central `tenants` table.
* Renames `users.supabase_uid` -> `users.pb_user_id`.

Revision ID: 007_pocketbase_auth
Revises: 006_product_shortcut
Create Date: 2026-06-29
"""
from alembic import op

revision = "007_pocketbase_auth"
down_revision = "006_product_shortcut"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Tenant auth columns (idempotent — guarded against re-runs)
    op.execute(
        """
        DO $$ BEGIN
            ALTER TABLE tenants ADD COLUMN subdomain VARCHAR(100);
        EXCEPTION WHEN duplicate_column THEN NULL; END $$
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_tenants_subdomain ON tenants (subdomain)")
    for col, ddl in [
        ("pocketbase_url", "ALTER TABLE tenants ADD COLUMN pocketbase_url VARCHAR(500)"),
        ("pb_admin_email", "ALTER TABLE tenants ADD COLUMN pb_admin_email VARCHAR(255)"),
        ("pb_admin_password", "ALTER TABLE tenants ADD COLUMN pb_admin_password VARCHAR(255)"),
        ("auth_jwt_secret", "ALTER TABLE tenants ADD COLUMN auth_jwt_secret VARCHAR(255)"),
    ]:
        op.execute(
            f"DO $$ BEGIN {ddl}; EXCEPTION WHEN duplicate_column THEN NULL; END $$"
        )

    # 2. Rename users.supabase_uid -> users.pb_user_id (only if needed)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'supabase_uid'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'pb_user_id'
            ) THEN
                ALTER TABLE users RENAME COLUMN supabase_uid TO pb_user_id;
            END IF;
        END $$
        """
    )


def downgrade():
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'pb_user_id'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'supabase_uid'
            ) THEN
                ALTER TABLE users RENAME COLUMN pb_user_id TO supabase_uid;
            END IF;
        END $$
        """
    )
    op.execute("DROP INDEX IF EXISTS ix_tenants_subdomain")
    for col in ("subdomain", "pocketbase_url", "pb_admin_email", "pb_admin_password", "auth_jwt_secret"):
        op.execute(f"ALTER TABLE tenants DROP COLUMN IF EXISTS {col}")
