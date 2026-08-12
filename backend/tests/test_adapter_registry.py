"""Tests for system-wide adapter enable/disable (admin) and its enforcement."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact


async def _create_admin(db_session: AsyncSession) -> tuple[str, str]:
    from app.core.security import hash_password
    from app.models.user import User

    user = User(
        email="admin@test.com", display_name="Admin",
        password_hash=hash_password("adminpass123"), is_admin=True,
    )
    db_session.add(user)
    await db_session.commit()
    return "admin@test.com", "adminpass123"


async def _login_admin(async_client: AsyncClient, db_session: AsyncSession) -> None:
    email, password = await _create_admin(db_session)
    resp = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


async def _create_profile_with_artifact(async_client: AsyncClient, db_session: AsyncSession) -> str:
    resp = await async_client.post(
        "/api/v1/collections",
        json={"name": "adapter-toggle-collection", "git_url": "https://example.com/repo.git"},
    )
    assert resp.status_code == 201
    collection_id = resp.json()["id"]

    db_session.add(
        Artifact(
            collection_id=uuid.UUID(collection_id),
            artifact_type="rule", name="test-rule", priority=80,
            body="Always use type annotations.", file_path="rules/test-rule.md",
        )
    )
    await db_session.commit()

    resp = await async_client.post(
        "/api/v1/profiles",
        json={"name": "adapter-toggle-profile", "base_collection_id": collection_id},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestAdapterListing:
    @pytest.mark.asyncio
    async def test_all_adapters_enabled_by_default(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        await _login_admin(async_client, db_session)
        resp = await async_client.get("/api/v1/adapters")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        assert all(a["enabled"] is True for a in data)

    @pytest.mark.asyncio
    async def test_single_adapter_enabled_by_default(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        await _login_admin(async_client, db_session)
        resp = await async_client.get("/api/v1/adapters/claude-code")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True


class TestAdapterToggle:
    @pytest.mark.asyncio
    async def test_requires_admin(self, db_session: AsyncSession, async_client: AsyncClient):
        from app.core.security import hash_password
        from app.models.user import User

        user = User(
            email="user@test.com", display_name="User",
            password_hash=hash_password("userpass123"), is_admin=False,
        )
        db_session.add(user)
        await db_session.commit()
        await async_client.post("/api/v1/auth/login", json={"email": "user@test.com", "password": "userpass123"})

        resp = await async_client.patch("/api/v1/admin/adapters/claude-code?enabled=false")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unknown_adapter_404(self, db_session: AsyncSession, async_client: AsyncClient):
        await _login_admin(async_client, db_session)
        resp = await async_client.patch("/api/v1/admin/adapters/bogus-adapter?enabled=false")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_disable_and_reenable_reflected_in_listing(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        await _login_admin(async_client, db_session)

        resp = await async_client.patch("/api/v1/admin/adapters/claude-code?enabled=false")
        assert resp.status_code == 200
        assert resp.json() == {"name": "claude-code", "enabled": False}

        resp = await async_client.get("/api/v1/adapters/claude-code")
        assert resp.json()["enabled"] is False

        resp = await async_client.get("/api/v1/adapters")
        by_name = {a["name"]: a for a in resp.json()}
        assert by_name["claude-code"]["enabled"] is False
        assert by_name["opencode"]["enabled"] is True

        resp = await async_client.patch("/api/v1/admin/adapters/claude-code?enabled=true")
        assert resp.status_code == 200
        resp = await async_client.get("/api/v1/adapters/claude-code")
        assert resp.json()["enabled"] is True

    @pytest.mark.asyncio
    async def test_settings_endpoint_reports_disabled_adapters(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        await _login_admin(async_client, db_session)
        await async_client.patch("/api/v1/admin/adapters/cursor?enabled=false")

        resp = await async_client.get("/api/v1/admin/settings")
        assert resp.json()["disabled_adapters"] == ["cursor"]


class TestCompileEnforcement:
    @pytest.mark.asyncio
    async def test_compile_rejects_disabled_adapter(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        await _login_admin(async_client, db_session)
        profile_id = await _create_profile_with_artifact(async_client, db_session)

        await async_client.patch("/api/v1/admin/adapters/claude-code?enabled=false")

        resp = await async_client.post(
            "/api/v1/profiles/compile", json={"profile_id": profile_id, "target": "claude-code"}
        )
        assert resp.status_code == 400
        assert "disabled" in resp.text.lower()

    @pytest.mark.asyncio
    async def test_compile_zip_rejects_disabled_adapter(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        await _login_admin(async_client, db_session)
        profile_id = await _create_profile_with_artifact(async_client, db_session)

        await async_client.patch("/api/v1/admin/adapters/claude-code?enabled=false")

        resp = await async_client.post(
            "/api/v1/profiles/compile/zip", json={"profile_id": profile_id, "target": "claude-code"}
        )
        assert resp.status_code == 400
        assert "disabled" in resp.text.lower()

    @pytest.mark.asyncio
    async def test_compile_still_works_for_enabled_adapter(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        await _login_admin(async_client, db_session)
        profile_id = await _create_profile_with_artifact(async_client, db_session)

        await async_client.patch("/api/v1/admin/adapters/cursor?enabled=false")

        resp = await async_client.post(
            "/api/v1/profiles/compile", json={"profile_id": profile_id, "target": "claude-code"}
        )
        assert resp.status_code == 200
        assert "files" in resp.json()

    @pytest.mark.asyncio
    async def test_reenabling_restores_compile(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        await _login_admin(async_client, db_session)
        profile_id = await _create_profile_with_artifact(async_client, db_session)

        await async_client.patch("/api/v1/admin/adapters/claude-code?enabled=false")
        await async_client.patch("/api/v1/admin/adapters/claude-code?enabled=true")

        resp = await async_client.post(
            "/api/v1/profiles/compile", json={"profile_id": profile_id, "target": "claude-code"}
        )
        assert resp.status_code == 200
