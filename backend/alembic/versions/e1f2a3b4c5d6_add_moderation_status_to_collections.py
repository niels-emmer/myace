"""add_moderation_status_to_collections

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-08-16 10:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'e1f2a3b4c5d6'
down_revision: str | None = 'd0e1f2a3b4c5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'collections',
        sa.Column(
            'moderation_status', sa.String(length=32), nullable=False, server_default='draft'
        ),
    )
    op.add_column('collections', sa.Column('moderation_reason', sa.Text(), nullable=True))
    op.add_column(
        'collections', sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'collections', sa.Column('moderated_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'collections',
        sa.Column('moderated_by', sa.Uuid(), sa.ForeignKey('users.id'), nullable=True),
    )

    # Grandfather every collection currently visible in the community listing
    # (GET /collections/community's own filter is `published AND is_active` —
    # it does not additionally check visibility, so the backfill mirrors that
    # exactly rather than assuming visibility='public' is part of it).
    op.execute(
        "UPDATE collections SET moderation_status = 'approved' "
        "WHERE published = true AND is_active = true"
    )


def downgrade() -> None:
    op.drop_column('collections', 'moderated_by')
    op.drop_column('collections', 'moderated_at')
    op.drop_column('collections', 'submitted_at')
    op.drop_column('collections', 'moderation_reason')
    op.drop_column('collections', 'moderation_status')
