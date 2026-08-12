"""add_oauth_provider_credentials

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-12 10:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'a7b8c9d0e1f2'
down_revision: str | None = 'f6a7b8c9d0e1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'system_settings', sa.Column('oidc_client_id', sa.String(length=255), nullable=True)
    )
    op.add_column(
        'system_settings',
        sa.Column('oidc_client_secret_encrypted', sa.Text(), nullable=True),
    )
    op.add_column(
        'system_settings', sa.Column('oidc_issuer_url', sa.String(length=500), nullable=True)
    )
    op.add_column(
        'system_settings', sa.Column('oidc_scopes', sa.String(length=255), nullable=True)
    )
    op.add_column(
        'system_settings', sa.Column('github_client_id', sa.String(length=255), nullable=True)
    )
    op.add_column(
        'system_settings',
        sa.Column('github_client_secret_encrypted', sa.Text(), nullable=True),
    )
    op.add_column(
        'system_settings', sa.Column('google_client_id', sa.String(length=255), nullable=True)
    )
    op.add_column(
        'system_settings',
        sa.Column('google_client_secret_encrypted', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('system_settings', 'google_client_secret_encrypted')
    op.drop_column('system_settings', 'google_client_id')
    op.drop_column('system_settings', 'github_client_secret_encrypted')
    op.drop_column('system_settings', 'github_client_id')
    op.drop_column('system_settings', 'oidc_scopes')
    op.drop_column('system_settings', 'oidc_issuer_url')
    op.drop_column('system_settings', 'oidc_client_secret_encrypted')
    op.drop_column('system_settings', 'oidc_client_id')
