"""Tests for sort= on GET /collections/community and GET /moderation/queue."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collection import Collection
from app.models.user import User


async def _create_user(db_session: AsyncSession, email: str, password: str = "userpass123") -> uuid.UUID:
    from app.core.security import hash_password

    user = User(email=email, display_name=email.split("@")[0], password_hash=hash_password(password))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user.id


async def _login(async_client: AsyncClient, email: str, password: str = "userpass123") -> None:
    resp = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


async def _make_approved(
    db_session: AsyncSession, owner_id: uuid.UUID, name: str, downloads: int, avg_rating: float
) -> Collection:
    coll = Collection(
        owner_id=owner_id, name=name, git_url="https://example.com/repo.git",
        visibility="public", published=True, moderation_status="approved",
        download_count=downloads, avg_rating=avg_rating, category="test",
    )
    db_session.add(coll)
    await db_session.commit()
    await db_session.refresh(coll)
    return coll


class TestCommunitySort:
    @pytest.mark.asyncio
    async def test_sort_by_downloads_default(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        owner_id = await _create_user(db_session, "owner@test.com")
        await _make_approved(db_session, owner_id, "low-downloads", downloads=1, avg_rating=5.0)
        await _make_approved(db_session, owner_id, "high-downloads", downloads=100, avg_rating=1.0)

        await _login(async_client, "owner@test.com")
        res = await async_client.get("/api/v1/collections/community")
        names = [c["name"] for c in res.json()["items"]]
        assert names.index("high-downloads") < names.index("low-downloads")

    @pytest.mark.asyncio
    async def test_sort_by_rating(self, async_client: AsyncClient, db_session: AsyncSession):
        owner_id = await _create_user(db_session, "owner@test.com")
        await _make_approved(db_session, owner_id, "low-rated", downloads=100, avg_rating=1.0)
        await _make_approved(db_session, owner_id, "high-rated", downloads=1, avg_rating=5.0)

        await _login(async_client, "owner@test.com")
        res = await async_client.get("/api/v1/collections/community?sort=rating")
        names = [c["name"] for c in res.json()["items"]]
        assert names.index("high-rated") < names.index("low-rated")

    @pytest.mark.asyncio
    async def test_sort_alpha(self, async_client: AsyncClient, db_session: AsyncSession):
        owner_id = await _create_user(db_session, "owner@test.com")
        await _make_approved(db_session, owner_id, "zeta", downloads=100, avg_rating=1.0)
        await _make_approved(db_session, owner_id, "alpha", downloads=1, avg_rating=5.0)

        await _login(async_client, "owner@test.com")
        res = await async_client.get("/api/v1/collections/community?sort=alpha")
        names = [c["name"] for c in res.json()["items"]]
        assert names.index("alpha") < names.index("zeta")


class TestModerationQueueSort:
    @pytest.mark.asyncio
    async def test_default_oldest_submitted_first(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        from datetime import UTC, datetime, timedelta

        owner_id = await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com")
        from sqlmodel import select

        result = await db_session.execute(select(User).where(User.email == "mod@test.com"))
        mod = result.scalar_one()
        mod.role = "moderator"
        db_session.add(mod)
        await db_session.commit()

        now = datetime.now(UTC)
        older = Collection(
            owner_id=owner_id, name="older-submission", git_url="https://example.com/repo.git",
            moderation_status="submitted", submitted_at=now - timedelta(hours=2),
        )
        newer = Collection(
            owner_id=owner_id, name="newer-submission", git_url="https://example.com/repo.git",
            moderation_status="submitted", submitted_at=now,
        )
        db_session.add(older)
        db_session.add(newer)
        await db_session.commit()

        await _login(async_client, "mod@test.com")
        res = await async_client.get("/api/v1/moderation/queue")
        names = [c["name"] for c in res.json()]
        assert names.index("older-submission") < names.index("newer-submission")

    @pytest.mark.asyncio
    async def test_queue_sort_override_alpha(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        owner_id = await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com")
        from sqlmodel import select

        result = await db_session.execute(select(User).where(User.email == "mod@test.com"))
        mod = result.scalar_one()
        mod.role = "moderator"
        db_session.add(mod)
        await db_session.commit()

        db_session.add(Collection(
            owner_id=owner_id, name="zeta", git_url="https://example.com/repo.git",
            moderation_status="submitted",
        ))
        db_session.add(Collection(
            owner_id=owner_id, name="alpha", git_url="https://example.com/repo.git",
            moderation_status="submitted",
        ))
        await db_session.commit()

        await _login(async_client, "mod@test.com")
        res = await async_client.get("/api/v1/moderation/queue?sort=alpha")
        names = [c["name"] for c in res.json()]
        assert names.index("alpha") < names.index("zeta")
