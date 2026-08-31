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


def send_email_verification_reminder(recipient: str, token: str) -> str:
    """Send the one-time follow-up issued after an account remains unverified."""
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
            "Subject": {"Data": "Reminder: verify your Run My Pool email", "Charset": "UTF-8"},
            "Body": {
                "Text": {"Data": (
                    "Your Run My Pool account is still waiting for email verification.\n\n"
                    f"Verify your email: {verification_url}\n\n"
                    "This new link expires in 24 hours and can only be used once. "
                    "If you did not create this account, you can ignore this email."
                ), "Charset": "UTF-8"},
                "Html": {"Data": (
                    "<h1>Your account is waiting</h1>"
                    "<p>Verify your email to finish activating your Run My Pool account.</p>"
                    f'<p><a href="{safe_url}">Verify your email</a></p>'
                    "<p>This new link expires in 24 hours and can only be used once.</p>"
                    "<p>If you did not create this account, you can ignore this email.</p>"
                ), "Charset": "UTF-8"},
            },
        }},
    )
    message_id = response["MessageId"]
    log_event(logger, logging.INFO, "email_verification_reminder_queued", message_id=message_id)
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


def send_pool_owner_report(recipient: str, report: dict) -> str:
    """Send a concise, branded weekly pool-health report."""
    region = os.getenv("AWS_SES_REGION", "us-east-1")
    frontend_url = os.getenv("FRONTEND_URL", "https://runmypool.net").rstrip("/")
    sender = os.getenv("EMAIL_FROM", "Run My Pool Reports <no-reply@runmypool.net>")
    reply_to = os.getenv("EMAIL_REPLY_TO", "support@runmypool.net")
    pool_name = " ".join(report["pool_name"].split())
    safe_name = html.escape(pool_name)
    report_url = f"{frontend_url}/admin/league/{report['pool_id']}"
    completion = f"{report['weekly_entries_with_picks']}/{report['weekly_eligible_entries']}"
    popular_text = ", ".join(f"{item['team']} ({item['picks']})" for item in report["popular_locked_picks"]) or "Available after picks lock"
    text_body = (
        f"{pool_name} — Week {report['week']} pool report\n\n"
        f"Members engaged: {report['engaged_members']}/{report['members']}\n"
        f"Entries remaining: {report['remaining_entries']}/{report['total_entries']}\n"
        f"Weekly entry completion: {completion}\n"
        f"Week results: {report['weekly_wins']} wins, {report['weekly_losses']} losses\n"
        f"Season picks: {report['season_picks']}\nForum messages: {report['forum_messages']}\n"
        f"Popular locked picks: {popular_text}\n\nManage pool: {report_url}\n"
        "You are receiving this because you enabled weekly owner reports. You can opt out in Pool Management."
    )
    html_body = (
        '<div style="background:#071113;color:#e8efed;padding:28px;font-family:Arial,sans-serif">'
        '<div style="color:#d7ff3f;font-size:12px;font-weight:700;letter-spacing:2px">WEEKLY POOL REPORT</div>'
        f'<h1 style="margin:8px 0">{safe_name} · Week {report["week"]}</h1>'
        f'<p><strong>{report["engaged_members"]}/{report["members"]}</strong> members engaged &nbsp; '
        f'<strong>{report["remaining_entries"]}/{report["total_entries"]}</strong> entries remaining</p>'
        f'<p><strong>{completion}</strong> eligible entries picked this week &nbsp; '
        f'<strong>{report["weekly_wins"]}</strong> wins / <strong>{report["weekly_losses"]}</strong> losses</p>'
        f'<p>{report["season_picks"]} season picks · {report["forum_messages"]} forum messages</p>'
        f'<p><strong>Popular locked picks:</strong> {html.escape(popular_text)}</p>'
        f'<p><a href="{html.escape(report_url, quote=True)}" style="display:inline-block;background:#d7ff3f;color:#071113;padding:12px 18px;text-decoration:none;font-weight:700">Open commissioner dashboard</a></p>'
        '<p style="color:#9dafb2;font-size:12px">You enabled weekly owner reports. Opt out any time in Pool Management.</p></div>'
    )
    response = boto3.client("sesv2", region_name=region).send_email(
        FromEmailAddress=sender,
        Destination={"ToAddresses": [recipient]},
        ReplyToAddresses=[reply_to],
        Content={"Simple": {
            "Subject": {"Data": f"{pool_name}: Week {report['week']} pool report", "Charset": "UTF-8"},
            "Body": {"Text": {"Data": text_body, "Charset": "UTF-8"}, "Html": {"Data": html_body, "Charset": "UTF-8"}},
        }},
    )
    message_id = response["MessageId"]
    log_event(logger, logging.INFO, "owner_pool_report_queued", message_id=message_id, pool_id=report["pool_id"])
    return message_id


