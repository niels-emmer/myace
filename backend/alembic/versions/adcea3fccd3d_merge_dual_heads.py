"""merge_dual_heads

Revision ID: adcea3fccd3d
Revises: c4d5e6f7a8b9, d4e5f6a7b8c9
Create Date: 2026-08-10 18:06:40.520436
"""
from collections.abc import Sequence

revision: str = 'adcea3fccd3d'
down_revision: str | tuple[str, ...] | None = ('c4d5e6f7a8b9', 'd4e5f6a7b8c9')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op merge: reconciles the two divergent heads left by
    add_download_count_published_category and add_mfa_fields_to_users,
    which both branched from add_deleted_at_for_soft_delete."""
    pass


def downgrade() -> None:
    pass
