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
    client: AsyncClient,
    collection_id: str,
    name: str = "zip-test-profile",
    additional_collection_ids: list[str] | None = None,
) -> str:
    res = await client.post(
        "/api/v1/profiles",
        json={
            "name": name,
            "base_collection_id": collection_id,
            "additional_collection_ids": additional_collection_ids or [],
        },
    )
    assert res.status_code == 201
    return res.json()["id"]


async def _create_collection_with_named_artifact(
    client: AsyncClient, db_session: AsyncSession, collection_name: str, artifact_name: str
) -> str:
    res = await client.post(
        "/api/v1/collections",
        json={"name": collection_name, "git_url": "https://example.com/repo.git"},
    )
    assert res.status_code == 201
    collection_id = res.json()["id"]

    db_session.add(
        Artifact(
            collection_id=uuid.UUID(collection_id),
            artifact_type="rule",
            name=artifact_name,
            priority=50,
            body="Some rule body.",
            file_path=f"rules/{artifact_name}.md",
        )
    )
    await db_session.commit()

    return collection_id


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
async def test_compile_zip_unknown_target_returns_422(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client)
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id)

    res = await async_client.post(
        "/api/v1/profiles/compile/zip",
        json={"profile_id": profile_id, "target": "nonexistent-target"},
    )
    # Literal type validation rejects invalid targets at the schema level
    assert res.status_code == 422


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "target", ["claude-code", "opencode", "cursor", "codex-cli", "copilot-cli", "cline", "windsurf"]
)
async def test_compile_accepts_every_registered_adapter(
    async_client: AsyncClient, db_session: AsyncSession, target: str
) -> None:
    """Every adapter registered in app.adapters must be a valid compile target,
    not just the original three — a stale Literal here 422s before the request
    ever reaches a perfectly working adapter."""
    await _register(async_client)
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id)

    res = await async_client.post(
        "/api/v1/profiles/compile",
        json={"profile_id": profile_id, "target": target},
    )
    assert res.status_code == 200
    assert "error" not in res.json()


@pytest.mark.asyncio
async def test_compile_reports_no_warnings_when_no_collision(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client)
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id)

    res = await async_client.post(
        "/api/v1/profiles/compile",
        json={"profile_id": profile_id, "target": "claude-code"},
    )
    assert res.status_code == 200
    assert res.json()["warnings"] == []


@pytest.mark.asyncio
async def test_compile_reports_name_collision_warning(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Two collections in one profile sharing an artifact name must produce
    exactly one name_collision warning naming both collections."""
    await _register(async_client)
    base_id = await _create_collection_with_named_artifact(
        async_client, db_session, "base-collection", "shared-rule"
    )
    additional_id = await _create_collection_with_named_artifact(
        async_client, db_session, "additional-collection", "shared-rule"
    )
    profile_id = await _create_profile(
        async_client, base_id, additional_collection_ids=[additional_id]
    )

    res = await async_client.post(
        "/api/v1/profiles/compile",
        json={"profile_id": profile_id, "target": "claude-code"},
    )
    assert res.status_code == 200
    warnings = res.json()["warnings"]
    assert len(warnings) == 1
    warning = warnings[0]
    assert warning["level"] == "warning"
    assert warning["code"] == "name_collision"
    assert "base-collection" in warning["message"]
    assert "additional-collection" in warning["message"]
    assert "shared-rule" in warning["message"]


@pytest.mark.asyncio
async def test_compile_zip_includes_warnings_file_only_when_present(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client)
    base_id = await _create_collection_with_named_artifact(
        async_client, db_session, "zip-base-collection", "zip-shared-rule"
    )
    additional_id = await _create_collection_with_named_artifact(
        async_client, db_session, "zip-additional-collection", "zip-shared-rule"
    )
    colliding_profile_id = await _create_profile(
        async_client, base_id, name="zip-colliding-profile", additional_collection_ids=[additional_id]
    )
    clean_profile_id = await _create_profile(async_client, base_id, name="zip-clean-profile")

    colliding_res = await async_client.post(
        "/api/v1/profiles/compile/zip",
        json={"profile_id": colliding_profile_id, "target": "claude-code"},
    )
    assert colliding_res.status_code == 200
    with zipfile.ZipFile(io.BytesIO(colliding_res.content)) as zf:
        assert "_myace_warnings.txt" in zf.namelist()
        warnings_text = zf.read("_myace_warnings.txt").decode("utf-8")
        assert "name_collision" in warnings_text
        assert "zip-base-collection" in warnings_text
        assert "zip-additional-collection" in warnings_text

    clean_res = await async_client.post(
        "/api/v1/profiles/compile/zip",
        json={"profile_id": clean_profile_id, "target": "claude-code"},
    )
    assert clean_res.status_code == 200
    with zipfile.ZipFile(io.BytesIO(clean_res.content)) as zf:
        assert "_myace_warnings.txt" not in zf.namelist()


@pytest.mark.asyncio
async def test_deleted_profile_excluded_from_list(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client)
    collection_id = await _create_collection_with_artifact(async_client, db_session)
    profile_id = await _create_profile(async_client, collection_id)

    delete_res = await async_client.delete(f"/api/v1/profiles/{profile_id}")
    assert delete_res.status_code == 200

    list_res = await async_client.get("/api/v1/profiles")
    assert list_res.status_code == 200
    assert profile_id not in [p["id"] for p in list_res.json()]

    get_res = await async_client.get(f"/api/v1/profiles/{profile_id}")
    assert get_res.status_code == 404
