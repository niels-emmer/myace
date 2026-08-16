"""add_notification_preferences_and_digest

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-08-16 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'a3b4c5d6e7f8'
down_revision: str | None = 'f2a3b4c5d6e7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'notify_on_download', sa.Boolean(), nullable=False, server_default=sa.text('false')
        ),
    )
    op.add_column(
        'users',
        sa.Column(
            'notify_on_comment', sa.Boolean(), nullable=False, server_default=sa.text('false')
        ),
    )
    op.add_column(
        'collections',
        sa.Column('last_digest_download_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'collections',
        sa.Column('last_digest_sent_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('collections', 'last_digest_sent_at')
    op.drop_column('collections', 'last_digest_download_count')
    op.drop_column('users', 'notify_on_comment')
    op.drop_column('users', 'notify_on_download')
