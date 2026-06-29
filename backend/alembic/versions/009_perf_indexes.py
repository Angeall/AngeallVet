"""Performance indexes: pg_trgm trigram search + composite indexes.

Mirrors the runtime index-ensure step in app.main (which also applies these to
each tenant database). See app.core.db_indexes for the shared DDL.

Revision ID: 009_perf_indexes
Revises: 008_encrypt_tenant_secrets
Create Date: 2026-06-29
"""
from alembic import op

from app.core.db_indexes import PG_TRGM_EXTENSION, PERF_INDEXES

revision = "009_perf_indexes"
down_revision = "008_encrypt_tenant_secrets"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(PG_TRGM_EXTENSION)
    for _table, ddl in PERF_INDEXES:
        op.execute(ddl)


def downgrade():
    for name in (
        "ix_clients_last_name_trgm",
        "ix_clients_first_name_trgm",
        "ix_animals_name_trgm",
        "ix_products_name_trgm",
        "ix_notifications_user_id_is_read",
        "ix_medical_records_animal_created",
        "ix_weight_records_animal_recorded",
        "ix_appointments_vet_start",
        "ix_cse_product_date",
    ):
        op.execute(f"DROP INDEX IF EXISTS {name}")
