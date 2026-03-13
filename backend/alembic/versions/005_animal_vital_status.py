"""Add vital_status and vital_status_date to animals.

Replace boolean is_deceased with a proper vital status enum (alive, lost, deceased).
Keeps is_deceased and deceased_date for backwards compatibility during transition.

Revision ID: 005_animal_vital_status
Revises: 004_multi_tenant_rls
Create Date: 2026-03-13
"""
from alembic import op
import sqlalchemy as sa

revision = "005_animal_vital_status"
down_revision = "004_multi_tenant_rls"
branch_labels = None
depends_on = None


def upgrade():
    # Create the enum type
    vital_status_enum = sa.Enum("alive", "lost", "deceased", name="vitalstatus")
    vital_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column("animals", sa.Column("vital_status", vital_status_enum, nullable=False, server_default="alive"))
    op.add_column("animals", sa.Column("vital_status_date", sa.Date(), nullable=True))

    # Migrate existing data: is_deceased=True → vital_status='deceased'
    op.execute(
        "UPDATE animals SET vital_status = 'deceased', vital_status_date = deceased_date "
        "WHERE is_deceased = true"
    )


def downgrade():
    op.drop_column("animals", "vital_status_date")
    op.drop_column("animals", "vital_status")
    sa.Enum(name="vitalstatus").drop(op.get_bind(), checkfirst=True)
