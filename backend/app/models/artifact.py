"""Artifact model — a single canonical IR document with YAML frontmatter."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Column, String, DateTime, Integer, Boolean
from sqlalchemy import Uuid,  ForeignKey, Text


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
    description: Optional[str] = Field(default=None, sa_column=Column("description", Text))
    body: str = Field(sa_column=Column("body", Text, nullable=False))
    file_path: str = Field(sa_column=Column("file_path", Text, nullable=False))
    is_enabled: bool = Field(default=True, sa_column=Column("is_enabled", Boolean, default=True))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column("created_at", DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column("updated_at", DateTime(timezone=True), nullable=False, onupdate=lambda: datetime.now(timezone.utc)),
        
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
    description: Optional[str] = None
    body: str
    file_path: str


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
    description: Optional[str] = None
    body: str
    file_path: str
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


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
    source_collection_id: Optional[uuid.UUID] = None
    source_collection_name: Optional[str] = None
