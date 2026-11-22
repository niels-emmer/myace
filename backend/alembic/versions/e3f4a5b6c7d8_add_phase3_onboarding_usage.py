"""add phase 3 onboarding/usage fields

Adds:
  * profiles.target_frameworks (JSON text, backfilled from target_framework)
  * profiles.pack_snapshots (JSON text)
  * collections.license
  * users.onboarding_completed_at
  * profile_installs table

See docs/adr/0015-pack-reference-freeze.md.

Revision ID: e3f4a5b6c7d8
Revises: a9b8c7d6e5f4
Create Date: 2026-11-22 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'e3f4a5b6c7d8'
down_revision: str | None = 'a9b8c7d6e5f4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'profiles',
        sa.Column('target_frameworks', sa.Text(), nullable=False, server_default='[]'),
    )
    op.add_column(
        'profiles',
        sa.Column('pack_snapshots', sa.Text(), nullable=False, server_default='{}'),
    )
    op.add_column(
        'collections',
        sa.Column('license', sa.String(64), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('onboarding_completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        'profile_installs',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('profile_id', sa.Uuid(), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('target', sa.String(64), nullable=False),
        sa.Column('location', sa.String(16), nullable=False),
        sa.Column('method', sa.String(32), nullable=False, server_default='cli'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            'user_id', 'profile_id', 'target', 'location',
            name='uq_profile_installs_user_profile_target_location',
        ),
    )

    # Backfill the new list column from the deprecated single-value column.
    # Adapter names are lowercase ASCII (no quotes/backslashes), so this
    # string concatenation is a safe JSON array literal on both SQLite and
    # PostgreSQL. Rows without a legacy value keep the '[]' server default.
    op.execute(
        "UPDATE profiles "
        "SET target_frameworks = '[\"' || target_framework || '\"]' "
        "WHERE target_framework IS NOT NULL AND target_framework <> ''"
    )


def downgrade() -> None:
    op.drop_table('profile_installs')
    op.drop_column('users', 'onboarding_completed_at')
    op.drop_column('collections', 'license')
    op.drop_column('profiles', 'pack_snapshots')
    op.drop_column('profiles', 'target_frameworks')
