"""Add role_permissions and notifications tables, guest role

Revision ID: 003
Revises: 002
Create Date: 2026-03-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_tables = inspector.get_table_names()

    # Add 'guest' value to userrole enum if not present
    # PostgreSQL requires ALTER TYPE for enum extension
    try:
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'guest'")
    except Exception:
        pass

    # Create role_permissions table
    if 'role_permissions' not in existing_tables:
        op.create_table(
            'role_permissions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('role', sa.String(50), nullable=False, unique=True),
            sa.Column('permissions', sa.JSON(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # Create notifications table
    if 'notifications' not in existing_tables:
        op.create_table(
            'notifications',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), nullable=False, index=True),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('message', sa.String(1000)),
            sa.Column('notification_type', sa.String(50), server_default='info'),
            sa.Column('is_read', sa.Boolean(), server_default='false'),
            sa.Column('link', sa.String(255)),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade():
    op.drop_table('notifications')
    op.drop_table('role_permissions')
