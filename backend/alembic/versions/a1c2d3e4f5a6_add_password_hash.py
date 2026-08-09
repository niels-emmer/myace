"""add_password_hash

Revision ID: a1c2d3e4f5a6
Revises: 14d0f63dc5bd
Create Date: 2026-08-08 20:30:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'a1c2d3e4f5a6'
down_revision: str | None = '14d0f63dc5bd'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'password_hash')
