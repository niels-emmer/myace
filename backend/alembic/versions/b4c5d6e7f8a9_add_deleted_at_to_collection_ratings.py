"""add_deleted_at_to_collection_ratings

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-08-16 13:00:00.000000

Fixes a rule-15 violation introduced by the ratings/comments migration
(f2a3b4c5d6e7): DELETE /collections/{id}/rating was hard-deleting the
CollectionRating row instead of soft-deleting it. Caught during the
documentation pass, fixed with a new migration rather than editing the
already-committed one (AGENTS.md rule 2 / invariants.md rule 16).
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b4c5d6e7f8a9'
down_revision: str | None = 'a3b4c5d6e7f8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'collection_ratings', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('collection_ratings', 'deleted_at')
