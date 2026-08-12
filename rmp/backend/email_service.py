"""Transactional email delivery through Amazon SES."""

import html
import logging
import os
from urllib.parse import urlencode

import boto3

from app_logging import log_event


logger = logging.getLogger("runmypool.email")


def send_password_reset_email(recipient: str, token: str) -> str:
    """Send a one-hour password-reset link without logging the bearer token."""
    region = os.getenv("AWS_SES_REGION", "us-east-1")
    frontend_url = os.getenv("FRONTEND_URL", "https://runmypool.net").rstrip("/")
    sender = os.getenv("EMAIL_FROM", "Run My Pool Accounts <accounts@runmypool.net>")
    reply_to = os.getenv("EMAIL_REPLY_TO", "support@runmypool.net")
    reset_url = f"{frontend_url}/reset-password?{urlencode({'token': token})}"
    safe_url = html.escape(reset_url, quote=True)

    response = boto3.client("sesv2", region_name=region).send_email(
        FromEmailAddress=sender,
        Destination={"ToAddresses": [recipient]},
        ReplyToAddresses=[reply_to],
        Content={
            "Simple": {
                "Subject": {"Data": "Reset your Run My Pool password", "Charset": "UTF-8"},
                "Body": {
                    "Text": {
                        "Data": (
                            "We received a request to reset your Run My Pool password.\n\n"
                            f"Reset your password: {reset_url}\n\n"
                            "This link expires in one hour and can only be used once. "
                            "If you did not request it, you can ignore this email."
                        ),
                        "Charset": "UTF-8",
                    },
                    "Html": {
                        "Data": (
                            "<h1>Reset your password</h1>"
                            "<p>We received a request to reset your Run My Pool password.</p>"
                            f'<p><a href="{safe_url}">Reset your password</a></p>'
                            "<p>This link expires in one hour and can only be used once.</p>"
                            "<p>If you did not request it, you can ignore this email.</p>"
                        ),
                        "Charset": "UTF-8",
                    },
                },
            }
        },
    )
    message_id = response["MessageId"]
    log_event(logger, logging.INFO, "password_reset_email_queued", message_id=message_id)
    return message_id
