"""Transactional email (optional SMTP)."""

import logging
import smtplib
from email.message import EmailMessage

from quack_db.config import get_settings

log = logging.getLogger(__name__)


def send_api_key_email(to_email: str, plaintext_key: str) -> None:
    s = get_settings()
    if not s.smtp_host:
        log.warning("SMTP not configured — API key email not sent to %s", to_email)
        return
    msg = EmailMessage()
    msg["Subject"] = "Your API key"
    msg["From"] = s.smtp_from or s.smtp_user
    msg["To"] = to_email
    msg.set_content(
        "Your API key (store it securely; it is not shown again):\n\n"
        f"{plaintext_key}\n\n"
        "Use header: X-API-Key: <key> or Authorization: Bearer <key>\n"
    )
    with smtplib.SMTP(s.smtp_host, s.smtp_port) as smtp:
        if s.smtp_use_tls:
            smtp.starttls()
        if s.smtp_user:
            smtp.login(s.smtp_user, s.smtp_password)
        smtp.send_message(msg)
