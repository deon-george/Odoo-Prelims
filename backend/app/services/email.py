"""Password-reset email delivery with a development file outbox."""

from __future__ import annotations

import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from urllib.parse import quote

from app.core.config import settings


def build_reset_url(raw_token: str) -> str:
    base = settings.frontend_url.rstrip("/")
    return f"{base}/reset-password?token={quote(raw_token)}"


def _build_message(to_email: str, reset_url: str) -> EmailMessage:
    subject = "Reset your Subscription Management System password"
    body = (
        "Hello,\n\n"
        "We received a request to reset your password.\n\n"
        f"Reset your password using this link (valid for "
        f"{settings.password_reset_token_expire_minutes} minutes):\n\n"
        f"{reset_url}\n\n"
        "If you did not request this, you can safely ignore this email. "
        "Your password will not change.\n"
    )
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email or "no-reply@localhost"
    message["To"] = to_email
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain="localhost")
    message.set_content(body)
    return message


def _write_to_dev_outbox(to_email: str, message: EmailMessage) -> Path:
    outbox = settings.mail_dev_path
    outbox.mkdir(parents=True, exist_ok=True)
    safe_recipient = to_email.replace("@", "_at_").replace("/", "_")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = outbox / f"{stamp}-{safe_recipient}.eml"
    path.write_bytes(bytes(message))
    return path


def send_password_reset_email(to_email: str, raw_token: str) -> Path | None:
    """Send the reset email, or write it to the dev outbox when SMTP is unset.

    Returns the outbox path in development and None when SMTP was used. The
    token is never printed to stdout or application logs.
    """
    reset_url = build_reset_url(raw_token)
    message = _build_message(to_email, reset_url)

    if not settings.smtp_host:
        return _write_to_dev_outbox(to_email, message)

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
        timeout=15,
    ) as server:
        server.ehlo()
        if settings.smtp_tls:
            server.starttls()
            server.ehlo()
        if settings.smtp_username and settings.smtp_password is not None:
            server.login(
                settings.smtp_username,
                settings.smtp_password.get_secret_value(),
            )
        server.send_message(message)
    return None
