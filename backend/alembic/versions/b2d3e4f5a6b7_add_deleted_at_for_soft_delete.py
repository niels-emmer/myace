"""add_deleted_at_for_soft_delete

Revision ID: b2d3e4f5a6b7
Revises: a1c2d3e4f5a6
Create Date: 2026-08-09 11:15:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b2d3e4f5a6b7'
down_revision: str | None = 'a1c2d3e4f5a6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('artifacts', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('profiles', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('doc_cache', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('doc_cache', 'deleted_at')
    op.drop_column('profiles', 'deleted_at')
    op.drop_column('artifacts', 'deleted_at')
