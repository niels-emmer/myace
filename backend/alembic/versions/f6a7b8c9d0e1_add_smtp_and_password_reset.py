"""add_smtp_and_password_reset

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-12 09:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'f6a7b8c9d0e1'
down_revision: str | None = 'e5f6a7b8c9d0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('reset_token_hash', sa.String(length=64), nullable=True))
    op.add_column(
        'users', sa.Column('reset_token_expires_at', sa.DateTime(timezone=True), nullable=True)
    )

    op.add_column(
        'system_settings',
        sa.Column('smtp_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.add_column('system_settings', sa.Column('smtp_host', sa.String(length=255), nullable=True))
    op.add_column('system_settings', sa.Column('smtp_port', sa.Integer(), nullable=True))
    op.add_column(
        'system_settings', sa.Column('smtp_username', sa.String(length=255), nullable=True)
    )
    op.add_column(
        'system_settings', sa.Column('smtp_password_encrypted', sa.Text(), nullable=True)
    )
    op.add_column(
        'system_settings', sa.Column('smtp_from_email', sa.String(length=255), nullable=True)
    )
    op.add_column(
        'system_settings', sa.Column('smtp_from_name', sa.String(length=255), nullable=True)
    )
    op.add_column('system_settings', sa.Column('smtp_use_tls', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('system_settings', 'smtp_use_tls')
    op.drop_column('system_settings', 'smtp_from_name')
    op.drop_column('system_settings', 'smtp_from_email')
    op.drop_column('system_settings', 'smtp_password_encrypted')
    op.drop_column('system_settings', 'smtp_username')
    op.drop_column('system_settings', 'smtp_port')
    op.drop_column('system_settings', 'smtp_host')
    op.drop_column('system_settings', 'smtp_enabled')

    op.drop_column('users', 'reset_token_expires_at')
    op.drop_column('users', 'reset_token_hash')
