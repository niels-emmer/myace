"""add_is_starter_pack_to_collection

Revision ID: 916f98461729
Revises: adcea3fccd3d
Create Date: 2026-08-10 18:07:00.000748
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '916f98461729'
down_revision: str | None = 'adcea3fccd3d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'collections',
        sa.Column(
            'is_starter_pack', sa.Boolean(), nullable=False, server_default=sa.text('false')
        ),
    )


def downgrade() -> None:
    op.drop_column('collections', 'is_starter_pack')
