"""add_disabled_adapters

Revision ID: b8c9d0e1f2a3
Revises: e5f6a7b8c9d0
Create Date: 2026-08-12 11:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b8c9d0e1f2a3'
down_revision: str | None = 'e5f6a7b8c9d0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'system_settings',
        sa.Column('disabled_adapters', sa.Text(), nullable=False, server_default='[]'),
    )


def downgrade() -> None:
    op.drop_column('system_settings', 'disabled_adapters')
