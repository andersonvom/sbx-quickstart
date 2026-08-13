"""
Notification service for DevBoard.

Sends email notifications when an issue status changes using the smtplib
standard library (no third-party dependencies). SMTP settings are read from
environment variables:

    SMTP_HOST  — SMTP server hostname
    SMTP_PORT  — SMTP server port (default 587)
    SMTP_USER  — username for SMTP authentication
    SMTP_PASS  — password for SMTP authentication

If SMTP config is missing, a warning is logged and sending is skipped
rather than crashing.
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


async def send_status_change_notification(
    issue_id: int,
    issue_title: str,
    old_status: str,
    new_status: str,
    assignee_email: Optional[str] = None,
    reporter_email: Optional[str] = None,
) -> None:
    """
    Notify the issue reporter when an issue status changes.

    Skips sending (with a logged warning) when SMTP config is missing or
    no reporter email is available. Send failures are logged but do not
    propagate, so a broken mail server never breaks the API.
    """
    logger.info(
        "[NOTIFY] Issue #%d ('%s') changed: %s → %s | "
        "assignee=%s reporter=%s",
        issue_id,
        issue_title,
        old_status,
        new_status,
        assignee_email or "unassigned",
        reporter_email or "unknown",
    )

    if not reporter_email:
        logger.warning("[NOTIFY] No reporter email for issue #%d — skipping", issue_id)
        return

    host = os.getenv("SMTP_HOST")
    if not host:
        logger.warning("[NOTIFY] SMTP_HOST not set — skipping email for issue #%d", issue_id)
        return

    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASS", "")

    link = f"https://devboard.example.com/issues/{issue_id}"
    body = (
        f"Issue '{issue_title}' (#{issue_id}) changed status from "
        f"'{old_status}' to '{new_status}'.\n\n"
        f"View it at: {link}"
    )
    message = MIMEText(body)
    message["Subject"] = f"[DevBoard] Issue #{issue_id} status update"
    message["From"] = user or "devboard@example.com"
    message["To"] = reporter_email

    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            if user:
                smtp.starttls()
                smtp.login(user, password)
            smtp.send_message(message)
        logger.info("[NOTIFY] Sent status-change email for issue #%d to %s", issue_id, reporter_email)
    except Exception as exc:
        logger.warning("[NOTIFY] Failed to send email for issue #%d: %s", issue_id, exc)