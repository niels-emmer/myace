"""Anonymous pack install (ADR-0018) and the public framework list.

Pins the boundary rather than just the happy path: only approved + published +
active packs compile, disabled items never appear, an unknown target yields
guidance instead of an error, an admin-disabled target is a hard 400, and
fetching never moves a counter.
"""

import io
import json
import uuid
import zipfile

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.artifact import Artifact
from app.models.collection import Collection
from app.models.profile import Profile
from app.models.system_settings import SystemSettings
from app.services.compiler import compile_pack, compile_profile

INSTALL = "/api/v1/collections/community/{id}/install.md"


async def _seed_pack(
    session: AsyncSession,
    *,
    name: str = "Public Pack",
    published: bool = True,
    moderation_status: str = "approved",
    is_active: bool = True,
    visibility: str = "public",
) -> Collection:
    collection = Collection(
        owner_id=uuid.uuid4(),
        name=name,
        description="A pack for install tests",
        git_url="https://example.com/pack.git",
        collection_type="base",
        visibility=visibility,
        is_active=is_active,
        published=published,
        moderation_status=moderation_status,
        category="Testing",
    )
    session.add(collection)
    await session.commit()
    await session.refresh(collection)
    return collection


async def _seed_artifact(
    session: AsyncSession,
    collection_id: uuid.UUID,
    name: str,
    *,
    body: str = "A rule body.",
    enabled: bool = True,
) -> Artifact:
    artifact = Artifact(
        collection_id=collection_id,
        artifact_type="rule",
        name=name,
        priority=50,
        body=body,
        file_path="AGENTS.md",
        is_enabled=enabled,
    )
    session.add(artifact)
    await session.commit()
    await session.refresh(artifact)
    return artifact


