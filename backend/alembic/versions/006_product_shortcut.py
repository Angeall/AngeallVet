"""Add is_shortcut flag to products for quick billing buttons.

Revision ID: 006_product_shortcut
Revises: 005_animal_vital_status
Create Date: 2026-03-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

revision = "006_product_shortcut"
down_revision = "005_animal_vital_status"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    # products is a tenant table — it may not exist in the central DB
    if "products" not in inspector.get_table_names():
        return

    existing_cols = [c["name"] for c in inspector.get_columns("products")]
    if "is_shortcut" in existing_cols:
        return  # Already applied (e.g. by _ensure_schema)

    op.add_column("products", sa.Column("is_shortcut", sa.Boolean(), nullable=False, server_default="false"))


def downgrade():
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    if "products" not in inspector.get_table_names():
        return
    op.drop_column("products", "is_shortcut")
