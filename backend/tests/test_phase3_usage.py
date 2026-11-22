"""Phase 3 backend: multi-target profiles, install claims, reference freeze,
onboarding completion, and use counts.

See docs/adr/0015-pack-reference-freeze.md.
"""

import io
import json
import uuid
import zipfile

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app as fastapi_app
from app.models.artifact import Artifact
from app.models.collection import Collection
from app.models.profile import Profile
from app.models.user import User

PASSWORD = "password123"


async def _register(client: AsyncClient, email: str) -> dict[str, str]:
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "Phase 3"},
    )
    assert res.status_code == 201
    return res.json()


def _new_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test")


async def _make_collection(
    client: AsyncClient, name: str = "p3-collection", visibility: str = "private"
) -> str:
    res = await client.post(
        "/api/v1/collections",
        json={"name": name, "git_url": "https://example.com/repo.git", "visibility": visibility},
    )
    assert res.status_code == 201
    return str(res.json()["id"])


async def _add_artifact(db_session: AsyncSession, collection_id: str, name: str) -> str:
    artifact = Artifact(
        collection_id=uuid.UUID(collection_id),
        artifact_type="rule",
        name=name,
        priority=50,
        body=f"{name} body",
        file_path=f"rules/{name}.md",
    )
    db_session.add(artifact)
    await db_session.commit()
    return str(artifact.id)


async def _make_profile(
    client: AsyncClient,
    collection_id: str,
    name: str = "p3-profile",
    **extra: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": name,
        "base_collection_id": collection_id,
        **extra,
    }
    res = await client.post("/api/v1/profiles", json=payload)
    assert res.status_code == 201, res.text
    return res.json()


# ─── target_frameworks ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_target_frameworks_filters_unknown_and_serializes(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client, "tf-owner@example.com")
    cid = await _make_collection(async_client)
    created = await _make_profile(
        async_client,
        cid,
        target_frameworks=["claude-code", "not-an-adapter", "opencode"],
    )

    # Unknown adapter names are silently dropped, never 422.
    assert created["target_frameworks"] == ["claude-code", "opencode"]

    got = await async_client.get(f"/api/v1/profiles/{created['id']}")
    assert got.status_code == 200
    assert got.json()["target_frameworks"] == ["claude-code", "opencode"]

    # Stored as JSON text, same convention as additional_collection_ids.
    db_profile = await db_session.get(Profile, uuid.UUID(str(created["id"])))
    assert db_profile is not None
    assert json.loads(db_profile.target_frameworks) == ["claude-code", "opencode"]


@pytest.mark.asyncio
async def test_legacy_target_framework_backfills_new_list(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client, "tf-legacy@example.com")
    cid = await _make_collection(async_client)

    # New writes that only send the deprecated field still populate the list.
    created = await _make_profile(async_client, cid, target_framework="cursor")
    assert created["target_framework"] == "cursor"
    assert created["target_frameworks"] == ["cursor"]


@pytest.mark.asyncio
async def test_migration_backfill_sql_on_legacy_row(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """Exercise the migration's exact backfill statement against a row that
    looks like it predates `target_frameworks` (legacy field set, list
    defaulted to '[]'). Alembic itself isn't run by the test suite, so this
    is the practical model-level equivalent."""
    me = await _register(async_client, "tf-backfill@example.com")
    cid = await _make_collection(async_client)

    profile = Profile(
        owner_id=uuid.UUID(me["id"]),
        name="legacy-profile",
        base_collection_id=uuid.UUID(cid),
        target_framework="cursor",
        target_frameworks="[]",
    )
    db_session.add(profile)
    await db_session.commit()

    await db_session.execute(
        text(
            "UPDATE profiles "
            "SET target_frameworks = '[\"' || target_framework || '\"]' "
            "WHERE target_framework IS NOT NULL AND target_framework <> ''"
        )
    )
    await db_session.commit()

    res = await async_client.get(f"/api/v1/profiles/{profile.id}")
    assert res.status_code == 200
    assert res.json()["target_frameworks"] == ["cursor"]


@pytest.mark.asyncio
async def test_profile_update_refreshes_target_frameworks(
    async_client: AsyncClient,
) -> None:
    await _register(async_client, "tf-update@example.com")
    cid = await _make_collection(async_client)
    created = await _make_profile(async_client, cid, target_frameworks=["cursor"])

    res = await async_client.put(
        f"/api/v1/profiles/{created['id']}",
        json={
            "name": "p3-profile",
            "base_collection_id": cid,
            "target_frameworks": ["opencode", "bogus"],
        },
    )
    assert res.status_code == 200
    assert res.json()["target_frameworks"] == ["opencode"]


# ─── onboarding ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_onboarding_set_and_clear_only_touches_caller(
    async_client: AsyncClient,
) -> None:
    await _register(async_client, "onb-a@example.com")

    async with _new_client() as other:
        await _register(other, "onb-b@example.com")

        set_res = await async_client.patch(
            "/api/v1/auth/me/onboarding", json={"completed": True}
        )
        assert set_res.status_code == 200
        assert set_res.json()["onboarding_completed_at"] is not None

        me = await async_client.get("/api/v1/auth/me")
        assert me.json()["onboarding_completed_at"] is not None

        other_me = await other.get("/api/v1/auth/me")
        assert other_me.json()["onboarding_completed_at"] is None

        # Clearing only clears the caller's timestamp.
        clear_res = await async_client.patch(
            "/api/v1/auth/me/onboarding", json={"completed": False}
        )
        assert clear_res.status_code == 200
        assert clear_res.json()["onboarding_completed_at"] is None


