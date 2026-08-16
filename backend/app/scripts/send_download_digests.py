"""Daily download-digest email — run once a day via cron, not in-process.

    python -m app.scripts.send_download_digests

There is no in-process task scheduler in this backend (no APScheduler/
Celery); adding one for a single daily job wasn't worth it, so this is
meant to be invoked by the host's crontab instead (see docs/deployment.md).
Not safe to run concurrently on multiple hosts — the watermark update
below assumes a single runner.
"""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session_factory
from app.models.collection import Collection
from app.models.user import User
from app.services.effective_settings import get_effective_smtp_config
from app.services.email import EmailSendError, build_download_digest_email, send_email

logger = logging.getLogger("myace")


async def send_download_digests(session: AsyncSession) -> None:
    config = await get_effective_smtp_config(session)
    if not config.enabled:
        logger.info("SMTP is not configured/enabled — skipping download digest run.")
        return

    result = await session.execute(
        select(Collection, User)
        .join(User, User.id == Collection.owner_id)
        .where(Collection.download_count > Collection.last_digest_download_count)
    )
    rows = result.all()
    now = datetime.now(UTC)

    for collection, owner in rows:
        delta = collection.download_count - collection.last_digest_download_count

        if owner.notify_on_download and owner.email:
            subject, body = build_download_digest_email(collection.name, delta)
            try:
                await send_email(config=config, to=owner.email, subject=subject, text_body=body)
            except EmailSendError:
                logger.exception(
                    "Failed to send download-digest email for collection %s — "
                    "advancing the watermark anyway so a bad address doesn't "
                    "cause the delta to balloon forever.", collection.id,
                )

        # Advance the watermark regardless of whether the email actually
        # sent (preference off, no email on file, or a send failure).
        collection.last_digest_download_count = collection.download_count
        collection.last_digest_sent_at = now
        session.add(collection)

    await session.commit()
    logger.info("Download digest run complete: %d collection(s) processed.", len(rows))


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    session_factory = get_session_factory()
    async with session_factory() as session:
        await send_download_digests(session)


if __name__ == "__main__":
    asyncio.run(main())
