"""Tests for the first-user-becomes-admin bootstrap and its ADMIN_BOOTSTRAP_ENABLED gate."""

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str) -> dict:
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "display_name": "Test User"},
    )
    assert res.status_code == 201
    return res.json()


@pytest.mark.asyncio
async def test_first_registered_user_becomes_admin_by_default(async_client: AsyncClient) -> None:
    user = await _register(async_client, "first@example.com")
    assert user["is_admin"] is True


@pytest.mark.asyncio
async def test_second_registered_user_is_not_admin(async_client: AsyncClient) -> None:
    await _register(async_client, "first@example.com")

    # A second client is needed so the second registration doesn't inherit
    # the first user's session cookie.
    from httpx import ASGITransport

    from app.main import app as fastapi_app

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as second_client:
        second_user = await _register(second_client, "second@example.com")

    assert second_user["is_admin"] is False


@pytest.mark.asyncio
async def test_bootstrap_disabled_first_user_is_not_admin(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.auth.settings.admin_bootstrap_enabled", False)

    user = await _register(async_client, "first@example.com")
    assert user["is_admin"] is False


@pytest.mark.asyncio
async def test_admin_emails_promoted_regardless_of_bootstrap_flag(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.api.auth.settings.admin_bootstrap_enabled", False)
    monkeypatch.setattr("app.api.auth.settings.admin_emails", "admin@example.com")

    user = await _register(async_client, "admin@example.com")
    assert user["is_admin"] is True
