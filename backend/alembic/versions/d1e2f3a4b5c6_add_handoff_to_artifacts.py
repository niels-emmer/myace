"""add_handoff_to_artifacts

Revision ID: d1e2f3a4b5c6
Revises: c5d6e7f8a9b0
Create Date: 2026-08-16 13:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'd1e2f3a4b5c6'
down_revision: str | None = 'c5d6e7f8a9b0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('artifacts', sa.Column('handoff_to', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('artifacts', 'handoff_to')
