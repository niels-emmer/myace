"""CollectionComment model — a comment on a published collection."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Text, Uuid
from sqlmodel import Column, DateTime, Field, SQLModel


class CollectionComment(SQLModel, table=True):
    """A comment on a collection. Soft-deleted (`deleted_at`), never hard
    deleted, per this repo's soft-delete rule."""

    __tablename__ = "collection_comments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    collection_id: uuid.UUID = Field(
        sa_column=Column("collection_id", Uuid, ForeignKey("collections.id"), nullable=False),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column("user_id", Uuid, ForeignKey("users.id"), nullable=False),
    )
    body: str = Field(sa_column=Column("body", Text, nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column("created_at", DateTime(timezone=True), nullable=False),
    )
    deleted_at: datetime | None = Field(
        default=None, sa_column=Column("deleted_at", DateTime(timezone=True), nullable=True)
    )


class CollectionCommentCreate(SQLModel):
    """Schema for creating a comment. Capped at 2000 chars, enforced here
    at the schema layer (not just informally)."""
    body: str = Field(min_length=1, max_length=2000)


class CollectionCommentRead(SQLModel):
    """Schema for reading a comment."""
    id: uuid.UUID
    collection_id: uuid.UUID
    user_id: uuid.UUID
    author_display_name: str
    body: str
    created_at: datetime
