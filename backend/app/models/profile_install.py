"""ProfileInstall model — a user's *claim* that a setup was installed.

This is a claim, never verification. `SyncStatus` (fed by
`myace check --report`) remains the only verified source of "the files on
disk actually match the compiled output" — a row here only records that the
user reported installing a profile to a target at a location. See
docs/adr/0015-pack-reference-freeze.md and docs/invariants.md.
"""

import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import ForeignKey, UniqueConstraint, Uuid
from sqlmodel import Column, DateTime, Field, SQLModel, String

from app.models.profile import CompileTarget

InstallLocation = Literal["project", "machine"]


class ProfileInstall(SQLModel, table=True):
    """One claimed install of a profile for a (user, target, location)."""

    __tablename__ = "profile_installs"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "profile_id", "target", "location",
            name="uq_profile_installs_user_profile_target_location",
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
    location: str = Field(sa_column=Column("location", String(16), nullable=False))
    method: str = Field(
        default="cli", sa_column=Column("method", String(32), nullable=False, default="cli")
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


class ProfileInstallCreate(SQLModel):
    """Body for `POST /profiles/{id}/installs`.

    `target` reuses `CompileTarget` so an unknown adapter is a 422 at the
    schema layer, matching every other target-accepting route. `location`
    is likewise a closed `Literal`. `method` is a free-form string (e.g.
    "cli", "zip") — it describes how the user installed, not a verified
    fact.
    """
    target: CompileTarget
    location: InstallLocation
    method: str = Field(default="cli", min_length=1, max_length=32)


class ProfileInstallRead(SQLModel):
    """Schema for reading an install claim."""
    id: uuid.UUID
    profile_id: uuid.UUID
    target: str
    location: Literal["project", "machine"]
    method: str
    created_at: datetime
    updated_at: datetime
