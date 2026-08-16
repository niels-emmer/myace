"""add_role_to_users

Revision ID: d0e1f2a3b4c5
Revises: b8c9d0e1f2a3
Create Date: 2026-08-16 09:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'd0e1f2a3b4c5'
down_revision: str | None = 'b8c9d0e1f2a3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('role', sa.String(length=32), nullable=False, server_default='user'),
    )
    op.execute("UPDATE users SET role = 'admin' WHERE is_admin = true")


def downgrade() -> None:
    op.drop_column('users', 'role')
