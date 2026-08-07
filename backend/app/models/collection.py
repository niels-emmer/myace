"""Collection model — a Git repository of canonical artifacts."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Column, String, DateTime, Boolean, Integer
from sqlalchemy import Uuid,  ForeignKey, Text


class Collection(SQLModel, table=True):
    """A collection of canonical artifacts sourced from a Git repository."""

    __tablename__ = "collections"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        sa_column=Column("owner_id", Uuid, ForeignKey("users.id"), nullable=False),
    )
    name: str = Field(sa_column=Column("name", String(255), nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column("description", Text))
    git_url: str = Field(sa_column=Column("git_url", Text, nullable=False))
    git_branch: str = Field(default="main", sa_column=Column("git_branch", String(255), default="main"))
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
    last_synced_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column("last_synced_at", DateTime(timezone=True)),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column("created_at", DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column("updated_at", DateTime(timezone=True), nullable=False, onupdate=lambda: datetime.now(timezone.utc)),
        
    )


class CollectionCreate(SQLModel):
    """Schema for creating a collection."""
    name: str
    description: Optional[str] = None
    git_url: str
    git_branch: str = "main"
    collection_type: str = "base"
    visibility: str = "private"


class CollectionRead(SQLModel):
    """Schema for reading a collection."""
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: Optional[str] = None
    git_url: str
    git_branch: str
    collection_type: str
    visibility: str
    is_active: bool
    artifact_count: int
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