@pytest.mark.asyncio
async def test_markdown_install_for_public_pack(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    pack = await _seed_pack(db_session)
    await _seed_artifact(db_session, pack.id, "primary-rule", body="Primary rule body.")

    resp = await async_client.get(INSTALL.format(id=pack.id) + "?target=claude-code")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    assert "CLAUDE.md" in resp.text
    assert "Primary rule body." in resp.text
    assert "sha256:" in resp.text
    assert resp.headers["etag"].startswith('W/"')
    assert resp.headers["x-robots-tag"] == "noindex"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs",
    [
        {"published": False, "moderation_status": "draft"},
        {"published": False, "moderation_status": "submitted"},
        {"published": True, "moderation_status": "submitted"},
        {"is_active": False},
    ],
)
async def test_non_public_packs_are_404(
    async_client: AsyncClient, db_session: AsyncSession, kwargs: dict[str, object]
) -> None:
    pack = await _seed_pack(db_session, **kwargs)
    await _seed_artifact(db_session, pack.id, "hidden-rule")

    resp = await async_client.get(INSTALL.format(id=pack.id) + "?target=claude-code")

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_omitted_target_returns_guidance_not_422(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    pack = await _seed_pack(db_session)

    resp = await async_client.get(INSTALL.format(id=pack.id))

    assert resp.status_code == 200
    assert "Choose a coding framework" in resp.text
    assert "claude-code" in resp.text
    assert "target=claude-code" in resp.text


@pytest.mark.asyncio
async def test_unrecognised_target_returns_guidance_not_400(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    pack = await _seed_pack(db_session)

    resp = await async_client.get(INSTALL.format(id=pack.id) + "?target=not-a-framework")

    assert resp.status_code == 200
    assert "not recognised" in resp.text
    assert "not-a-framework" in resp.text


@pytest.mark.asyncio
async def test_guidance_ignores_requested_format(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """`?target=typo&format=zip` must still return readable markdown."""
    pack = await _seed_pack(db_session)

    resp = await async_client.get(INSTALL.format(id=pack.id) + "?target=typo&format=zip")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")


@pytest.mark.asyncio
async def test_admin_disabled_target_is_400(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    pack = await _seed_pack(db_session)
    await _seed_artifact(db_session, pack.id, "a-rule")
    db_session.add(SystemSettings(id=1, disabled_adapters=json.dumps(["cursor"])))
    await db_session.commit()

    resp = await async_client.get(INSTALL.format(id=pack.id) + "?target=cursor")

    assert resp.status_code == 400
    assert "disabled" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_json_format_carries_pack_discriminator(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    pack = await _seed_pack(db_session)
    await _seed_artifact(db_session, pack.id, "json-rule", body="Json body.")

    resp = await async_client.get(
        INSTALL.format(id=pack.id) + "?target=claude-code&format=json"
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["subject"] == "pack"
    assert body["pack_id"] == str(pack.id)
    # The field is present only because the envelope requires it; branch on
    # `subject`, never on this id being a setup.
    assert body["profile_id"] == body["pack_id"]
    assert "Json body." in body["files"]["CLAUDE.md"]


@pytest.mark.asyncio
async def test_zip_format_contains_compiled_files(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    pack = await _seed_pack(db_session, name="Zip Pack")
    await _seed_artifact(db_session, pack.id, "zip-rule", body="Zip body.")

    resp = await async_client.get(
        INSTALL.format(id=pack.id) + "?target=claude-code&format=zip"
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "zip-pack.claude-code.zip" in resp.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        names = zf.namelist()
        assert "CLAUDE.md" in names
        # No bookkeeping file when there are no warnings.
        assert "_myace_warnings.txt" not in names


@pytest.mark.asyncio
async def test_with_composes_a_second_public_pack(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _seed_pack(db_session, name="Base Pack")
    addon = await _seed_pack(db_session, name="Addon Pack")
    await _seed_artifact(db_session, base.id, "base-rule", body="Base body.")
    await _seed_artifact(db_session, addon.id, "addon-rule", body="Addon body.")

    resp = await async_client.get(
        INSTALL.format(id=base.id) + f"?target=claude-code&format=json&with={addon.id}"
    )

    assert resp.status_code == 200
    files = resp.json()["files"]
    assert "Base body." in files["CLAUDE.md"]
    assert "Addon body." in files["CLAUDE.md"]


@pytest.mark.asyncio
async def test_with_non_public_pack_is_404(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _seed_pack(db_session, name="Base Pack")
    draft = await _seed_pack(
        db_session, name="Draft Addon", published=False, moderation_status="draft"
    )

    resp = await async_client.get(
        INSTALL.format(id=base.id) + f"?target=claude-code&with={draft.id}"
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_name_collision_across_composed_packs_is_reported(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _seed_pack(db_session, name="Base Pack")
    addon = await _seed_pack(db_session, name="Addon Pack")
    await _seed_artifact(db_session, base.id, "shared-rule", body="Base version.")
    await _seed_artifact(db_session, addon.id, "shared-rule", body="Addon version.")

    resp = await async_client.get(
        INSTALL.format(id=base.id) + f"?target=claude-code&format=json&with={addon.id}"
    )

    assert resp.status_code == 200
    codes = [w["code"] for w in resp.json()["warnings"]]
    assert "name_collision" in codes


@pytest.mark.asyncio
async def test_disabled_items_are_excluded(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    pack = await _seed_pack(db_session)
    await _seed_artifact(db_session, pack.id, "live-rule", body="Live body.")
    await _seed_artifact(
        db_session, pack.id, "off-rule", body="Off body.", enabled=False
    )

    resp = await async_client.get(
        INSTALL.format(id=pack.id) + "?target=claude-code&format=json"
    )

    assert resp.status_code == 200
    assert "Live body." in resp.json()["files"]["CLAUDE.md"]
    assert "Off body." not in resp.json()["files"]["CLAUDE.md"]


@pytest.mark.asyncio
async def test_download_count_never_moves(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    pack = await _seed_pack(db_session)
    await _seed_artifact(db_session, pack.id, "counted-rule")

    for _ in range(3):
        resp = await async_client.get(INSTALL.format(id=pack.id) + "?target=claude-code")
        assert resp.status_code == 200

    await db_session.refresh(pack)
    assert pack.download_count == 0


@pytest.mark.asyncio
async def test_etag_revalidation_is_304(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    pack = await _seed_pack(db_session)
    await _seed_artifact(db_session, pack.id, "etag-rule")

    first = await async_client.get(INSTALL.format(id=pack.id) + "?target=claude-code")
    etag = first.headers["etag"]

    second = await async_client.get(
        INSTALL.format(id=pack.id) + "?target=claude-code",
        headers={"If-None-Match": etag},
    )

    assert second.status_code == 304


@pytest.mark.asyncio
async def test_size_guard_is_413(
    async_client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack = await _seed_pack(db_session)
    await _seed_artifact(db_session, pack.id, "big-rule", body="x" * 500)
    monkeypatch.setattr(settings, "pack_install_max_bytes", 64)

    resp = await async_client.get(INSTALL.format(id=pack.id) + "?target=claude-code")

    assert resp.status_code == 413
    assert "format=zip" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_compile_pack_matches_compile_profile(
    db_session: AsyncSession,
) -> None:
    """A pack compile must be the same compile a one-pack setup gets."""
    pack = await _seed_pack(db_session)
    await _seed_artifact(db_session, pack.id, "parity-rule", body="Parity body.")

    profile = Profile(
        owner_id=uuid.uuid4(),
        name="Single-pack setup",
        base_collection_id=pack.id,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    from_pack = await compile_pack(db_session, [pack.id], "claude-code", pack.name)
    from_setup = await compile_profile(db_session, profile, "claude-code")

    assert from_pack.files == from_setup.files
    assert from_pack.compiled_hash == from_setup.compiled_hash


class TestPublicFrameworks:
    @pytest.mark.asyncio
    async def test_anonymous_list_contains_primary_adapter_names(
        self, async_client: AsyncClient
    ) -> None:
        resp = await async_client.get("/api/v1/frameworks")

        assert resp.status_code == 200
        names = resp.json()
        assert "claude-code" in names
        # Primary names only — never a `supported_targets()` alias (rule 23).
        assert "claude" not in names

    @pytest.mark.asyncio
    async def test_disabled_adapters_are_excluded(
        self, async_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        db_session.add(SystemSettings(id=1, disabled_adapters=json.dumps(["cursor"])))
        await db_session.commit()

        resp = await async_client.get("/api/v1/frameworks")

        assert resp.status_code == 200
        assert "cursor" not in resp.json()
        assert "claude-code" in resp.json()

    @pytest.mark.asyncio
    async def test_authenticated_adapter_route_still_requires_auth(
        self, async_client: AsyncClient
    ) -> None:
        assert (await async_client.get("/api/v1/adapters")).status_code == 401
