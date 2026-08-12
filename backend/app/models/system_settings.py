"""System settings model — single-row table for runtime-configurable settings."""

import json
from datetime import UTC, datetime

from sqlalchemy import Text
from sqlmodel import Column, DateTime, Field, Integer, SQLModel


class SystemSettings(SQLModel, table=True):
    """Runtime system-wide settings. Single-row table (id=1 always).

    Env vars serve as initial defaults and for sensitive credentials (OIDC
    client secrets). DB settings override env vars at runtime for toggles
    and non-sensitive configuration.
    """

    __tablename__ = "system_settings"

    id: int = Field(default=1, sa_column=Column(Integer, primary_key=True))

    # ─── Auth Provider Toggles ──────────────────────────────────
    oidc_enabled: bool = Field(default=True)
    github_enabled: bool = Field(default=True)
    google_enabled: bool = Field(default=True)

    # ─── Registration ──────────────────────────────────────────
    allow_registration: bool = Field(default=True)

    # ─── MFA Settings ──────────────────────────────────────────
    mfa_enabled: bool = Field(default=False)
    mfa_forced: bool = Field(default=False)

    # ─── Doc Cache ─────────────────────────────────────────────
    doc_cache_ttl_days: int = Field(default=7)

    # ─── Adapter Registry ────────────────────────────────────────
    # JSON-encoded list[str] of adapter names (BaseAdapter.adapter_name())
    # currently disabled system-wide — same manual-JSON-in-Text-column
    # convention as Profile.disabled_artifact_ids. Enforced both in the
    # frontend target picker and in compile_profile() (see AGENTS.md).
    disabled_adapters: str = Field(
        default="[]", sa_column=Column("disabled_adapters", Text, server_default="[]")
    )

    # ─── Metadata ──────────────────────────────────────────────
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            "updated_at", DateTime(timezone=True), nullable=False,
            onupdate=lambda: datetime.now(UTC),
        ),
    )


class SystemSettingsRead(SQLModel):
    """Schema for reading system settings (no secrets)."""
    oidc_enabled: bool
    github_enabled: bool
    google_enabled: bool
    allow_registration: bool
    mfa_enabled: bool
    mfa_forced: bool
    doc_cache_ttl_days: int
    disabled_adapters: list[str]
    updated_at: datetime

    @classmethod
    def from_settings(cls, settings: "SystemSettings") -> "SystemSettingsRead":
        return cls(
            **settings.model_dump(exclude={"disabled_adapters"}),
            disabled_adapters=json.loads(settings.disabled_adapters),
        )


class SystemSettingsUpdate(SQLModel):
    """Schema for updating system settings (all fields optional)."""
    oidc_enabled: bool | None = None
    github_enabled: bool | None = None
    google_enabled: bool | None = None
    allow_registration: bool | None = None
    mfa_enabled: bool | None = None
    mfa_forced: bool | None = None
    doc_cache_ttl_days: int | None = None
    disabled_adapters: list[str] | None = None
