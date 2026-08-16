"""Collection model — a Git repository of canonical artifacts."""

import uuid
from datetime import UTC, date, datetime
from typing import Literal

from sqlalchemy import Date, ForeignKey, Text, Uuid
from sqlmodel import Boolean, Column, DateTime, Field, Float, Integer, SQLModel, String


class Collection(SQLModel, table=True):
    """A collection of canonical artifacts sourced from a Git repository."""

    __tablename__ = "collections"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        sa_column=Column("owner_id", Uuid, ForeignKey("users.id"), nullable=False),
    )
    name: str = Field(sa_column=Column("name", String(255), nullable=False))
    description: str | None = Field(default=None, sa_column=Column("description", Text))
    git_url: str = Field(sa_column=Column("git_url", Text, nullable=False))
    git_branch: str = Field(
        default="main", sa_column=Column("git_branch", String(255), default="main")
    )
    collection_type: str = Field(
        default="base",
        sa_column=Column("collection_type", String(64), nullable=False),
    )
    visibility: str = Field(
        default="private",
        sa_column=Column("visibility", String(32), default="private"),
    )
    is_active: bool = Field(default=True, sa_column=Column("is_active", Boolean, default=True))
    artifact_count: int = Field(default=0, sa_column=Column("artifact_count", Integer, default=0))
    download_count: int = Field(default=0, sa_column=Column("download_count", Integer, default=0))
    published: bool = Field(default=False, sa_column=Column("published", Boolean, default=False))
    category: str | None = Field(default=None, sa_column=Column("category", String(128)))
    is_starter_pack: bool = Field(
        default=False, sa_column=Column("is_starter_pack", Boolean, nullable=False, default=False)
    )
    avg_rating: float = Field(default=0.0, sa_column=Column("avg_rating", Float, default=0.0))
    rating_count: int = Field(default=0, sa_column=Column("rating_count", Integer, default=0))
    moderation_status: str = Field(
        default="draft",
        sa_column=Column("moderation_status", String(32), nullable=False, default="draft"),
    )
    moderation_reason: str | None = Field(
        default=None, sa_column=Column("moderation_reason", Text)
    )
    submitted_at: datetime | None = Field(
        default=None, sa_column=Column("submitted_at", DateTime(timezone=True))
    )
    moderated_at: datetime | None = Field(
        default=None, sa_column=Column("moderated_at", DateTime(timezone=True))
    )
    moderated_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column("moderated_by", Uuid, ForeignKey("users.id"), nullable=True),
    )
    last_synced_at: datetime | None = Field(
        default=None,
        sa_column=Column("last_synced_at", DateTime(timezone=True)),
    )
    last_verified_at: date | None = Field(
        default=None,
        sa_column=Column("last_verified_at", Date),
    )
    verified_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column("verified_by", Uuid, ForeignKey("users.id"), nullable=True),
    )
    last_digest_download_count: int = Field(
        default=0,
        sa_column=Column("last_digest_download_count", Integer, nullable=False, default=0),
    )
    last_digest_sent_at: datetime | None = Field(
        default=None,
        sa_column=Column("last_digest_sent_at", DateTime(timezone=True)),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column("created_at", DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            "updated_at", DateTime(timezone=True), nullable=False,
            onupdate=lambda: datetime.now(UTC),
        ),
    )


class CollectionCreate(SQLModel):
    """Schema for creating a collection."""
    name: str
    description: str | None = None
    git_url: str
    git_branch: str = "main"
    collection_type: Literal["base", "additional"] = "base"
    visibility: Literal["private", "public"] = "private"
    category: str | None = None


class CollectionUpdate(SQLModel):
    """Schema for updating a collection (all fields optional)."""
    name: str | None = None
    description: str | None = None
    collection_type: Literal["base", "additional"] | None = None
    visibility: Literal["private", "public"] | None = None
    category: str | None = None


class CollectionRead(SQLModel):
    """Schema for reading a collection."""
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str | None = None
    git_url: str
    git_branch: str
    collection_type: str
    visibility: str
    is_active: bool
    artifact_count: int
    download_count: int = 0
    published: bool = False
    category: str | None = None
    is_starter_pack: bool = False
    avg_rating: float = 0.0
    rating_count: int = 0
    moderation_status: Literal["draft", "submitted", "approved", "denied"] = "draft"
    moderation_reason: str | None = None
    submitted_at: datetime | None = None
    moderated_at: datetime | None = None
    moderated_by: uuid.UUID | None = None
    last_synced_at: datetime | None = None
    last_verified_at: date | None = None
    verified_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
