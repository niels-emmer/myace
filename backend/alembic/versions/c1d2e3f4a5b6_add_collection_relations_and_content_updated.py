"""add_collection_relations_and_content_updated

Revision ID: c1d2e3f4a5b6
Revises: b7c8d9e0f1a2
Create Date: 2026-11-28 18:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'c1d2e3f4a5b6'
down_revision: str | None = 'b7c8d9e0f1a2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # JSON-encoded {"layers_on": [slug], "pairs_with": [slug]}; NULL = none declared.
    op.add_column('collections', sa.Column('relations', sa.Text(), nullable=True))
    # When a seeded pack's items last changed (stamped by seeding and reconcile).
    op.add_column(
        'collections',
        sa.Column('content_updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('collections', 'content_updated_at')
    op.drop_column('collections', 'relations')
