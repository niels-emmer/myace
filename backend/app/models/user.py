"""User model and Pydantic schemas."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Text
from sqlmodel import Boolean, Column, DateTime, Field, SQLModel, String


class User(SQLModel, table=True):
    """Multi-tenant user account."""

    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(sa_column=Column("email", String(255), unique=True, nullable=False))
    display_name: str = Field(sa_column=Column("display_name", String(255), nullable=False))
    password_hash: str | None = Field(default=None, sa_column=Column("password_hash", String(255)))
    oidc_sub: str | None = Field(
        default=None, sa_column=Column("oidc_sub", String(255), unique=True)
    )
    oidc_provider: str | None = Field(default=None, sa_column=Column("oidc_provider", String(64)))
    avatar_url: str | None = Field(default=None, sa_column=Column("avatar_url", Text))
    is_active: bool = Field(default=True, sa_column=Column("is_active", Boolean, default=True))
    is_admin: bool = Field(default=False, sa_column=Column("is_admin", Boolean, default=False))
    mfa_enabled: bool = Field(default=False, sa_column=Column("mfa_enabled", Boolean, default=False))
    totp_secret: str | None = Field(default=None, sa_column=Column("totp_secret", String(64)))
    deleted_at: datetime | None = Field(
        default=None, sa_column=Column("deleted_at", DateTime(timezone=True), nullable=True)
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


class UserCreate(SQLModel):
    """Schema for creating a user."""
    email: str
    display_name: str
    oidc_sub: str | None = None
    oidc_provider: str | None = None
    avatar_url: str | None = None


class UserRead(SQLModel):
    """Schema for reading a user (public fields)."""
    id: uuid.UUID
    email: str
    display_name: str
    avatar_url: str | None = None
    is_active: bool
    is_admin: bool
    created_at: datetime


class UserRegister(SQLModel):
    """Schema for email+password registration."""
    email: str
    password: str
    display_name: str


class UserLogin(SQLModel):
    """Schema for email+password login."""
    email: str
    password: str


class UserUpdate(SQLModel):
    """Schema for updating user profile."""
    display_name: str | None = None
    email: str | None = None


class PasswordChange(SQLModel):
    """Schema for changing password."""
    current_password: str
    new_password: str
