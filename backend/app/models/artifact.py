"""Artifact model — a single canonical IR document with YAML frontmatter."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Text, Uuid
from sqlmodel import Boolean, Column, DateTime, Field, Integer, SQLModel, String


class Artifact(SQLModel, table=True):
    """A single canonical artifact (rule, skill, agent, workflow, or model_config)."""

    __tablename__ = "artifacts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    collection_id: uuid.UUID = Field(
        sa_column=Column("collection_id", Uuid, ForeignKey("collections.id"), nullable=False),
    )
    artifact_type: str = Field(
        sa_column=Column("artifact_type", String(64), nullable=False),
    )
    name: str = Field(sa_column=Column("name", String(255), nullable=False))
    version: str = Field(default="1.0.0", sa_column=Column("version", String(32), default="1.0.0"))
    priority: int = Field(default=50, sa_column=Column("priority", Integer, default=50))
    target_compatibility: str = Field(
        default="[]",
        sa_column=Column("target_compatibility", Text, default="[]"),
    )
    tags: str = Field(
        default="[]",
        sa_column=Column("tags", Text, default="[]"),
    )
    description: str | None = Field(default=None, sa_column=Column("description", Text))
    body: str = Field(sa_column=Column("body", Text, nullable=False))
    file_path: str = Field(sa_column=Column("file_path", Text, nullable=False))
    handoff_to: str | None = Field(
        default=None,
        sa_column=Column("handoff_to", Text, nullable=True),
    )
    is_enabled: bool = Field(default=True, sa_column=Column("is_enabled", Boolean, default=True))
    deleted_at: datetime | None = Field(
        default=None, sa_column=Column("deleted_at", DateTime(timezone=True)),
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


class ArtifactCreate(SQLModel):
    """Schema for creating an artifact."""
    collection_id: uuid.UUID
    artifact_type: str
    name: str
    version: str = "1.0.0"
    priority: int = 50
    target_compatibility: list[str] = []
    tags: list[str] = []
    description: str | None = None
    body: str
    file_path: str
    handoff_to: list[str] | None = None


class ArtifactRead(SQLModel):
    """Schema for reading an artifact."""
    id: uuid.UUID
    collection_id: uuid.UUID
    artifact_type: str
    name: str
    version: str
    priority: int
    target_compatibility: list[str]
    tags: list[str]
    description: str | None = None
    body: str
    file_path: str
    handoff_to: list[str] | None = None
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class ArtifactUpdate(SQLModel):
    """Schema for updating an artifact (all fields optional)."""
    name: str | None = None
    artifact_type: str | None = None
    version: str | None = None
    priority: int | None = None
    target_compatibility: list[str] | None = None
    tags: list[str] | None = None
    description: str | None = None
    body: str | None = None
    file_path: str | None = None
    handoff_to: list[str] | None = None
    is_enabled: bool | None = None


class CanonicalArtifact(SQLModel):
    """
    Canonical Intermediate Representation — the single source of truth.
    This is the format used for composition and translation.
    """
    artifact_type: str  # rule | skill | agent | workflow | model_config
    name: str
    version: str
    target_compatibility: list[str]
    priority: int
    tags: list[str]
    description: str
    body: str  # Markdown content
    handoff_to: list[str] | None = None
    source_collection_id: uuid.UUID | None = None
    source_collection_name: str | None = None
