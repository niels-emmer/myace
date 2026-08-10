"""add_download_count_published_category

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
    op.add_column(
        'collections',
        sa.Column('download_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
    )
    op.add_column(
        'collections',
        sa.Column('published', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.add_column('collections', sa.Column('category', sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column('collections', 'category')
    op.drop_column('collections', 'published')
    op.drop_column('collections', 'download_count')
