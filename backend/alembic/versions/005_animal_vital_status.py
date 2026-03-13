"""Add vital_status and vital_status_date to animals.

Replace boolean is_deceased with a proper vital status enum (alive, lost, deceased).
Keeps is_deceased and deceased_date for backwards compatibility during transition.

Revision ID: 005_animal_vital_status
Revises: 004_multi_tenant_rls
Create Date: 2026-03-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

revision = "005_animal_vital_status"
down_revision = "004_multi_tenant_rls"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    # animals is a tenant table — it may not exist in the central DB
    if "animals" not in inspector.get_table_names():
        return

    existing_cols = [c["name"] for c in inspector.get_columns("animals")]
    if "vital_status" in existing_cols:
        return  # Already applied (e.g. by _ensure_schema)

    vital_status_enum = sa.Enum("alive", "lost", "deceased", name="vitalstatus")
    vital_status_enum.create(bind, checkfirst=True)

    op.add_column("animals", sa.Column("vital_status", vital_status_enum, nullable=False, server_default="alive"))
    op.add_column("animals", sa.Column("vital_status_date", sa.Date(), nullable=True))

    # Migrate existing data: is_deceased=True → vital_status='deceased'
    op.execute(
        "UPDATE animals SET vital_status = 'deceased', vital_status_date = deceased_date "
        "WHERE is_deceased = true"
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    if "animals" not in inspector.get_table_names():
        return
    op.drop_column("animals", "vital_status_date")
    op.drop_column("animals", "vital_status")
    sa.Enum(name="vitalstatus").drop(bind, checkfirst=True)
