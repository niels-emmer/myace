"""SMTP email sending — password-reset emails and the admin test-email button."""

import logging
from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings
from app.services.effective_settings import SmtpConfig

logger = logging.getLogger("myace")


class EmailSendError(RuntimeError):
    """Raised when an email could not be sent (missing config, SMTP error)."""


async def send_email(
    config: SmtpConfig,
    to: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    """Send an email via SMTP using the given effective config."""
    if not config.host:
        raise EmailSendError("SMTP is not configured (no host set).")

    message = EmailMessage()
    message["From"] = (
        f"{config.from_name} <{config.from_email}>" if config.from_name else config.from_email
    )
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=config.host,
            port=config.port,
            username=config.username or None,
            password=config.password or None,
            start_tls=config.use_tls,
        )
    except (aiosmtplib.SMTPException, OSError) as exc:
        raise EmailSendError(f"Failed to send email via SMTP: {exc}") from exc


def build_password_reset_email(reset_link: str) -> tuple[str, str]:
    """Return (subject, text_body) for a password-reset email."""
    subject = f"Reset your {settings.app_name} password"
    body = (
        f"We received a request to reset your {settings.app_name} password.\n\n"
        f"Click the link below to choose a new password. This link expires in 1 hour "
        f"and can only be used once.\n\n{reset_link}\n\n"
        f"If you didn't request this, you can safely ignore this email."
    )
    return subject, body


def build_moderation_approved_email(collection_name: str) -> tuple[str, str]:
    """Return (subject, text_body) for a submission-approved email."""
    subject = f'Your collection "{collection_name}" was approved'
    body = (
        f'Good news — your submission "{collection_name}" has been reviewed and '
        f"approved. It's now live in the {settings.app_name} community collections."
    )
    return subject, body


def build_moderation_denied_email(collection_name: str, reason: str) -> tuple[str, str]:
    """Return (subject, text_body) for a submission-denied email."""
    subject = f'Your collection "{collection_name}" was not approved'
    body = (
        f'Your submission "{collection_name}" was reviewed and was not approved '
        f"for the {settings.app_name} community collections.\n\n"
        f"Reviewer's note:\n{reason}\n\n"
        f"You can edit the collection and resubmit it for another review."
    )
    return subject, body


def build_moderation_unpublished_email(collection_name: str, reason: str | None) -> tuple[str, str]:
    """Return (subject, text_body) for a moderator-initiated unpublish email.

    Only sent when the actor isn't the owner themselves — an owner
    unpublishing their own collection doesn't need to be told about it."""
    subject = f'Your collection "{collection_name}" was unpublished'
    body = (
        f'A moderator removed your collection "{collection_name}" from the '
        f"{settings.app_name} community collections. It's no longer public, "
        f"but you still own it and can edit it.\n\n"
    )
    if reason:
        body += f"Reviewer's note:\n{reason}\n\n"
    body += "You can resubmit it for another review once it's ready."
    return subject, body


def build_comment_notification_email(collection_name: str, commenter_name: str) -> tuple[str, str]:
    """Return (subject, text_body) for a new-comment notification email."""
    subject = f'New comment on "{collection_name}"'
    body = (
        f'{commenter_name} left a comment on your collection "{collection_name}" '
        f"in the {settings.app_name} community collections."
    )
    return subject, body


def build_download_digest_email(collection_name: str, download_delta: int) -> tuple[str, str]:
    """Return (subject, text_body) for a daily download-digest email."""
    plural = "download" if download_delta == 1 else "downloads"
    subject = f'"{collection_name}" got {download_delta} new {plural}'
    body = (
        f'Your collection "{collection_name}" received {download_delta} new {plural} '
        f"since your last digest."
    )
    return subject, body


def build_freshness_digest_email(count: int) -> tuple[str, str]:
    """Return (subject, text_body) for the weekly collection-freshness
    digest sent to moderators/admins by
    app/scripts/check_collection_freshness.py.
    """
    plural = "collection" if count == 1 else "collections"
    subject = f"{count} community {plural} need a freshness re-check"
    body = (
        f"{count} approved community {plural} in {settings.app_name} either have never been "
        f"manually verified or haven't been re-checked in over "
        f"{settings.collection_freshness_threshold_days} days.\n\n"
        f"Visit the Freshness Queue in the admin area to review and verify them."
    )
    return subject, body
