"""Tests for the download-digest script (app.scripts.send_download_digests)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collection import Collection
from app.models.user import User
from app.scripts.send_download_digests import send_download_digests
from app.services.effective_settings import SmtpConfig

ENABLED_SMTP = SmtpConfig(
    host="smtp.test", port=587, username="", password="",
    from_email="a@b.com", from_name="", use_tls=True, enabled=True,
)
DISABLED_SMTP = SmtpConfig(
    host="", port=587, username="", password="", from_email="", from_name="",
    use_tls=True, enabled=False,
)


async def _create_owner(db_session: AsyncSession, notify_on_download: bool = True) -> User:
    from app.core.security import hash_password

    user = User(
        email="owner@test.com", display_name="owner",
        password_hash=hash_password("userpass123"), notify_on_download=notify_on_download,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_collection(
    db_session: AsyncSession, owner_id: uuid.UUID, download_count: int, last_digest: int = 0
) -> Collection:
    coll = Collection(
        owner_id=owner_id, name="digest-me", git_url="https://example.com/repo.git",
        download_count=download_count, last_digest_download_count=last_digest,
    )
    db_session.add(coll)
    await db_session.commit()
    await db_session.refresh(coll)
    return coll


class TestSendDownloadDigests:
    @pytest.mark.asyncio
    async def test_sends_when_delta_positive_and_preference_on(
        self, db_session: AsyncSession
    ):
        owner = await _create_owner(db_session, notify_on_download=True)
        coll = await _create_collection(db_session, owner.id, download_count=10, last_digest=2)

        with patch(
            "app.scripts.send_download_digests.get_effective_smtp_config",
            new=AsyncMock(return_value=ENABLED_SMTP),
        ):
            with patch(
                "app.scripts.send_download_digests.send_email", new=AsyncMock()
            ) as mock_send:
                await send_download_digests(db_session)

        mock_send.assert_called_once()
        await db_session.refresh(coll)
        assert coll.last_digest_download_count == 10
        assert coll.last_digest_sent_at is not None

    @pytest.mark.asyncio
    async def test_no_send_when_delta_zero(self, db_session: AsyncSession):
        owner = await _create_owner(db_session, notify_on_download=True)
        await _create_collection(db_session, owner.id, download_count=5, last_digest=5)

        with patch(
            "app.scripts.send_download_digests.get_effective_smtp_config",
            new=AsyncMock(return_value=ENABLED_SMTP),
        ):
            with patch(
                "app.scripts.send_download_digests.send_email", new=AsyncMock()
            ) as mock_send:
                await send_download_digests(db_session)

        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_send_when_preference_off(self, db_session: AsyncSession):
        owner = await _create_owner(db_session, notify_on_download=False)
        coll = await _create_collection(db_session, owner.id, download_count=10, last_digest=2)

        with patch(
            "app.scripts.send_download_digests.get_effective_smtp_config",
            new=AsyncMock(return_value=ENABLED_SMTP),
        ):
            with patch(
                "app.scripts.send_download_digests.send_email", new=AsyncMock()
            ) as mock_send:
                await send_download_digests(db_session)

        mock_send.assert_not_called()
        # Watermark still advances even though nothing was sent.
        await db_session.refresh(coll)
        assert coll.last_digest_download_count == 10

    @pytest.mark.asyncio
    async def test_watermark_advances_on_send_failure(self, db_session: AsyncSession):
        from app.services.email import EmailSendError

        owner = await _create_owner(db_session, notify_on_download=True)
        coll = await _create_collection(db_session, owner.id, download_count=10, last_digest=2)

        with patch(
            "app.scripts.send_download_digests.get_effective_smtp_config",
            new=AsyncMock(return_value=ENABLED_SMTP),
        ):
            with patch(
                "app.scripts.send_download_digests.send_email",
                new=AsyncMock(side_effect=EmailSendError("down")),
            ):
                await send_download_digests(db_session)

        await db_session.refresh(coll)
        assert coll.last_digest_download_count == 10

    @pytest.mark.asyncio
    async def test_skips_entirely_when_smtp_disabled(self, db_session: AsyncSession):
        owner = await _create_owner(db_session, notify_on_download=True)
        coll = await _create_collection(db_session, owner.id, download_count=10, last_digest=2)

        with patch(
            "app.scripts.send_download_digests.get_effective_smtp_config",
            new=AsyncMock(return_value=DISABLED_SMTP),
        ):
            with patch(
                "app.scripts.send_download_digests.send_email", new=AsyncMock()
            ) as mock_send:
                await send_download_digests(db_session)

        mock_send.assert_not_called()
        # No watermark advance either — the whole run is skipped.
        await db_session.refresh(coll)
        assert coll.last_digest_download_count == 2
