"""Documentation cache model for framework compatibility rules."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Text
from sqlmodel import Column, DateTime, Field, Integer, SQLModel, String


class DocCacheEntry(SQLModel, table=True):
    """Cached framework documentation for adapter compatibility rules."""

    __tablename__ = "doc_cache"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    framework: str = Field(
        sa_column=Column("framework", String(64), nullable=False, index=True),
    )
    url: str = Field(sa_column=Column("url", Text, nullable=False))
    content_hash: str = Field(sa_column=Column("content_hash", String(64), nullable=False))
    content: str = Field(sa_column=Column("content", Text, nullable=False))
    content_type: str = Field(
        default="schema",
        sa_column=Column("content_type", String(64), default="schema"),
    )
    ttl_days: int = Field(default=7, sa_column=Column("ttl_days", Integer, default=7))
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column("fetched_at", DateTime(timezone=True), nullable=False),
    )
    expires_at: datetime = Field(
        sa_column=Column("expires_at", DateTime(timezone=True), nullable=False),
    )


class DocCacheCreate(SQLModel):
    """Schema for creating a doc cache entry."""
    framework: str
    url: str
    content_hash: str
    content: str
    content_type: str = "schema"
    ttl_days: int = 7
