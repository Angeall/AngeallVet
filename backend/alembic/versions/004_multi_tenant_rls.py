"""Add multi-tenant support: tenants table + tenant_id on users.

Each tenant gets its own PostgreSQL database. The central database
holds only the tenants and users tables. All clinic data (clients,
animals, invoices, etc.) lives in the tenant's dedicated database.

Revision ID: 004_multi_tenant_rls
Revises: 003_rbac_notifications
Create Date: 2026-03-10
"""
from alembic import op
import sqlalchemy as sa

revision = "004_multi_tenant_rls"
down_revision = "003_rbac_notifications"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create tenants table in the central database
    op.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(100) UNIQUE NOT NULL,
            database_url VARCHAR(500) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_tenants_slug ON tenants (slug)")

    # 2. Add tenant_id to users table (FK to tenants)
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE users ADD COLUMN tenant_id INTEGER REFERENCES tenants(id);
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_tenant_id ON users (tenant_id)")


def downgrade():
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS tenant_id")
    op.execute("DROP TABLE IF EXISTS tenants")
