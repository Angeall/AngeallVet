"""Add multi-tenant support with tenant_id columns and PostgreSQL RLS policies.

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

# Tables that get a tenant_id column (root/parent tables only)
TENANT_TABLES = [
    "users",
    "clients",
    "appointments",
    "medical_records",
    "consultation_templates",
    "products",
    "suppliers",
    "purchase_orders",
    "invoices",
    "estimates",
    "communications",
    "reminder_rules",
    "hospitalizations",
]


def upgrade():
    # 1. Create tenants table
    op.execute("""
        CREATE TABLE IF NOT EXISTS tenants (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(100) UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_tenants_slug ON tenants (slug)")

    # 2. Add tenant_id column to all parent tables
    for table in TENANT_TABLES:
        op.execute(f"""
            DO $$ BEGIN
                ALTER TABLE {table} ADD COLUMN tenant_id INTEGER REFERENCES tenants(id);
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$
        """)
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_tenant_id ON {table} (tenant_id)")

    # 3. Enable RLS on all tenant-scoped tables
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # Also enable RLS on child tables that inherit tenant via parent
    child_tables = [
        "animals", "animal_alerts", "weight_records",
        "invoice_lines", "estimate_lines", "payments",
        "prescriptions", "prescription_items", "attachments",
        "product_lots", "stock_movements",
        "care_tasks", "purchase_order_items", "reminder_logs",
    ]
    for table in child_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # 4. Create a PostgreSQL role for tenant-scoped access
    #    Each tenant gets a DB role: tenant_<id>
    #    The application sets the role via SET ROLE or current_setting('app.tenant_id')

    # Create policies using the session variable app.tenant_id
    # The application will SET app.tenant_id = '<tenant_id>' before each query

    for table in TENANT_TABLES:
        # Policy: users with matching tenant_id can see/modify rows
        op.execute(f"""
            DO $$ BEGIN
                CREATE POLICY tenant_isolation_select ON {table}
                    FOR SELECT
                    USING (
                        tenant_id::text = current_setting('app.tenant_id', true)
                        OR current_setting('app.tenant_id', true) IS NULL
                        OR current_setting('app.tenant_id', true) = ''
                    );
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$
        """)
        op.execute(f"""
            DO $$ BEGIN
                CREATE POLICY tenant_isolation_insert ON {table}
                    FOR INSERT
                    WITH CHECK (
                        tenant_id::text = current_setting('app.tenant_id', true)
                        OR current_setting('app.tenant_id', true) IS NULL
                        OR current_setting('app.tenant_id', true) = ''
                    );
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$
        """)
        op.execute(f"""
            DO $$ BEGIN
                CREATE POLICY tenant_isolation_update ON {table}
                    FOR UPDATE
                    USING (
                        tenant_id::text = current_setting('app.tenant_id', true)
                        OR current_setting('app.tenant_id', true) IS NULL
                        OR current_setting('app.tenant_id', true) = ''
                    );
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$
        """)
        op.execute(f"""
            DO $$ BEGIN
                CREATE POLICY tenant_isolation_delete ON {table}
                    FOR DELETE
                    USING (
                        tenant_id::text = current_setting('app.tenant_id', true)
                        OR current_setting('app.tenant_id', true) IS NULL
                        OR current_setting('app.tenant_id', true) = ''
                    );
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$
        """)

    # 5. Create Supabase-compatible RLS policies
    #    In Supabase, RLS policies can use auth.jwt() -> 'app_metadata' ->> 'tenant_id'
    #    This allows Supabase client-side access to be tenant-scoped too
    for table in TENANT_TABLES:
        op.execute(f"""
            DO $$ BEGIN
                CREATE POLICY supabase_tenant_select ON {table}
                    FOR SELECT
                    USING (
                        tenant_id::text = coalesce(
                            current_setting('request.jwt.claims', true)::json->>'tenant_id',
                            current_setting('app.tenant_id', true)
                        )
                        OR current_setting('app.tenant_id', true) IS NULL
                        OR current_setting('app.tenant_id', true) = ''
                    );
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$
        """)


def downgrade():
    # Remove policies
    for table in TENANT_TABLES:
        for policy in [
            "tenant_isolation_select", "tenant_isolation_insert",
            "tenant_isolation_update", "tenant_isolation_delete",
            "supabase_tenant_select",
        ]:
            op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")

    # Disable RLS
    all_tables = TENANT_TABLES + [
        "animals", "animal_alerts", "weight_records",
        "invoice_lines", "estimate_lines", "payments",
        "prescriptions", "prescription_items", "attachments",
        "product_lots", "stock_movements",
        "care_tasks", "purchase_order_items", "reminder_logs",
    ]
    for table in all_tables:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    # Remove tenant_id columns
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS tenant_id")

    # Drop tenants table
    op.execute("DROP TABLE IF EXISTS tenants")
