"""add_ratings_and_comments

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-08-16 11:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'f2a3b4c5d6e7'
down_revision: str | None = 'e1f2a3b4c5d6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'collections', sa.Column('avg_rating', sa.Float(), nullable=False, server_default='0')
    )
    op.add_column(
        'collections', sa.Column('rating_count', sa.Integer(), nullable=False, server_default='0')
    )

    op.create_table(
        'collection_ratings',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('collection_id', sa.Uuid(), sa.ForeignKey('collections.id'), nullable=False),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('stars', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            'collection_id', 'user_id', name='uq_collection_ratings_collection_user'
        ),
        sa.CheckConstraint('stars >= 1 AND stars <= 5', name='ck_collection_ratings_stars_range'),
    )

    op.create_table(
        'collection_comments',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('collection_id', sa.Uuid(), sa.ForeignKey('collections.id'), nullable=False),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('collection_comments')
    op.drop_table('collection_ratings')
    op.drop_column('collections', 'rating_count')
    op.drop_column('collections', 'avg_rating')
