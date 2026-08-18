"""Tests for the community moderation queue: submit -> approve/deny."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact
from app.models.user import User


async def _create_user(
    db_session: AsyncSession, email: str, password: str = "userpass123", role: str = "user"
) -> uuid.UUID:
    from app.core.security import hash_password

    user = User(
        email=email, display_name=email.split("@")[0],
        password_hash=hash_password(password), is_admin=(role == "admin"), role=role,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user.id


async def _login(async_client: AsyncClient, email: str, password: str = "userpass123") -> None:
    resp = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


async def _create_submitted_collection(
    async_client: AsyncClient, db_session: AsyncSession, owner_email: str
) -> str:
    await _login(async_client, owner_email)
    res = await async_client.post(
        "/api/v1/collections",
        json={"name": "sub-me", "git_url": "https://example.com/repo.git", "visibility": "private"},
    )
    assert res.status_code == 201
    collection_id = res.json()["id"]

    db_session.add(Artifact(
        collection_id=uuid.UUID(collection_id), artifact_type="rule",
        name="r", priority=50, body="body", file_path="rules/r.md",
    ))
    await db_session.commit()

    res = await async_client.post(
        f"/api/v1/collections/{collection_id}/publish", json={"category": "python"}
    )
    assert res.status_code == 200
    assert res.json()["moderation_status"] == "submitted"
    await async_client.post("/api/v1/auth/logout")
    return collection_id


class TestQueue:
    @pytest.mark.asyncio
    async def test_moderator_sees_submitted_collections(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "mod@test.com")
        res = await async_client.get("/api/v1/moderation/queue")
        assert res.status_code == 200
        assert any(c["id"] == collection_id for c in res.json())

    @pytest.mark.asyncio
    async def test_plain_user_forbidden(self, async_client: AsyncClient, db_session: AsyncSession):
        await _create_user(db_session, "user@test.com")
        await _login(async_client, "user@test.com")
        res = await async_client.get("/api/v1/moderation/queue")
        assert res.status_code == 403


class TestApprove:
    @pytest.mark.asyncio
    async def test_moderator_can_approve(self, async_client: AsyncClient, db_session: AsyncSession):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "mod@test.com")
        res = await async_client.post(f"/api/v1/moderation/{collection_id}/approve")
        assert res.status_code == 200
        data = res.json()
        assert data["moderation_status"] == "approved"
        assert data["published"] is True
        assert data["visibility"] == "public"
        assert data["moderated_at"] is not None

        # Now visible in the community listing.
        res = await async_client.get("/api/v1/collections/community")
        assert any(c["id"] == collection_id for c in res.json()["items"])

    @pytest.mark.asyncio
    async def test_owner_cannot_approve_own_collection(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Owner is neither moderator nor admin -> 403, even for their own
        submission. Owners never self-approve."""
        await _create_user(db_session, "owner@test.com")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "owner@test.com")
        res = await async_client.post(f"/api/v1/moderation/{collection_id}/approve")
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_moderator_who_owns_the_collection_cannot_self_approve(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """The self-approval block must hold even when the owner *is* a
        moderator/admin — require_moderator_or_admin alone only checks
        role, not ownership, so this needs its own explicit guard."""
        await _create_user(db_session, "modowner@test.com", role="moderator")
        collection_id = await _create_submitted_collection(
            async_client, db_session, "modowner@test.com"
        )

        await _login(async_client, "modowner@test.com")
        res = await async_client.post(f"/api/v1/moderation/{collection_id}/approve")
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_double_approve_404s(self, async_client: AsyncClient, db_session: AsyncSession):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "mod@test.com")
        res = await async_client.post(f"/api/v1/moderation/{collection_id}/approve")
        assert res.status_code == 200

        res = await async_client.post(f"/api/v1/moderation/{collection_id}/approve")
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_cannot_approve_a_draft_collection(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com", role="user")
        await _create_user(db_session, "mod@test.com", role="moderator")

        await _login(async_client, "owner@test.com")
        res = await async_client.post(
            "/api/v1/collections",
            json={"name": "draft-coll", "git_url": "https://example.com/repo.git"},
        )
        draft_id = res.json()["id"]
        await async_client.post("/api/v1/auth/logout")

        await _login(async_client, "mod@test.com")
        res = await async_client.post(f"/api/v1/moderation/{draft_id}/approve")
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_email_failure_does_not_roll_back_state(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")

        from app.services.effective_settings import SmtpConfig
        from app.services.email import EmailSendError

        await _login(async_client, "mod@test.com")
        with patch(
            "app.api.moderation.send_email",
            new=AsyncMock(side_effect=EmailSendError("smtp down")),
        ):
            with patch("app.api.moderation.get_effective_smtp_config") as mock_cfg:
                mock_cfg.return_value = SmtpConfig(
                    host="smtp.test", port=587, username="", password="",
                    from_email="a@b.com", from_name="", use_tls=True, enabled=True,
                )
                res = await async_client.post(f"/api/v1/moderation/{collection_id}/approve")

        # The approve/deny DB state change must commit even when the
        # best-effort notification email fails.
        assert res.status_code == 200
        assert res.json()["moderation_status"] == "approved"


class TestDeny:
    @pytest.mark.asyncio
    async def test_moderator_can_deny_with_reason(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "mod@test.com")
        res = await async_client.post(
            f"/api/v1/moderation/{collection_id}/deny", json={"reason": "Missing license info"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["moderation_status"] == "denied"
        assert data["moderation_reason"] == "Missing license info"
        assert data["published"] is False

    @pytest.mark.asyncio
    async def test_deny_requires_non_empty_reason(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "mod@test.com")
        res = await async_client.post(
            f"/api/v1/moderation/{collection_id}/deny", json={"reason": "  "}
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_resubmit_after_denial(self, async_client: AsyncClient, db_session: AsyncSession):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "mod@test.com")
        res = await async_client.post(
            f"/api/v1/moderation/{collection_id}/deny", json={"reason": "Needs work"}
        )
        assert res.status_code == 200
        await async_client.post("/api/v1/auth/logout")

        await _login(async_client, "owner@test.com")
        res = await async_client.post(
            f"/api/v1/collections/{collection_id}/publish", json={"category": "python"}
        )
        assert res.status_code == 200
        assert res.json()["moderation_status"] == "submitted"

    @pytest.mark.asyncio
    async def test_owner_cannot_deny_own_collection(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "owner@test.com")
        res = await async_client.post(
            f"/api/v1/moderation/{collection_id}/deny", json={"reason": "self-review"}
        )
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_moderator_who_owns_the_collection_cannot_self_deny(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "modowner@test.com", role="moderator")
        collection_id = await _create_submitted_collection(
            async_client, db_session, "modowner@test.com"
        )

        await _login(async_client, "modowner@test.com")
        res = await async_client.post(
            f"/api/v1/moderation/{collection_id}/deny", json={"reason": "self-review"}
        )
        assert res.status_code == 403


class TestMetaEdit:
    @pytest.mark.asyncio
    async def test_moderator_can_edit_meta_on_approved_collection(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """A moderator should be able to fix a typo on an already-approved
        collection too, not just mid-review."""
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "mod@test.com")
        res = await async_client.post(f"/api/v1/moderation/{collection_id}/approve")
        assert res.status_code == 200
        assert res.json()["moderation_status"] == "approved"

        res = await async_client.patch(
            f"/api/v1/moderation/{collection_id}/meta",
            json={"name": "Fixed Name", "category": "devops"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Fixed Name"
        assert data["category"] == "devops"
        assert data["moderation_status"] == "approved"

    @pytest.mark.asyncio
    async def test_partial_update_only_touches_provided_fields(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "mod@test.com")
        res = await async_client.patch(
            f"/api/v1/moderation/{collection_id}/meta", json={"category": "new-category"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["category"] == "new-category"
        assert data["name"] == "sub-me"  # unchanged

    @pytest.mark.asyncio
    async def test_admin_can_edit_meta(self, async_client: AsyncClient, db_session: AsyncSession):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "admin@test.com", role="admin")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "admin@test.com")
        res = await async_client.patch(
            f"/api/v1/moderation/{collection_id}/meta", json={"description": "Better description"}
        )
        assert res.status_code == 200
        assert res.json()["description"] == "Better description"

    @pytest.mark.asyncio
    async def test_plain_user_forbidden(self, async_client: AsyncClient, db_session: AsyncSession):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "outsider@test.com")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "outsider@test.com")
        res = await async_client.patch(
            f"/api/v1/moderation/{collection_id}/meta", json={"name": "Hijacked"}
        )
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_owner_who_is_not_moderator_forbidden(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """The collection's own owner must use their existing
        PATCH /collections/{id} route, not this moderator-only one."""
        await _create_user(db_session, "owner@test.com")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "owner@test.com")
        res = await async_client.patch(
            f"/api/v1/moderation/{collection_id}/meta", json={"name": "Self Edit"}
        )
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_unknown_collection_404(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "mod@test.com", role="moderator")
        await _login(async_client, "mod@test.com")

        res = await async_client.patch(
            f"/api/v1/moderation/{uuid.uuid4()}/meta", json={"name": "Nope"}
        )
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_never_submitted_draft_collection_404s(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """A moderator has no standing reason to read or edit a collection
        that's never been submitted to the queue — it's purely private to
        its owner. moderation_status == 'draft' must 404 here even though
        the collection genuinely exists."""
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")

        await _login(async_client, "owner@test.com")
        res = await async_client.post(
            "/api/v1/collections",
            json={"name": "private-draft", "git_url": "https://example.com/repo.git"},
        )
        draft_id = res.json()["id"]
        assert res.json()["moderation_status"] == "draft"
        await async_client.post("/api/v1/auth/logout")

        await _login(async_client, "mod@test.com")
        res = await async_client.patch(
            f"/api/v1/moderation/{draft_id}/meta", json={"name": "Hijacked"}
        )
        assert res.status_code == 404


async def _approve(async_client: AsyncClient, collection_id: str, moderator_email: str) -> None:
    await _login(async_client, moderator_email)
    res = await async_client.post(f"/api/v1/moderation/{collection_id}/approve")
    assert res.status_code == 200
    await async_client.post("/api/v1/auth/logout")


class TestUnpublish:
    @pytest.mark.asyncio
    async def test_owner_can_unpublish_own_approved_collection(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")
        await _approve(async_client, collection_id, "mod@test.com")

        await _login(async_client, "owner@test.com")
        res = await async_client.post(f"/api/v1/collections/{collection_id}/unpublish")
        assert res.status_code == 200
        data = res.json()
        assert data["moderation_status"] == "unpublished"
        assert data["published"] is False
        assert data["visibility"] == "private"

        # Gone from the community listing.
        res = await async_client.get("/api/v1/collections/community")
        assert not any(c["id"] == collection_id for c in res.json()["items"])

    @pytest.mark.asyncio
    async def test_moderator_can_unpublish_someone_elses_collection_with_reason(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")
        await _approve(async_client, collection_id, "mod@test.com")

        await _login(async_client, "mod@test.com")
        res = await async_client.post(
            f"/api/v1/collections/{collection_id}/unpublish",
            json={"reason": "Reported for outdated content"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["moderation_status"] == "unpublished"
        assert data["moderation_reason"] == "Reported for outdated content"

    @pytest.mark.asyncio
    async def test_admin_can_unpublish(self, async_client: AsyncClient, db_session: AsyncSession):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        await _create_user(db_session, "admin@test.com", role="admin")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")
        await _approve(async_client, collection_id, "mod@test.com")

        await _login(async_client, "admin@test.com")
        res = await async_client.post(f"/api/v1/collections/{collection_id}/unpublish")
        assert res.status_code == 200
        assert res.json()["moderation_status"] == "unpublished"

    @pytest.mark.asyncio
    async def test_outsider_cannot_unpublish(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        await _create_user(db_session, "outsider@test.com")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")
        await _approve(async_client, collection_id, "mod@test.com")

        await _login(async_client, "outsider@test.com")
        res = await async_client.post(f"/api/v1/collections/{collection_id}/unpublish")
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_cannot_unpublish_a_non_approved_collection(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "owner@test.com")
        res = await async_client.post(f"/api/v1/collections/{collection_id}/unpublish")
        assert res.status_code == 409

    @pytest.mark.asyncio
    async def test_resubmit_after_unpublish(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")
        await _approve(async_client, collection_id, "mod@test.com")

        await _login(async_client, "owner@test.com")
        res = await async_client.post(f"/api/v1/collections/{collection_id}/unpublish")
        assert res.status_code == 200

        res = await async_client.post(
            f"/api/v1/collections/{collection_id}/publish", json={"category": "python"}
        )
        assert res.status_code == 200
        assert res.json()["moderation_status"] == "submitted"

    @pytest.mark.asyncio
    async def test_unpublish_email_failure_does_not_roll_back_state(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")
        await _approve(async_client, collection_id, "mod@test.com")

        from app.services.effective_settings import SmtpConfig
        from app.services.email import EmailSendError

        await _login(async_client, "mod@test.com")
        with patch(
            "app.api.collections.send_email",
            new=AsyncMock(side_effect=EmailSendError("smtp down")),
        ):
            with patch("app.api.collections.get_effective_smtp_config") as mock_cfg:
                mock_cfg.return_value = SmtpConfig(
                    host="smtp.test", port=587, username="", password="",
                    from_email="a@b.com", from_name="", use_tls=True, enabled=True,
                )
                res = await async_client.post(f"/api/v1/collections/{collection_id}/unpublish")

        assert res.status_code == 200
        assert res.json()["moderation_status"] == "unpublished"


class TestModeratorReadAccess:
    @pytest.mark.asyncio
    async def test_moderator_can_view_submitted_collection_detail(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """A moderator needs to actually open a submission to review it —
        require_moderator_or_admin only gates the queue actions, not the
        plain GET /collections/{id} route the frontend uses to render it."""
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "mod@test.com")
        res = await async_client.get(f"/api/v1/collections/{collection_id}")
        assert res.status_code == 200

        res = await async_client.get(f"/api/v1/collections/{collection_id}/artifacts")
        assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_moderator_cannot_view_a_never_submitted_draft(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Same scope boundary as the moderator meta-edit endpoint (rule
        30): a draft that's never been submitted stays purely private to
        its owner, even from a moderator."""
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")

        await _login(async_client, "owner@test.com")
        res = await async_client.post(
            "/api/v1/collections",
            json={"name": "private-draft", "git_url": "https://example.com/repo.git"},
        )
        draft_id = res.json()["id"]
        await async_client.post("/api/v1/auth/logout")

        await _login(async_client, "mod@test.com")
        res = await async_client.get(f"/api/v1/collections/{draft_id}")
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_moderator_can_view_an_unpublished_collection(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        collection_id = await _create_submitted_collection(async_client, db_session, "owner@test.com")
        await _approve(async_client, collection_id, "mod@test.com")

        await _login(async_client, "owner@test.com")
        res = await async_client.post(f"/api/v1/collections/{collection_id}/unpublish")
        assert res.status_code == 200
        await async_client.post("/api/v1/auth/logout")

        await _login(async_client, "mod@test.com")
        res = await async_client.get(f"/api/v1/collections/{collection_id}")
        assert res.status_code == 200
