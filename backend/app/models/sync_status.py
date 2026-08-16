"""SyncStatus model — opt-in, self-reported local drift state from `myace check --report`.

See docs/adr/0009-manifest-based-drift-detection.md. This table is purely a
reporting sink: the CLI computes drift locally (against its own manifest and
the compile-status endpoint) and only ever POSTs a summary here when the user
explicitly passes --report. Nothing is derived or recomputed server-side.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Text, UniqueConstraint, Uuid
from sqlmodel import Boolean, Column, DateTime, Field, SQLModel, String


class SyncStatus(SQLModel, table=True):
    """A single (user, profile, target, machine) drift-check report."""

    __tablename__ = "sync_statuses"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "profile_id", "target", "machine_label",
            name="uq_sync_statuses_user_profile_target_machine",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column("user_id", Uuid, ForeignKey("users.id"), nullable=False),
    )
    profile_id: uuid.UUID = Field(
        sa_column=Column("profile_id", Uuid, ForeignKey("profiles.id"), nullable=False),
    )
    target: str = Field(sa_column=Column("target", String(64), nullable=False))
    machine_label: str = Field(sa_column=Column("machine_label", String(255), nullable=False))
    in_sync: bool = Field(sa_column=Column("in_sync", Boolean, nullable=False))
    locally_modified_files: str = Field(
        default="[]",
        sa_column=Column("locally_modified_files", Text, default="[]"),
    )
    last_checked_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column("last_checked_at", DateTime(timezone=True), nullable=False),
    )


class SyncReportRequest(SQLModel):
    """Request body for `POST /sync/report` — the shape `myace check --report`
    (and `myace watch --report`) sends. `user_id` is deliberately absent:
    ownership always comes from `current_user.id` (AGENTS.md rule 13), never
    a client-supplied field."""
    profile_id: uuid.UUID
    target: str
    machine_label: str
    in_sync: bool
    locally_modified_files: list[str] = []


class SyncStatusRead(SQLModel):
    """Schema for reading a sync status row. `locally_modified_files` is
    stored as JSON text (same pattern as `Artifact.tags` — AGENTS.md rule
    11) and must be `json.loads()`'d before this schema is populated; never
    return the raw `SyncStatus` row from a route."""
    id: uuid.UUID
    profile_id: uuid.UUID
    profile_name: str
    target: str
    machine_label: str
    in_sync: bool
    locally_modified_files: list[str]
    last_checked_at: datetime
