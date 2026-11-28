"""add_permissions_to_artifacts

Revision ID: b7c8d9e0f1a2
Revises: e3f4a5b6c7d8
Create Date: 2026-11-28 10:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b7c8d9e0f1a2'
down_revision: str | None = 'e3f4a5b6c7d8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('artifacts', sa.Column('permissions', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('artifacts', 'permissions')
