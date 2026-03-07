"""001 - add ean13 and notes to products

Revision ID: 001_product_ean13_notes
Revises: None
Create Date: 2026-03-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_product_ean13_notes'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Conditionally add columns (safe if they already exist from create_all)
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Check if 'products' table exists at all
    if 'products' not in inspector.get_table_names():
        return  # create_all will handle the full table creation

    existing_columns = [c['name'] for c in inspector.get_columns('products')]

    if 'ean13' not in existing_columns:
        op.add_column('products', sa.Column('ean13', sa.String(13), nullable=True))

    if 'notes' not in existing_columns:
        op.add_column('products', sa.Column('notes', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('products', 'notes')
    op.drop_column('products', 'ean13')
