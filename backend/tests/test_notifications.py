"""
Tests for the notifications service (email status-change notifications).
"""

import asyncio
import os
from unittest import mock

import pytest

from app.services.notifications import send_status_change_notification

SMTP_ENV_VARS = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS")


@pytest.fixture(autouse=True)
def _clear_smtp_env():
    """Remove SMTP env vars before and after each test."""
    for var in SMTP_ENV_VARS:
        os.environ.pop(var, None)
    yield
    for var in SMTP_ENV_VARS:
        os.environ.pop(var, None)


def test_send_status_change_notification_skips_without_smtp_host(caplog):
    """Without SMTP_HOST configured, log a warning and send nothing."""
    with mock.patch("smtplib.SMTP") as smtp_mock:
        asyncio.run(
            send_status_change_notification(
                issue_id=1,
                issue_title="Bug",
                old_status="open",
                new_status="closed",
                assignee_email="assignee@example.com",
                reporter_email="reporter@example.com",
            )
        )

    smtp_mock.assert_not_called()
    assert "SMTP_HOST" in caplog.text


def test_send_status_change_notification_sends_email():
    """Mock smtplib.SMTP and confirm the email is sent to the reporter."""
    os.environ["SMTP_HOST"] = "smtp.example.com"
    os.environ["SMTP_PORT"] = "587"
    os.environ["SMTP_USER"] = "devboard@example.com"
    os.environ["SMTP_PASS"] = "super-secret"

    with mock.patch("smtplib.SMTP") as smtp_mock:
        smtp = smtp_mock.return_value
        smtp.__enter__.return_value = smtp

        asyncio.run(
            send_status_change_notification(
                issue_id=42,
                issue_title="Login broken",
                old_status="open",
                new_status="in_progress",
                assignee_email="bob@example.com",
                reporter_email="alice@example.com",
            )
        )

    smtp_mock.assert_called_once_with("smtp.example.com", 587, timeout=30)
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("devboard@example.com", "super-secret")
    smtp.send_message.assert_called_once()

    message = smtp.send_message.call_args.args[0]
    assert message["To"] == "alice@example.com"
    assert message["From"] == "devboard@example.com"
    body = message.get_payload(decode=True).decode("utf-8")
    assert "Login broken" in body
    assert "Old status: open" in body
    assert "New status: in_progress" in body
    assert "https://devboard.example/issues/42" in body