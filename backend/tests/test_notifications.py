"""
Tests for the notification service.

Run these tests with:  pytest tests/test_notifications.py -v
"""

from unittest.mock import MagicMock, patch

import smtplib

import pytest

from app.services.notifications import send_status_change_notification


@pytest.mark.asyncio
@patch("app.services.notifications.smtplib.SMTP")
async def test_send_status_change_notification_sends_email(mock_smtp):
    """With SMTP config present, an email is sent to the reporter."""
    smtp_instance = MagicMock()
    mock_smtp.return_value.__enter__.return_value = smtp_instance

    with patch.dict(
        "os.environ",
        {
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "devboard",
            "SMTP_PASS": "secret",
        },
        clear=False,
    ):
        await send_status_change_notification(
            issue_id=42,
            issue_title="Login broken",
            old_status="open",
            new_status="in_progress",
            reporter_email="reporter@example.com",
        )

    mock_smtp.assert_called_once_with("smtp.example.com", 587, timeout=10)
    smtp_instance.starttls.assert_called_once_with()
    smtp_instance.login.assert_called_once_with("devboard", "secret")
    smtp_instance.send_message.assert_called_once()

    message = smtp_instance.send_message.call_args.args[0]
    assert message["To"] == "reporter@example.com"
    assert message["Subject"] == "[DevBoard] Issue #42 status update"
    payload = message.get_payload()
    assert "Login broken" in payload
    assert "open" in payload
    assert "in_progress" in payload
    assert "https://devboard.example.com/issues/42" in payload


@pytest.mark.asyncio
@patch("app.services.notifications.smtplib.SMTP")
async def test_missing_smtp_host_skips_sending(mock_smtp):
    """Missing SMTP_HOST should log a warning and return without sending."""
    with patch.dict("os.environ", {"SMTP_HOST": ""}, clear=False):
        await send_status_change_notification(
            issue_id=1,
            issue_title="Login broken",
            old_status="open",
            new_status="closed",
            reporter_email="reporter@example.com",
        )

    mock_smtp.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.notifications.smtplib.SMTP")
async def test_no_reporter_email_skips_sending(mock_smtp):
    """With no reporter email, sending should be skipped."""
    with patch.dict(
        "os.environ",
        {"SMTP_HOST": "smtp.example.com", "SMTP_PORT": "587"},
        clear=False,
    ):
        await send_status_change_notification(
            issue_id=2,
            issue_title="Login broken",
            old_status="open",
            new_status="closed",
        )

    mock_smtp.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.notifications.smtplib.SMTP")
async def test_smtp_send_failure_is_logged_not_raised(mock_smtp):
    """A failing SMTP server should not crash the caller."""
    smtp_instance = MagicMock()
    smtp_instance.send_message.side_effect = smtplib.SMTPException("connection refused")
    mock_smtp.return_value.__enter__.return_value = smtp_instance

    with patch.dict(
        "os.environ",
        {"SMTP_HOST": "smtp.example.com", "SMTP_PORT": "587"},
        clear=False,
    ):
        await send_status_change_notification(
            issue_id=3,
            issue_title="Login broken",
            old_status="open",
            new_status="closed",
            reporter_email="reporter@example.com",
        )

    smtp_instance.send_message.assert_called_once()