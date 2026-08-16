"""CollectionRating model — a user's 1-5 star rating of a collection."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, Uuid
from sqlmodel import Column, DateTime, Field, Integer, SQLModel


class CollectionRating(SQLModel, table=True):
    """A single user's rating of a collection. `Collection.avg_rating` and
    `Collection.rating_count` are a denormalized cache of these rows,
    recomputed on every write/delete — this table is the source of truth."""

    __tablename__ = "collection_ratings"
    __table_args__ = (
        UniqueConstraint("collection_id", "user_id", name="uq_collection_ratings_collection_user"),
        CheckConstraint("stars >= 1 AND stars <= 5", name="ck_collection_ratings_stars_range"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    collection_id: uuid.UUID = Field(
        sa_column=Column("collection_id", Uuid, ForeignKey("collections.id"), nullable=False),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column("user_id", Uuid, ForeignKey("users.id"), nullable=False),
    )
    stars: int = Field(sa_column=Column("stars", Integer, nullable=False))
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


class CollectionRatingRead(SQLModel):
    """Schema for reading a rating summary."""
    avg_rating: float
    rating_count: int
    my_rating: int | None = None
