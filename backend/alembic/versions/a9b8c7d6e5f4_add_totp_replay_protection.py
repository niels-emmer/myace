"""add_totp_replay_protection

Revision ID: a9b8c7d6e5f4
Revises: e2f3a4b5c6d7
Create Date: 2026-10-22 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'a9b8c7d6e5f4'
down_revision: str | None = 'e2f3a4b5c6d7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('last_totp_counter', sa.Integer(), nullable=True))
    op.add_column(
        'users', sa.Column('mfa_token_used_hash', sa.String(length=64), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('users', 'mfa_token_used_hash')
    op.drop_column('users', 'last_totp_counter')
