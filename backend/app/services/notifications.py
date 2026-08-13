"""
Notification service for DevBoard.

Sends email notifications via SMTP (smtplib) when an issue's status changes.
SMTP settings are read from environment variables: SMTP_HOST, SMTP_PORT,
SMTP_USER, SMTP_PASS.
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_SMTP_PORT = 587
ISSUE_URL_TEMPLATE = "https://devboard.example/issues/{issue_id}"


async def send_status_change_notification(
    issue_id: int,
    issue_title: str,
    old_status: str,
    new_status: str,
    assignee_email: Optional[str] = None,
    reporter_email: Optional[str] = None,
) -> None:
    """
    Send an email to the issue reporter when the issue's status changes.

    If SMTP_HOST is not configured (or there is no reporter email), log a
    warning and return without sending.
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

    smtp_host = os.getenv("SMTP_HOST")
    if not smtp_host:
        logger.warning(
            "SMTP_HOST is not configured; skipping status change email for issue #%d",
            issue_id,
        )
        return

    if not reporter_email:
        logger.warning(
            "No reporter email for issue #%d; skipping status change email",
            issue_id,
        )
        return

    smtp_port = int(os.getenv("SMTP_PORT", DEFAULT_SMTP_PORT))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    body = (
        f"Hello,\n\n"
        f"The status of issue #{issue_id} ('{issue_title}') has changed:\n\n"
        f"  Old status: {old_status}\n"
        f"  New status: {new_status}\n\n"
        f"View the issue: {ISSUE_URL_TEMPLATE.format(issue_id=issue_id)}\n"
    )

    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = f"[DevBoard] Issue #{issue_id} status changed: {old_status} -> {new_status}"
    message["From"] = smtp_user or "devboard@example.com"
    message["To"] = reporter_email

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
        if smtp_port == DEFAULT_SMTP_PORT:
            smtp.starttls()
        if smtp_user:
            smtp.login(smtp_user, smtp_pass)
        smtp.send_message(message)

    logger.info(
        "Sent status change email for issue #%d to %s",
        issue_id,
        reporter_email,
    )