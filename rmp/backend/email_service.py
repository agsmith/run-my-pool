"""Transactional email delivery through Amazon SES."""

import html
import logging
import os
from urllib.parse import urlencode

import boto3

from app_logging import log_event


logger = logging.getLogger("runmypool.email")


def send_email_verification_email(recipient: str, token: str) -> str:
    """Send a 24-hour verification link without logging the bearer token."""
    region = os.getenv("AWS_SES_REGION", "us-east-1")
    frontend_url = os.getenv("FRONTEND_URL", "https://runmypool.net").rstrip("/")
    sender = os.getenv("EMAIL_FROM", "Run My Pool Accounts <accounts@runmypool.net>")
    reply_to = os.getenv("EMAIL_REPLY_TO", "support@runmypool.net")
    verification_url = f"{frontend_url}/verify-email?{urlencode({'token': token})}"
    safe_url = html.escape(verification_url, quote=True)

    response = boto3.client("sesv2", region_name=region).send_email(
        FromEmailAddress=sender,
        Destination={"ToAddresses": [recipient]},
        ReplyToAddresses=[reply_to],
        Content={"Simple": {
            "Subject": {"Data": "Verify your Run My Pool email", "Charset": "UTF-8"},
            "Body": {
                "Text": {"Data": (
                    "Welcome to Run My Pool. Verify your email to activate your account.\n\n"
                    f"Verify your email: {verification_url}\n\n"
                    "This link expires in 24 hours and can only be used once. "
                    "If you did not create this account, you can ignore this email."
                ), "Charset": "UTF-8"},
                "Html": {"Data": (
                    "<h1>Verify your email</h1>"
                    "<p>Welcome to Run My Pool. Verify your email to activate your account.</p>"
                    f'<p><a href="{safe_url}">Verify your email</a></p>'
                    "<p>This link expires in 24 hours and can only be used once.</p>"
                    "<p>If you did not create this account, you can ignore this email.</p>"
                ), "Charset": "UTF-8"},
            },
        }},
    )
    message_id = response["MessageId"]
    log_event(logger, logging.INFO, "email_verification_queued", message_id=message_id)
    return message_id


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


def send_pool_invitation_email(recipient: str, pool_id: str, pool_name: str, is_private: bool) -> str:
    """Send a pool invitation without including a private pool join code."""
    region = os.getenv("AWS_SES_REGION", "us-east-1")
    frontend_url = os.getenv("FRONTEND_URL", "https://runmypool.net").rstrip("/")
    sender = os.getenv("EMAIL_FROM", "Run My Pool Accounts <accounts@runmypool.net>")
    reply_to = os.getenv("EMAIL_REPLY_TO", "support@runmypool.net")
    next_path = f"/leagues?{urlencode({'invite': pool_id})}"
    invite_url = f"{frontend_url}/login?{urlencode({'next': next_path})}"
    safe_url = html.escape(invite_url, quote=True)
    plain_name = " ".join(pool_name.split())
    safe_name = html.escape(plain_name, quote=True)
    access_note = (
        "This is a private pool. Ask the commissioner for the join code separately."
        if is_private
        else "This is a public pool and can be joined from the invitation page."
    )

    response = boto3.client("sesv2", region_name=region).send_email(
        FromEmailAddress=sender,
        Destination={"ToAddresses": [recipient]},
        ReplyToAddresses=[reply_to],
        Content={
            "Simple": {
                "Subject": {"Data": f"You're invited to {plain_name} on Run My Pool", "Charset": "UTF-8"},
                "Body": {
                    "Text": {
                        "Data": f"You're invited to join {plain_name}.\n\nOpen invitation: {invite_url}\n\n{access_note}",
                        "Charset": "UTF-8",
                    },
                    "Html": {
                        "Data": (
                            f"<h1>You're invited to {safe_name}</h1>"
                            "<p>A commissioner invited you to join their pool on Run My Pool.</p>"
                            f'<p><a href="{safe_url}">Open pool invitation</a></p>'
                            f"<p>{html.escape(access_note)}</p>"
                        ),
                        "Charset": "UTF-8",
                    },
                },
            }
        },
    )
    message_id = response["MessageId"]
    log_event(logger, logging.INFO, "pool_invitation_email_queued", message_id=message_id, pool_id=pool_id)
    return message_id
