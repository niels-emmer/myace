"""add_sync_statuses

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-08-16 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'c5d6e7f8a9b0'
down_revision: str | None = 'b4c5d6e7f8a9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'sync_statuses',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('profile_id', sa.Uuid(), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('target', sa.String(64), nullable=False),
        sa.Column('machine_label', sa.String(255), nullable=False),
        sa.Column('in_sync', sa.Boolean(), nullable=False),
        sa.Column('locally_modified_files', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            'user_id', 'profile_id', 'target', 'machine_label',
            name='uq_sync_statuses_user_profile_target_machine',
        ),
    )


def downgrade() -> None:
    op.drop_table('sync_statuses')
