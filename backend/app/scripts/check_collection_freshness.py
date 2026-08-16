"""Weekly collection-freshness digest — run once a week via cron, not in-process.

    python -m app.scripts.check_collection_freshness

Counts approved, active community collections whose manual
`last_verified_at` is missing or older than
`settings.collection_freshness_threshold_days` (default 6 months — the
same query GET /admin/freshness-queue uses), and if that count is greater
than zero, emails every active moderator/admin a digest so the queue
doesn't silently pile up unnoticed between visits to the admin area.

Same "no in-process scheduler" reasoning as
app/scripts/send_download_digests.py — meant to be invoked by the host's
crontab (see docs/deployment.md). Unlike that script, there's no DB
watermark to protect here (nothing is written on a successful run), so the
only thing a send failure must not do is stop the loop for the next
recipient — logged and skipped, exactly like the download-digest script's
own per-recipient failure handling.
"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.freshness import stale_collections_query
from app.core.database import get_session_factory
from app.models.user import User
from app.services.effective_settings import get_effective_smtp_config
from app.services.email import EmailSendError, build_freshness_digest_email, send_email

logger = logging.getLogger("myace")


async def check_collection_freshness(session: AsyncSession) -> None:
    config = await get_effective_smtp_config(session)
    if not config.enabled:
        logger.info("SMTP is not configured/enabled — skipping freshness digest run.")
        return

    result = await session.execute(stale_collections_query())
    stale_collections = result.scalars().all()
    count = len(stale_collections)

    if count == 0:
        logger.info("Freshness digest run complete: nothing past the threshold, no email sent.")
        return

    # The ignore below is the same mypy/SQLAlchemy stub-gap class as e.g.
    # Artifact.id.in_(...) in app/api/collections.py (a pre-existing,
    # unsuppressed baseline error there) — mypy resolves User.role as a
    # plain `str` rather than a SQLAlchemy ColumnElement in this context,
    # so `.in_()` isn't recognized even though it's correct at runtime.
    recipients_result = await session.execute(
        select(User).where(
            User.role.in_(("moderator", "admin")),  # type: ignore[attr-defined]
            User.is_active == True,
        )
    )
    recipients = recipients_result.scalars().all()

    subject, body = build_freshness_digest_email(count)
    sent = 0
    for recipient in recipients:
        if not recipient.email:
            continue
        try:
            await send_email(config=config, to=recipient.email, subject=subject, text_body=body)
            sent += 1
        except EmailSendError:
            logger.exception(
                "Failed to send freshness-digest email to %s — continuing to the next recipient.",
                recipient.id,
            )

    logger.info(
        "Freshness digest run complete: %d stale collection(s), %d/%d recipient(s) emailed.",
        count, sent, len(recipients),
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    session_factory = get_session_factory()
    async with session_factory() as session:
        await check_collection_freshness(session)


if __name__ == "__main__":
    asyncio.run(main())