# ─── install claims ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_install_claim_upsert_and_list(async_client: AsyncClient) -> None:
    await _register(async_client, "install-owner@example.com")
    cid = await _make_collection(async_client)
    profile = await _make_profile(async_client, cid)
    url = f"/api/v1/profiles/{profile['id']}/installs"

    first = await async_client.post(
        url, json={"target": "claude-code", "location": "project", "method": "cli"}
    )
    assert first.status_code == 200
    first_body = first.json()

    # Same (user, profile, target, location) upserts the existing row.
    second = await async_client.post(
        url, json={"target": "claude-code", "location": "project", "method": "zip"}
    )
    assert second.status_code == 200
    assert second.json()["id"] == first_body["id"]
    assert second.json()["method"] == "zip"

    # A different location is a distinct claim.
    third = await async_client.post(
        url, json={"target": "claude-code", "location": "machine", "method": "cli"}
    )
    assert third.status_code == 200

    listed = await async_client.get(url)
    assert listed.status_code == 200
    assert len(listed.json()) == 2


@pytest.mark.asyncio
async def test_install_claim_bad_target_is_422(async_client: AsyncClient) -> None:
    await _register(async_client, "install-bad@example.com")
    cid = await _make_collection(async_client)
    profile = await _make_profile(async_client, cid)

    res = await async_client.post(
        f"/api/v1/profiles/{profile['id']}/installs",
        json={"target": "not-an-adapter", "location": "project"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_install_claim_overlong_method_is_422(async_client: AsyncClient) -> None:
    await _register(async_client, "install-method@example.com")
    cid = await _make_collection(async_client)
    profile = await _make_profile(async_client, cid)

    res = await async_client.post(
        f"/api/v1/profiles/{profile['id']}/installs",
        json={"target": "claude-code", "location": "project", "method": "x" * 33},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_install_claim_on_unreadable_profile_is_404(
    async_client: AsyncClient,
) -> None:
    await _register(async_client, "install-private@example.com")
    cid = await _make_collection(async_client)
    profile = await _make_profile(async_client, cid)  # is_public=False

    async with _new_client() as other:
        await _register(other, "install-other@example.com")
        res = await other.post(
            f"/api/v1/profiles/{profile['id']}/installs",
            json={"target": "claude-code", "location": "project"},
        )
        assert res.status_code == 404
        listing = await other.get(f"/api/v1/profiles/{profile['id']}/installs")
        assert listing.status_code == 404


# ─── reference snapshots ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_snapshot_captured_only_for_non_owned_collections(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    async with _new_client() as owner:
        await _register(owner, "snap-owner@example.com")
        shared_cid = await _make_collection(owner, "shared-pack", visibility="public")
        artifact_id = await _add_artifact(db_session, shared_cid, "shared-rule")

        await _register(async_client, "snap-user@example.com")
        own_cid = await _make_collection(async_client, "own-pack")

        referencing = await _make_profile(
            async_client, shared_cid, name="references-shared"
        )
        owned = await _make_profile(async_client, own_cid, name="references-own")

    ref_row = await db_session.get(Profile, uuid.UUID(str(referencing["id"])))
    own_row = await db_session.get(Profile, uuid.UUID(str(owned["id"])))
    assert ref_row is not None and own_row is not None

    snapshots = json.loads(ref_row.pack_snapshots)
    assert str(shared_cid) in snapshots
    assert snapshots[str(shared_cid)]["artifact_ids"] == [artifact_id]
    assert snapshots[str(shared_cid)]["hash"]
    assert snapshots[str(shared_cid)]["captured_at"]

    # An owned collection is never snapshotted.
    assert json.loads(own_row.pack_snapshots) == {}


@pytest.mark.asyncio
async def test_unavailable_pack_compiles_from_frozen_snapshot(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    async with _new_client() as owner:
        await _register(owner, "freeze-owner@example.com")
        cid = await _make_collection(owner, "freeze-pack", visibility="public")
        await _add_artifact(db_session, cid, "frozen-rule")

        await _register(async_client, "freeze-user@example.com")
        profile = await _make_profile(async_client, cid)

        # Owner pulls the pack back to private — the referencing user can
        # no longer read it live.
        patch = await owner.patch(
            f"/api/v1/collections/{cid}", json={"visibility": "private"}
        )
        assert patch.status_code == 200

    res = await async_client.post(
        "/api/v1/profiles/compile",
        json={"profile_id": profile["id"], "target": "claude-code"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["artifact_count"] == 1
    assert "frozen-rule" in "".join(body["files"].values())
    codes = [warning["code"] for warning in body["warnings"]]
    assert "pack_unavailable" in codes


@pytest.mark.asyncio
async def test_no_snapshot_skips_pack_with_warning(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client, "nosnap-owner@example.com")
    cid = await _make_collection(async_client)
    await _add_artifact(db_session, cid, "vanishing-rule")
    profile = await _make_profile(async_client, cid)

    # Owned collections aren't snapshotted; soft-deleting one leaves the
    # profile with nothing to fall back to.
    collection = await db_session.get(Collection, uuid.UUID(cid))
    assert collection is not None
    collection.is_active = False
    await db_session.commit()

    res = await async_client.post(
        "/api/v1/profiles/compile",
        json={"profile_id": profile["id"], "target": "claude-code"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["artifact_count"] == 0
    warnings = [w for w in body["warnings"] if w["code"] == "pack_unavailable"]
    assert len(warnings) == 1
    assert "it was skipped" in warnings[0]["message"]


@pytest.mark.asyncio
async def test_update_profile_keeps_frozen_pack_editable(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """A referenced pack that goes private must not make the profile
    un-editable: the update refreshes/keeps the snapshot and still succeeds.

    Regression test for the review finding on PR #198.
    """
    async with _new_client() as owner:
        await _register(owner, "upd-owner@example.com")
        cid = await _make_collection(owner, "upd-pack", visibility="public")
        await _add_artifact(db_session, cid, "upd-rule")

        await _register(async_client, "upd-user@example.com")
        profile = await _make_profile(async_client, cid)

        patch = await owner.patch(
            f"/api/v1/collections/{cid}", json={"visibility": "private"}
        )
        assert patch.status_code == 200

    # Renaming and changing targets while keeping the now-unreadable pack
    # must return 200, not 404.
    res = await async_client.put(
        f"/api/v1/profiles/{profile['id']}",
        json={
            "name": "renamed-frozen-profile",
            "base_collection_id": cid,
            "target_frameworks": ["opencode"],
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["name"] == "renamed-frozen-profile"
    assert res.json()["target_frameworks"] == ["opencode"]

    # The frozen snapshot survived the update and still compiles.
    compile_res = await async_client.post(
        "/api/v1/profiles/compile",
        json={"profile_id": profile["id"], "target": "claude-code"},
    )
    assert compile_res.status_code == 200
    assert compile_res.json()["artifact_count"] == 1
    assert "upd-rule" in "".join(compile_res.json()["files"].values())


@pytest.mark.asyncio
async def test_update_rejects_newly_added_unreadable_pack(
    async_client: AsyncClient,
) -> None:
    async with _new_client() as other:
        await _register(other, "upd-new-other@example.com")
        private_cid = await _make_collection(other, "other-private-pack")

        await _register(async_client, "upd-new-owner@example.com")
        own_cid = await _make_collection(async_client, "own-pack")
        profile = await _make_profile(async_client, own_cid)

        # Newly adding a pack the caller cannot read is still a 404.
        res = await async_client.put(
            f"/api/v1/profiles/{profile['id']}",
            json={
                "name": "p3-profile",
                "base_collection_id": own_cid,
                "additional_collection_ids": [private_cid],
            },
        )
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_freeze_is_owner_scoped_across_compile_routes(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """The frozen set is served only to the profile owner or an admin.

    A third party compiling the owner's public profile must get
    `pack_unavailable` and zero frozen artifacts — on `/compile`, the zip
    route, and `compile-status` (all of which share `compile_profile()`).
    """
    async with _new_client() as pack_owner:
        await _register(pack_owner, "x-pack-owner@example.com")
        pack_cid = await _make_collection(pack_owner, "x-pack", visibility="public")
        await _add_artifact(db_session, pack_cid, "frozen-rule")

        # A owns the setup, which references X's pack; the profile is public.
        await _register(async_client, "a-setup-owner@example.com")
        profile = await _make_profile(async_client, pack_cid, is_public=True)

        patch = await pack_owner.patch(
            f"/api/v1/collections/{pack_cid}", json={"visibility": "private"}
        )
        assert patch.status_code == 200

    body = {"profile_id": profile["id"], "target": "claude-code"}

    # (1) A (setup owner) still gets the frozen artifact, plus a warning.
    a_res = await async_client.post("/api/v1/profiles/compile", json=body)
    assert a_res.status_code == 200
    a_body = a_res.json()
    assert a_body["artifact_count"] == 1
    assert "frozen-rule" in "".join(a_body["files"].values())
    assert "pack_unavailable" in [w["code"] for w in a_body["warnings"]]

    async with _new_client() as viewer:
        await _register(viewer, "b-viewer@example.com")

        # (2) B (non-owner) compiling A's public profile gets no frozen set.
        b_res = await viewer.post("/api/v1/profiles/compile", json=body)
        assert b_res.status_code == 200
        b_body = b_res.json()
        assert b_body["artifact_count"] == 0
        assert "frozen-rule" not in "".join(b_body["files"].values())
        assert "pack_unavailable" in [w["code"] for w in b_body["warnings"]]

        # Zip route shares compile_profile(); it must not leak the freeze.
        b_zip = await viewer.post("/api/v1/profiles/compile/zip", json=body)
        assert b_zip.status_code == 200
        with zipfile.ZipFile(io.BytesIO(b_zip.content)) as zf:
            zipped = "".join(zf.read(name).decode() for name in zf.namelist())
        assert "frozen-rule" not in zipped

        # compile-status() also funnels through compile_profile(), so the
        # hash must be viewer-dependent here.
        a_status = await async_client.get(
            f"/api/v1/profiles/{profile['id']}/compile-status",
            params={"target": "claude-code"},
        )
        b_status = await viewer.get(
            f"/api/v1/profiles/{profile['id']}/compile-status",
            params={"target": "claude-code"},
        )
        assert a_status.status_code == b_status.status_code == 200
        assert a_status.json()["compiled_hash"] != b_status.json()["compiled_hash"]

    # (3) An admin gets the frozen artifact even when the pack is gone. Use a
    # soft-delete here (not just private visibility) because an admin can
    # still read a private collection live, which would bypass the snapshot.
    async with _new_client() as admin_client:
        admin = await _register(admin_client, "c-admin@example.com")
        admin_row = await db_session.get(User, uuid.UUID(admin["id"]))
        assert admin_row is not None
        admin_row.is_admin = True
        admin_row.role = "admin"
        await db_session.commit()

        pack_row = await db_session.get(Collection, uuid.UUID(pack_cid))
        assert pack_row is not None
        pack_row.is_active = False
        await db_session.commit()

        c_res = await admin_client.post("/api/v1/profiles/compile", json=body)
        assert c_res.status_code == 200
        c_body = c_res.json()
        assert c_body["artifact_count"] == 1
        assert "frozen-rule" in "".join(c_body["files"].values())
        assert "pack_unavailable" in [w["code"] for w in c_body["warnings"]]


# ─── use counts ──────────────────────────────────────────────────────────────


async def _approve(collection_id: str, db_session: AsyncSession) -> None:
    collection = await db_session.get(Collection, uuid.UUID(collection_id))
    assert collection is not None
    collection.moderation_status = "approved"
    collection.published = True
    collection.visibility = "public"
    await db_session.commit()


@pytest.mark.asyncio
async def test_use_increments_and_blocks_owner(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register(async_client, "use-owner@example.com")
    cid = await _make_collection(async_client)
    await _approve(cid, db_session)

    async with _new_client() as user:
        await _register(user, "use-user@example.com")

        first = await user.post(f"/api/v1/collections/{cid}/use")
        assert first.status_code == 200
        assert first.json()["download_count"] == 1

        second = await user.post(f"/api/v1/collections/{cid}/use")
        assert second.status_code == 200
        assert second.json()["download_count"] == 2

    # The owner cannot inflate their own count.
    owner_res = await async_client.post(f"/api/v1/collections/{cid}/use")
    assert owner_res.status_code == 400


@pytest.mark.asyncio
async def test_use_unreadable_collection_is_404(async_client: AsyncClient) -> None:
    await _register(async_client, "use-private-owner@example.com")
    cid = await _make_collection(async_client)  # private draft

    async with _new_client() as other:
        await _register(other, "use-private-other@example.com")
        res = await other.post(f"/api/v1/collections/{cid}/use")
        assert res.status_code == 404
