"""add_system_settings_table

Revision ID: c3d4e5f6a7b8
Revises: b2d3e4f5a6b7
Create Date: 2026-08-10 10:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'c3d4e5f6a7b8'
down_revision: str | None = 'b2d3e4f5a6b7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('oidc_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('github_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('google_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('allow_registration', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('mfa_forced', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('doc_cache_ttl_days', sa.Integer(), nullable=False, server_default=sa.text('7')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    # Insert the default single row
    op.execute(
        "INSERT INTO system_settings (id, oidc_enabled, github_enabled, google_enabled, "
        "allow_registration, mfa_enabled, mfa_forced, doc_cache_ttl_days, updated_at) "
        "VALUES (1, true, true, true, true, false, false, 7, NOW())"
    )


def downgrade() -> None:
    op.drop_table('system_settings')
