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
