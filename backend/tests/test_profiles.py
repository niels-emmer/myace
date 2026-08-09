"""Tests for profile compilation routes, including the browser zip download."""

import io
import uuid
import zipfile

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact


async def _register(client: AsyncClient) -> None:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "zip-test@example.com",
            "password": "password123",
            "display_name": "Zip Test",
        },
    )
    assert res.status_code == 201


async def _create_collection_with_artifact(client: AsyncClient, db_session: AsyncSession) -> str:
    res = await client.post(
        "/api/v1/collections",
        json={"name": "zip-test-collection", "git_url": "https://example.com/repo.git"},
    )
    assert res.status_code == 201
    collection_id = res.json()["id"]

    db_session.add(
        Artifact(
            collection_id=uuid.UUID(collection_id),
            artifact_type="rule",
            name="test-rule",
            priority=80,
            body="Always use type annotations.",
            file_path="rules/test-rule.md",
        )
    )
    await db_session.commit()

    return collection_id


async def _create_profile(
    client: AsyncClient, collection_id: str, name: str = "zip-test-profile"
) -> str:
    res = await client.post(
        "/api/v1/profiles",
        json={"name": name, "base_collection_id": collection_id},
    )
    assert res.status_code == 201
    return res.json()["id"]


@pytest.mark.asyncio
async def test_compile_zip_matches_json_files(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client)
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id)

    json_res = await async_client.post(
        "/api/v1/profiles/compile",
        json={"profile_id": profile_id, "target": "claude-code"},
    )
    assert json_res.status_code == 200
    expected_files = json_res.json()["files"]

    zip_res = await async_client.post(
        "/api/v1/profiles/compile/zip",
        json={"profile_id": profile_id, "target": "claude-code"},
    )
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"
    assert "attachment" in zip_res.headers["content-disposition"]
    assert "zip-test-profile-claude-code.zip" in zip_res.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(zip_res.content)) as zf:
        assert set(zf.namelist()) == set(expected_files.keys())
        for filename, content in expected_files.items():
            assert zf.read(filename).decode("utf-8") == content


@pytest.mark.asyncio
async def test_compile_zip_unknown_target_returns_400(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client)
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id)

    res = await async_client.post(
        "/api/v1/profiles/compile/zip",
        json={"profile_id": profile_id, "target": "nonexistent-target"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_compile_zip_sanitizes_profile_name_in_header(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """A profile name with CR/LF or quotes must not leak into the raw header value."""
    await _register(async_client)
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    malicious_name = 'evil\r\nSet-Cookie: pwned=1" name="x'
    profile_id = await _create_profile(async_client, collection_id, name=malicious_name)

    res = await async_client.post(
        "/api/v1/profiles/compile/zip",
        json={"profile_id": profile_id, "target": "claude-code"},
    )
    assert res.status_code == 200
    disposition = res.headers["content-disposition"]
    assert "\r" not in disposition
    assert "\n" not in disposition
    assert "Set-Cookie" not in disposition
    assert disposition == 'attachment; filename="evil-set-cookie-pwned-1-name-x-claude-code.zip"'


@pytest.mark.asyncio
async def test_compile_zip_requires_auth(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    res = await async_client.post(
        "/api/v1/profiles/compile/zip",
        json={"profile_id": "00000000-0000-0000-0000-000000000000", "target": "claude-code"},
    )
    assert res.status_code == 401
