"""Profile model — a composed set of collections with artifact toggles."""

import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import ForeignKey, Text, Uuid
from sqlmodel import Boolean, Column, DateTime, Field, Integer, SQLModel, String


class Profile(SQLModel, table=True):
    """A user-defined profile combining a base collection with additional collections."""

    __tablename__ = "profiles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        sa_column=Column("owner_id", Uuid, ForeignKey("users.id"), nullable=False),
    )
    name: str = Field(sa_column=Column("name", String(255), nullable=False))
    description: str | None = Field(default=None, sa_column=Column("description", Text))
    base_collection_id: uuid.UUID = Field(
        sa_column=Column("base_collection_id", Uuid, ForeignKey("collections.id"), nullable=False),
    )
    additional_collection_ids: str = Field(
        default="[]",
        sa_column=Column("additional_collection_ids", Text, default="[]"),
    )
    disabled_artifact_ids: str = Field(
        default="[]",
        sa_column=Column("disabled_artifact_ids", Text, default="[]"),
    )
    target_framework: str | None = Field(
        default=None,
        sa_column=Column("target_framework", String(64)),
    )
    is_public: bool = Field(default=False, sa_column=Column("is_public", Boolean, default=False))
    deleted_at: datetime | None = Field(
        default=None, sa_column=Column("deleted_at", DateTime(timezone=True)),
    )
    version: int = Field(default=1, sa_column=Column("version", Integer, default=1))
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


class ProfileCreate(SQLModel):
    """Schema for creating a profile."""
    name: str
    description: str | None = None
    base_collection_id: uuid.UUID
    additional_collection_ids: list[uuid.UUID] = []
    disabled_artifact_ids: list[uuid.UUID] = []
    target_framework: str | None = None
    is_public: bool = False


class ProfileRead(SQLModel):
    """Schema for reading a profile."""
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str | None = None
    base_collection_id: uuid.UUID
    additional_collection_ids: list[uuid.UUID]
    disabled_artifact_ids: list[uuid.UUID]
    target_framework: str | None = None
    is_public: bool
    version: int
    created_at: datetime
    updated_at: datetime


CompileTarget = Literal[
    "claude-code", "opencode", "cursor", "codex-cli", "copilot-cli", "cline", "windsurf",
    "aider", "continue", "goose", "amazon-q",
]


class ProfileCompileRequest(SQLModel):
    """Request schema for compiling a profile into target-specific files."""
    profile_id: uuid.UUID
    target: CompileTarget = "opencode"
    include_disabled: bool = False


class ValidationIssue(SQLModel):
    """A non-fatal problem surfaced during compilation (e.g. an artifact name
    collision across composed collections). Additive to the compile response —
    never blocks compilation, just flags something worth a human look.

    `level` is a `Literal["warning"]` today because compile-time validation only
    ever emits warnings; a future error-level check would be a deliberate,
    reviewed addition to this Literal, not an implicit widening.
    """
    level: Literal["warning"] = "warning"
    code: str
    message: str


class ProfileCompileResponse(SQLModel):
    """Return type of `compile_profile()` and `response_model` for
    `POST /profiles/compile`. An unregistered `target` (unreachable via the
    API today — `ProfileCompileRequest.target` is a `Literal` covering every
    registered adapter, so FastAPI 422s first) raises
    `compiler.UnknownAdapterError` instead of returning a differently-shaped
    dict, which is what keeps this a single concrete return type end to end.
    """
    profile_id: str
    profile_name: str
    target: str
    artifact_count: int
    files: dict[str, str]
    warnings: list[ValidationIssue] = []
    compiled_hash: str


class ProfileCompileStatusResponse(SQLModel):
    """Return type of `GET /profiles/{id}/compile-status` — a cheap-to-transfer
    hash + timestamp pair a client can diff against a previously stored
    value (e.g. a CLI sync manifest, see `docs/adr/0009-manifest-based-drift-detection.md`)
    to detect server-side staleness without pulling every file's content.
    """
    compiled_hash: str
    updated_at: datetime
