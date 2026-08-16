"""add_collection_freshness_verification

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-08-16 15:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'e2f3a4b5c6d7'
down_revision: str | None = 'd1e2f3a4b5c6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('collections', sa.Column('last_verified_at', sa.Date(), nullable=True))
    op.add_column(
        'collections',
        sa.Column('verified_by', sa.Uuid(), sa.ForeignKey('users.id'), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('collections', 'verified_by')
    op.drop_column('collections', 'last_verified_at')
