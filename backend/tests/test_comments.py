"""Tests for collection comments."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact
from app.models.collection import Collection
from app.models.user import User


async def _create_user(
    db_session: AsyncSession,
    email: str,
    password: str = "userpass123",
    role: str = "user",
    notify_on_comment: bool = False,
) -> uuid.UUID:
    from app.core.security import hash_password

    user = User(
        email=email, display_name=email.split("@")[0],
        password_hash=hash_password(password), is_admin=(role == "admin"), role=role,
        notify_on_comment=notify_on_comment,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user.id


async def _login(async_client: AsyncClient, email: str, password: str = "userpass123") -> None:
    resp = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


async def _create_approved_collection(
    async_client: AsyncClient, db_session: AsyncSession, owner_email: str, name: str = "comment-me"
) -> str:
    await _login(async_client, owner_email)
    res = await async_client.post(
        "/api/v1/collections",
        json={"name": name, "git_url": "https://example.com/repo.git"},
    )
    collection_id = res.json()["id"]
    db_session.add(Artifact(
        collection_id=uuid.UUID(collection_id), artifact_type="rule",
        name="r", priority=50, body="body", file_path="rules/r.md",
    ))
    await db_session.commit()
    await async_client.post(
        f"/api/v1/collections/{collection_id}/publish", json={"category": "python"}
    )
    coll = await db_session.get(Collection, uuid.UUID(collection_id))
    coll.moderation_status = "approved"
    coll.published = True
    coll.visibility = "public"
    await db_session.commit()
    await async_client.post("/api/v1/auth/logout")
    return collection_id


class TestCreateComment:
    @pytest.mark.asyncio
    async def test_create_comment(self, async_client: AsyncClient, db_session: AsyncSession):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "commenter@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "commenter@test.com")
        res = await async_client.post(
            f"/api/v1/collections/{collection_id}/comments", json={"body": "Great collection!"}
        )
        assert res.status_code == 201
        data = res.json()
        assert data["body"] == "Great collection!"
        assert data["author_display_name"] == "commenter"

    @pytest.mark.asyncio
    async def test_comment_on_non_approved_collection_404s(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "commenter@test.com")
        await _login(async_client, "owner@test.com")
        res = await async_client.post(
            "/api/v1/collections",
            json={"name": "draft-coll", "git_url": "https://example.com/repo.git"},
        )
        draft_id = res.json()["id"]
        await async_client.post("/api/v1/auth/logout")

        await _login(async_client, "commenter@test.com")
        res = await async_client.post(
            f"/api/v1/collections/{draft_id}/comments", json={"body": "hi"}
        )
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_comment_too_long_rejected(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "commenter@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "commenter@test.com")
        res = await async_client.post(
            f"/api/v1/collections/{collection_id}/comments", json={"body": "x" * 2001}
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_comment_rejected(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "commenter@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "commenter@test.com")
        res = await async_client.post(
            f"/api/v1/collections/{collection_id}/comments", json={"body": ""}
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_comment_notification_sent_when_preference_on(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com", notify_on_comment=True)
        await _create_user(db_session, "commenter@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        from app.services.effective_settings import SmtpConfig

        await _login(async_client, "commenter@test.com")
        with patch("app.api.comments.send_email", new=AsyncMock()) as mock_send:
            with patch("app.api.comments.get_effective_smtp_config") as mock_cfg:
                mock_cfg.return_value = SmtpConfig(
                    host="smtp.test", port=587, username="", password="",
                    from_email="a@b.com", from_name="", use_tls=True, enabled=True,
                )
                res = await async_client.post(
                    f"/api/v1/collections/{collection_id}/comments", json={"body": "hi"}
                )
        assert res.status_code == 201
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_comment_creation_survives_email_failure(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com", notify_on_comment=True)
        await _create_user(db_session, "commenter@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        from app.services.effective_settings import SmtpConfig
        from app.services.email import EmailSendError

        await _login(async_client, "commenter@test.com")
        with patch(
            "app.api.comments.send_email", new=AsyncMock(side_effect=EmailSendError("down"))
        ):
            with patch("app.api.comments.get_effective_smtp_config") as mock_cfg:
                mock_cfg.return_value = SmtpConfig(
                    host="smtp.test", port=587, username="", password="",
                    from_email="a@b.com", from_name="", use_tls=True, enabled=True,
                )
                res = await async_client.post(
                    f"/api/v1/collections/{collection_id}/comments", json={"body": "hi"}
                )
        assert res.status_code == 201

    @pytest.mark.asyncio
    async def test_no_notification_when_preference_off(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com", notify_on_comment=False)
        await _create_user(db_session, "commenter@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "commenter@test.com")
        with patch("app.api.comments.send_email", new=AsyncMock()) as mock_send:
            res = await async_client.post(
                f"/api/v1/collections/{collection_id}/comments", json={"body": "hi"}
            )
        assert res.status_code == 201
        mock_send.assert_not_called()


class TestListComments:
    @pytest.mark.asyncio
    async def test_list_excludes_deleted(self, async_client: AsyncClient, db_session: AsyncSession):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "commenter@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "commenter@test.com")
        res = await async_client.post(
            f"/api/v1/collections/{collection_id}/comments", json={"body": "will be deleted"}
        )
        comment_id = res.json()["id"]
        await async_client.delete(f"/api/v1/collections/{collection_id}/comments/{comment_id}")

        res = await async_client.get(f"/api/v1/collections/{collection_id}/comments")
        assert res.status_code == 200
        assert res.json() == []

    @pytest.mark.asyncio
    async def test_list_newest_first(self, async_client: AsyncClient, db_session: AsyncSession):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "commenter@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "commenter@test.com")
        await async_client.post(
            f"/api/v1/collections/{collection_id}/comments", json={"body": "first"}
        )
        await async_client.post(
            f"/api/v1/collections/{collection_id}/comments", json={"body": "second"}
        )
        res = await async_client.get(f"/api/v1/collections/{collection_id}/comments")
        bodies = [c["body"] for c in res.json()]
        assert bodies == ["second", "first"]


class TestDeleteComment:
    @pytest.mark.asyncio
    async def test_author_can_delete_own_comment(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "commenter@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "commenter@test.com")
        res = await async_client.post(
            f"/api/v1/collections/{collection_id}/comments", json={"body": "mine"}
        )
        comment_id = res.json()["id"]
        res = await async_client.delete(
            f"/api/v1/collections/{collection_id}/comments/{comment_id}"
        )
        assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_collection_owner_can_delete_comment(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "commenter@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "commenter@test.com")
        res = await async_client.post(
            f"/api/v1/collections/{collection_id}/comments", json={"body": "spam"}
        )
        comment_id = res.json()["id"]
        await async_client.post("/api/v1/auth/logout")

        await _login(async_client, "owner@test.com")
        res = await async_client.delete(
            f"/api/v1/collections/{collection_id}/comments/{comment_id}"
        )
        assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_moderator_can_delete_comment(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "commenter@test.com")
        await _create_user(db_session, "mod@test.com", role="moderator")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "commenter@test.com")
        res = await async_client.post(
            f"/api/v1/collections/{collection_id}/comments", json={"body": "spam"}
        )
        comment_id = res.json()["id"]
        await async_client.post("/api/v1/auth/logout")

        await _login(async_client, "mod@test.com")
        res = await async_client.delete(
            f"/api/v1/collections/{collection_id}/comments/{comment_id}"
        )
        assert res.status_code == 200

    @pytest.mark.asyncio
    async def test_unrelated_user_forbidden(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        await _create_user(db_session, "commenter@test.com")
        await _create_user(db_session, "outsider@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "commenter@test.com")
        res = await async_client.post(
            f"/api/v1/collections/{collection_id}/comments", json={"body": "mine"}
        )
        comment_id = res.json()["id"]
        await async_client.post("/api/v1/auth/logout")

        await _login(async_client, "outsider@test.com")
        res = await async_client.delete(
            f"/api/v1/collections/{collection_id}/comments/{comment_id}"
        )
        assert res.status_code == 403

    @pytest.mark.asyncio
    async def test_unknown_comment_404(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user(db_session, "owner@test.com")
        collection_id = await _create_approved_collection(async_client, db_session, "owner@test.com")

        await _login(async_client, "owner@test.com")
        res = await async_client.delete(
            f"/api/v1/collections/{collection_id}/comments/{uuid.uuid4()}"
        )
        assert res.status_code == 404
