"""System settings model — single-row table for runtime-configurable settings."""

from datetime import UTC, datetime

from sqlalchemy import Text
from sqlmodel import Column, DateTime, Field, Integer, SQLModel, String


class SystemSettings(SQLModel, table=True):
    """Runtime system-wide settings. Single-row table (id=1 always).

    Env vars serve as initial defaults. DB settings override env vars at
    runtime for toggles, non-sensitive configuration, and — since
    ADR-0006 — admin-editable secrets (SMTP password, OAuth client
    secrets), which are encrypted before being stored here.
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

    # ─── SMTP (password-reset email) ────────────────────────────
    # Empty/None fields fall back to the env var default of the same name
    # (see app/services/effective_settings.py). smtp_password is never
    # stored in plaintext — only its Fernet-encrypted form.
    smtp_enabled: bool = Field(default=False)
    smtp_host: str | None = Field(default=None, sa_column=Column("smtp_host", String(255)))
    smtp_port: int | None = Field(default=None)
    smtp_username: str | None = Field(
        default=None, sa_column=Column("smtp_username", String(255))
    )
    smtp_password_encrypted: str | None = Field(
        default=None, sa_column=Column("smtp_password_encrypted", Text)
    )
    smtp_from_email: str | None = Field(
        default=None, sa_column=Column("smtp_from_email", String(255))
    )
    smtp_from_name: str | None = Field(
        default=None, sa_column=Column("smtp_from_name", String(255))
    )
    smtp_use_tls: bool | None = Field(default=None)

    # ─── OAuth Provider Credentials (admin-editable, encrypted) ──
    # Empty/None fields fall back to the matching env var (see
    # app/services/effective_settings.py). The *_client_secret_encrypted
    # columns are never returned by the API — only a computed
    # `{provider}_client_secret_set` boolean (see SystemSettingsRead).
    oidc_client_id: str | None = Field(
        default=None, sa_column=Column("oidc_client_id", String(255))
    )
    oidc_client_secret_encrypted: str | None = Field(
        default=None, sa_column=Column("oidc_client_secret_encrypted", Text)
    )
    oidc_issuer_url: str | None = Field(
        default=None, sa_column=Column("oidc_issuer_url", String(500))
    )
    oidc_scopes: str | None = Field(default=None, sa_column=Column("oidc_scopes", String(255)))
    github_client_id: str | None = Field(
        default=None, sa_column=Column("github_client_id", String(255))
    )
    github_client_secret_encrypted: str | None = Field(
        default=None, sa_column=Column("github_client_secret_encrypted", Text)
    )
    google_client_id: str | None = Field(
        default=None, sa_column=Column("google_client_id", String(255))
    )
    google_client_secret_encrypted: str | None = Field(
        default=None, sa_column=Column("google_client_secret_encrypted", Text)
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
    smtp_enabled: bool
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password_set: bool = False
    smtp_from_email: str | None = None
    smtp_from_name: str | None = None
    smtp_use_tls: bool | None = None
    oidc_client_id: str | None = None
    oidc_client_secret_set: bool = False
    oidc_issuer_url: str | None = None
    oidc_scopes: str | None = None
    github_client_id: str | None = None
    github_client_secret_set: bool = False
    google_client_id: str | None = None
    google_client_secret_set: bool = False
    updated_at: datetime

    @classmethod
    def from_settings(cls, settings: "SystemSettings") -> "SystemSettingsRead":
        encrypted_fields = {
            "smtp_password_encrypted", "oidc_client_secret_encrypted",
            "github_client_secret_encrypted", "google_client_secret_encrypted",
        }
        return cls(
            **settings.model_dump(exclude=encrypted_fields),
            smtp_password_set=bool(settings.smtp_password_encrypted),
            oidc_client_secret_set=bool(settings.oidc_client_secret_encrypted),
            github_client_secret_set=bool(settings.github_client_secret_encrypted),
            google_client_secret_set=bool(settings.google_client_secret_encrypted),
        )


class SystemSettingsUpdate(SQLModel):
    """Schema for updating system settings (all fields optional).

    `smtp_password` is a plaintext write-only field — the route handler
    encrypts it into `smtp_password_encrypted` before persisting. Sending
    an empty string clears the stored secret; omitting the field leaves
    it unchanged.
    """
    oidc_enabled: bool | None = None
    github_enabled: bool | None = None
    google_enabled: bool | None = None
    allow_registration: bool | None = None
    mfa_enabled: bool | None = None
    mfa_forced: bool | None = None
    doc_cache_ttl_days: int | None = None
    smtp_enabled: bool | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str | None = None
    smtp_use_tls: bool | None = None
    oidc_client_id: str | None = None
    oidc_client_secret: str | None = None
    oidc_issuer_url: str | None = None
    oidc_scopes: str | None = None
    github_client_id: str | None = None
    github_client_secret: str | None = None
    google_client_id: str | None = None
    google_client_secret: str | None = None
