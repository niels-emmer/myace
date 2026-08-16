"""Tests for the weekly freshness-digest script
(app.scripts.check_collection_freshness)."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.collection import Collection
from app.models.user import User
from app.scripts.check_collection_freshness import check_collection_freshness
from app.services.effective_settings import SmtpConfig

ENABLED_SMTP = SmtpConfig(
    host="smtp.test", port=587, username="", password="",
    from_email="a@b.com", from_name="", use_tls=True, enabled=True,
)
DISABLED_SMTP = SmtpConfig(
    host="", port=587, username="", password="", from_email="", from_name="",
    use_tls=True, enabled=False,
)


async def _create_moderator(db_session: AsyncSession) -> User:
    from app.core.security import hash_password

    user = User(
        email="mod@test.com", display_name="mod",
        password_hash=hash_password("modpass123"), role="moderator",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_owner(db_session: AsyncSession) -> User:
    from app.core.security import hash_password

    user = User(
        email="owner@test.com", display_name="owner",
        password_hash=hash_password("ownerpass123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_collection(
    db_session: AsyncSession, owner_id, last_verified_at: date | None,
) -> Collection:
    coll = Collection(
        owner_id=owner_id, name="freshness-digest-test",
        git_url="https://example.com/repo.git",
        moderation_status="approved", published=True, visibility="public",
        last_verified_at=last_verified_at,
    )
    db_session.add(coll)
    await db_session.commit()
    await db_session.refresh(coll)
    return coll


class TestCheckCollectionFreshness:
    @pytest.mark.asyncio
    async def test_emails_moderators_when_count_positive(self, db_session: AsyncSession) -> None:
        mod = await _create_moderator(db_session)
        owner = await _create_owner(db_session)
        await _create_collection(db_session, owner.id, None)

        with patch(
            "app.scripts.check_collection_freshness.get_effective_smtp_config",
            new=AsyncMock(return_value=ENABLED_SMTP),
        ):
            with patch(
                "app.scripts.check_collection_freshness.send_email", new=AsyncMock()
            ) as mock_send:
                await check_collection_freshness(db_session)

        mock_send.assert_called_once()
        assert mock_send.call_args.kwargs["to"] == mod.email

    @pytest.mark.asyncio
    async def test_no_email_when_count_zero(self, db_session: AsyncSession) -> None:
        await _create_moderator(db_session)
        owner = await _create_owner(db_session)
        await _create_collection(db_session, owner.id, date.today())

        with patch(
            "app.scripts.check_collection_freshness.get_effective_smtp_config",
            new=AsyncMock(return_value=ENABLED_SMTP),
        ):
            with patch(
                "app.scripts.check_collection_freshness.send_email", new=AsyncMock()
            ) as mock_send:
                await check_collection_freshness(db_session)

        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_entirely_when_smtp_disabled(self, db_session: AsyncSession) -> None:
        await _create_moderator(db_session)
        owner = await _create_owner(db_session)
        await _create_collection(db_session, owner.id, None)

        with patch(
            "app.scripts.check_collection_freshness.get_effective_smtp_config",
            new=AsyncMock(return_value=DISABLED_SMTP),
        ):
            with patch(
                "app.scripts.check_collection_freshness.send_email", new=AsyncMock()
            ) as mock_send:
                await check_collection_freshness(db_session)

        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_one_recipient_send_failure_does_not_stop_the_next(
        self, db_session: AsyncSession
    ) -> None:
        from app.services.email import EmailSendError

        await _create_moderator(db_session)
        # A second moderator so we can verify the loop continues past a failure.
        from app.core.security import hash_password

        second = User(
            email="mod2@test.com", display_name="mod2",
            password_hash=hash_password("modpass123"), role="moderator",
        )
        db_session.add(second)
        await db_session.commit()

        owner = await _create_owner(db_session)
        await _create_collection(
            db_session, owner.id,
            date.today() - timedelta(days=settings.collection_freshness_threshold_days + 1),
        )

        with patch(
            "app.scripts.check_collection_freshness.get_effective_smtp_config",
            new=AsyncMock(return_value=ENABLED_SMTP),
        ):
            with patch(
                "app.scripts.check_collection_freshness.send_email",
                new=AsyncMock(side_effect=[EmailSendError("down"), None]),
            ) as mock_send:
                await check_collection_freshness(db_session)

        assert mock_send.call_count == 2
