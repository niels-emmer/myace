"""API Token model for CLI authentication."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Text, Uuid
from sqlmodel import Boolean, Column, DateTime, Field, SQLModel, String


class ApiToken(SQLModel, table=True):
    """Persisted API token for CLI authentication."""

    __tablename__ = "api_tokens"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        sa_column=Column("user_id", Uuid, ForeignKey("users.id"), nullable=False),
    )
    name: str = Field(sa_column=Column("name", String(255), nullable=False))
    token_prefix: str = Field(sa_column=Column("token_prefix", String(16), nullable=False))
    token_hash: str = Field(sa_column=Column("token_hash", Text, nullable=False))
    last_used_at: datetime | None = Field(
        default=None,
        sa_column=Column("last_used_at", DateTime(timezone=True)),
    )
    expires_at: datetime = Field(
        sa_column=Column("expires_at", DateTime(timezone=True), nullable=False),
    )
    is_active: bool = Field(default=True, sa_column=Column("is_active", Boolean, default=True))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column("created_at", DateTime(timezone=True), nullable=False),
    )


class ApiTokenCreate(SQLModel):
    """Schema for creating an API token."""
    name: str
    expires_at: datetime | None = None


class ApiTokenRead(SQLModel):
    """Schema for reading an API token (without the hash)."""
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    token_prefix: str
    last_used_at: datetime | None = None
    expires_at: datetime
    is_active: bool
    created_at: datetime


class ApiTokenCreateResponse(ApiTokenRead):
    """Schema for the create-token response — includes the raw key, shown only once."""
    token: str
