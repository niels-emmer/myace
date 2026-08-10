"""add_mfa_fields_to_users

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-10 11:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'd4e5f6a7b8c9'
down_revision: str | None = 'c3d4e5f6a7b8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), nullable=False,
                  server_default=sa.text('false')))
    op.add_column('users', sa.Column('totp_secret', sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'totp_secret')
    op.drop_column('users', 'mfa_enabled')