def send_member_weekly_recap(recipient: str, recap: dict) -> str:
    """Send a completed-week recap containing only the recipient's entry details."""
    region = os.getenv("AWS_SES_REGION", "us-east-1")
    frontend_url = os.getenv("FRONTEND_URL", "https://runmypool.net").rstrip("/")
    sender = os.getenv("EMAIL_FROM", "Run My Pool Accounts <accounts@runmypool.net>")
    reply_to = os.getenv("EMAIL_REPLY_TO", "support@runmypool.net")
    pool_name = " ".join(recap["pool_name"].split())
    safe_name = html.escape(pool_name)
    pool_url = f"{frontend_url}/pool/{recap['pool_id']}"
    preference_url = f"{pool_url}#weekly-recap"
    entry_lines = [
        f"{item['entry_name']}: {item['pick'] or 'No pick'} — {item['result'].title()}"
        for item in recap["entries"]
    ] or ["No entries"]
    text_body = (
        f"{pool_name} — Week {recap['week']} recap\n\n"
        + "\n".join(entry_lines)
        + f"\n\nYour week: {recap['wins']} correct, {recap['losses']} incorrect, {recap['pending']} pending/no result"
        + f"\nYour entries remaining: {recap['remaining_entries']}/{recap['total_entries']}"
        + f"\nPool entries remaining: {recap['pool_remaining_entries']}/{recap['pool_total_entries']}"
        + f"\n\nOpen pool: {pool_url}\nManage or turn off weekly recaps: {preference_url}"
    )
    rows = "".join(
        "<tr>"
        f"<td style='padding:8px;border-bottom:1px solid #314449'>{html.escape(item['entry_name'])}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #314449'>{html.escape(item['pick'] or 'No pick')}</td>"
        f"<td style='padding:8px;border-bottom:1px solid #314449'>{html.escape(item['result'].title())}</td>"
        "</tr>"
        for item in recap["entries"]
    ) or "<tr><td colspan='3' style='padding:8px'>No entries</td></tr>"
    html_body = (
        '<div style="background:#071113;color:#e8efed;padding:28px;font-family:Arial,sans-serif">'
        '<div style="color:#d7ff3f;font-size:12px;font-weight:700;letter-spacing:2px">YOUR WEEKLY RECAP</div>'
        f'<h1 style="margin:8px 0">{safe_name} · Week {recap["week"]}</h1>'
        '<table style="width:100%;border-collapse:collapse"><thead><tr><th align="left">Entry</th><th align="left">Pick</th><th align="left">Result</th></tr></thead>'
        f"<tbody>{rows}</tbody></table>"
        f'<p><strong>{recap["wins"]}</strong> correct · <strong>{recap["losses"]}</strong> incorrect · <strong>{recap["pending"]}</strong> pending/no result</p>'
        f'<p><strong>{recap["remaining_entries"]}/{recap["total_entries"]}</strong> of your entries remain · '
        f'<strong>{recap["pool_remaining_entries"]}/{recap["pool_total_entries"]}</strong> remain pool-wide</p>'
        f'<p><a href="{html.escape(pool_url, quote=True)}" style="display:inline-block;background:#d7ff3f;color:#071113;padding:12px 18px;text-decoration:none;font-weight:700">Open your pool</a></p>'
        f'<p style="color:#9dafb2;font-size:12px">You opted into weekly member recaps. <a style="color:#9dafb2" href="{html.escape(preference_url, quote=True)}">Manage or turn off recaps</a>.</p></div>'
    )
    response = boto3.client("sesv2", region_name=region).send_email(
        FromEmailAddress=sender,
        Destination={"ToAddresses": [recipient]},
        ReplyToAddresses=[reply_to],
        Content={"Simple": {
            "Subject": {"Data": f"{pool_name}: your Week {recap['week']} recap", "Charset": "UTF-8"},
            "Body": {"Text": {"Data": text_body, "Charset": "UTF-8"}, "Html": {"Data": html_body, "Charset": "UTF-8"}},
        }},
    )
    message_id = response["MessageId"]
    log_event(logger, logging.INFO, "member_weekly_recap_queued", message_id=message_id, pool_id=recap["pool_id"], week=recap["week"])
    return message_id
