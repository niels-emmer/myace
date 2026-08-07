"""User model and Pydantic schemas."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Column, String, DateTime, Boolean
from sqlalchemy import Uuid,  Text


class User(SQLModel, table=True):
    """Multi-tenant user account."""

    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(sa_column=Column("email", String(255), unique=True, nullable=False))
    display_name: str = Field(sa_column=Column("display_name", String(255), nullable=False))
    oidc_sub: Optional[str] = Field(default=None, sa_column=Column("oidc_sub", String(255), unique=True))
    oidc_provider: Optional[str] = Field(default=None, sa_column=Column("oidc_provider", String(64)))
    avatar_url: Optional[str] = Field(default=None, sa_column=Column("avatar_url", Text))
    is_active: bool = Field(default=True, sa_column=Column("is_active", Boolean, default=True))
    is_admin: bool = Field(default=False, sa_column=Column("is_admin", Boolean, default=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column("created_at", DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column("updated_at", DateTime(timezone=True), nullable=False, onupdate=lambda: datetime.now(timezone.utc)),
        
    )


class UserCreate(SQLModel):
    """Schema for creating a user."""
    email: str
    display_name: str
    oidc_sub: Optional[str] = None
    oidc_provider: Optional[str] = None
    avatar_url: Optional[str] = None


class UserRead(SQLModel):
    """Schema for reading a user (public fields)."""
    id: uuid.UUID
    email: str
    display_name: str
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime
