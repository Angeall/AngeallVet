"""002 - add home_treatment to medical_records

Revision ID: 002_medical_home_treatment
Revises: 001_product_ean13_notes
Create Date: 2026-03-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_medical_home_treatment'
down_revision: Union[str, None] = '001_product_ean13_notes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'medical_records' not in inspector.get_table_names():
        return

    existing_columns = [c['name'] for c in inspector.get_columns('medical_records')]

    if 'home_treatment' not in existing_columns:
        op.add_column('medical_records', sa.Column('home_treatment', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('medical_records', 'home_treatment')
