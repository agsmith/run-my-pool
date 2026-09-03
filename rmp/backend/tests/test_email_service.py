from unittest.mock import Mock, patch

from email_service import (
    send_email_verification_email,
    send_email_verification_reminder,
    send_password_reset_email,
    send_pool_invitation_email,
    send_season_join_reminder,
    send_season_entry_reminder,
    send_weekly_pick_reminder,
    send_member_weekly_recap,
    send_pool_owner_report,
)


@patch("email_service.boto3.client")
def test_email_verification_uses_ses_and_safe_single_use_link(mock_client, monkeypatch):
    ses = Mock()
    ses.send_email.return_value = {"MessageId": "verify-123"}
    mock_client.return_value = ses
    monkeypatch.setenv("FRONTEND_URL", "https://runmypool.net")

    message_id = send_email_verification_email("member@example.com", "token+with/symbols=")

    assert message_id == "verify-123"
    request = ses.send_email.call_args.kwargs
    assert request["Destination"] == {"ToAddresses": ["member@example.com"]}
    text = request["Content"]["Simple"]["Body"]["Text"]["Data"]
    assert "verify-email?token=token%2Bwith%2Fsymbols%3D" in text
    assert "expires in 24 hours" in text


@patch("email_service.boto3.client")
def test_email_verification_reminder_uses_fresh_safe_link(mock_client, monkeypatch):
    ses = Mock()
    ses.send_email.return_value = {"MessageId": "reminder-123"}
    mock_client.return_value = ses
    monkeypatch.setenv("FRONTEND_URL", "https://runmypool.net")

    message_id = send_email_verification_reminder(
        "waiting@example.com", "fresh+token="
    )

    assert message_id == "reminder-123"
    request = ses.send_email.call_args.kwargs
    assert request["Destination"] == {"ToAddresses": ["waiting@example.com"]}
    assert request["Content"]["Simple"]["Subject"]["Data"] == (
        "Reminder: verify your Run My Pool email"
    )
    text = request["Content"]["Simple"]["Body"]["Text"]["Data"]
    assert "verify-email?token=fresh%2Btoken%3D" in text
    assert "expires in 24 hours" in text


@patch("email_service.boto3.client")
def test_season_join_reminder_uses_browse_pools_cta(mock_client, monkeypatch):
    ses = Mock()
    ses.send_email.return_value = {"MessageId": "join-123"}
    mock_client.return_value = ses
    monkeypatch.setenv("FRONTEND_URL", "https://runmypool.net/")

    assert send_season_join_reminder("waiting@example.com", 2026) == "join-123"

    request = ses.send_email.call_args.kwargs
    assert request["Destination"] == {"ToAddresses": ["waiting@example.com"]}
    assert request["ReplyToAddresses"] == ["support@runmypool.net"]
    assert request["Content"]["Simple"]["Subject"]["Data"] == (
        "The 2026 season starts soon — join your pool"
    )
    text = request["Content"]["Simple"]["Body"]["Text"]["Data"]
    html_body = request["Content"]["Simple"]["Body"]["Html"]["Data"]
    assert "https://runmypool.net/leagues" in text
    assert "Browse pools" in html_body
    assert "join code" in text


@patch("email_service.boto3.client")
def test_season_entry_reminder_consolidates_and_escapes_pool_links(mock_client, monkeypatch):
    ses = Mock()
    ses.send_email.return_value = {"MessageId": "entry-reminder-123"}
    mock_client.return_value = ses
    monkeypatch.setenv("FRONTEND_URL", "https://runmypool.net/")

    result = send_season_entry_reminder(
        "member@example.com",
        2026,
        [
            {"id": "pool/one", "name": "Office <script>alert(1)</script>"},
            {"id": "pool-two", "name": "Friends Pick 'Em"},
        ],
    )

    assert result == "entry-reminder-123"
    request = ses.send_email.call_args.kwargs
    assert request["Destination"] == {"ToAddresses": ["member@example.com"]}
    text = request["Content"]["Simple"]["Body"]["Text"]["Data"]
    html_body = request["Content"]["Simple"]["Body"]["Html"]["Data"]
    assert "pool%2Fone/entries/create" in text
    assert "pool-two/entries/create" in text
    assert "<script>" not in html_body
    assert "Office &lt;script&gt;alert(1)&lt;/script&gt;" in html_body
    assert html_body.count("Create entry") == 2


@patch("email_service.boto3.client")
def test_weekly_pick_reminder_escapes_content_and_routes_by_pool_type(mock_client, monkeypatch):
    ses = Mock()
    ses.send_email.return_value = {"MessageId": "weekly-123"}
    mock_client.return_value = ses
    monkeypatch.setenv("FRONTEND_URL", "https://runmypool.net/")

    result = send_weekly_pick_reminder(
        "member@example.com", 2026, 3,
        [
            {"id": "survivor/one", "name": "Office <script>", "pool_type": "survivor", "missing_entries": 2},
            {"id": "pickem-two", "name": "Pick Em", "pool_type": "pickem", "missing_entries": 1},
        ],
    )
    assert result == "weekly-123"
    request = ses.send_email.call_args.kwargs
    text = request["Content"]["Simple"]["Body"]["Text"]["Data"]
    html_body = request["Content"]["Simple"]["Body"]["Html"]["Data"]
    assert "survivor%2Fone/entries" in text
    assert "pickem-two/pickem" in text
    assert "<script>" not in html_body
    assert "Office &lt;script&gt;" in html_body


@patch("email_service.boto3.client")
def test_password_reset_email_uses_ses_and_safe_link(mock_client, monkeypatch):
    ses = Mock()
    ses.send_email.return_value = {"MessageId": "message-123"}
    mock_client.return_value = ses
    monkeypatch.setenv("FRONTEND_URL", "https://runmypool.net")
    monkeypatch.setenv("EMAIL_FROM", "Run My Pool Accounts <accounts@runmypool.net>")
    monkeypatch.setenv("EMAIL_REPLY_TO", "support@runmypool.net")

    message_id = send_password_reset_email("member@example.com", "token+with/symbols=")

    assert message_id == "message-123"
    mock_client.assert_called_once_with("sesv2", region_name="us-east-1")
    request = ses.send_email.call_args.kwargs
    assert request["Destination"] == {"ToAddresses": ["member@example.com"]}
    assert request["ReplyToAddresses"] == ["support@runmypool.net"]
    text = request["Content"]["Simple"]["Body"]["Text"]["Data"]
    assert "token%2Bwith%2Fsymbols%3D" in text
    assert "expires in one hour" in text


@patch("email_service.boto3.client")
def test_pool_invitation_uses_continuation_link_without_private_code(mock_client, monkeypatch):
    ses = Mock()
    ses.send_email.return_value = {"MessageId": "invite-123"}
    mock_client.return_value = ses
    monkeypatch.setenv("FRONTEND_URL", "https://runmypool.net")

    message_id = send_pool_invitation_email(
        "player@example.com", "pool-1", "Office\nSurvivor", True
    )

    assert message_id == "invite-123"
    request = ses.send_email.call_args.kwargs
    assert request["Destination"] == {"ToAddresses": ["player@example.com"]}
    subject = request["Content"]["Simple"]["Subject"]["Data"]
    assert subject == "You're invited to Office Survivor on Run My Pool"
    text = request["Content"]["Simple"]["Body"]["Text"]["Data"]
    assert "https://runmypool.net/join/pool-1" in text
    assert "Ask the commissioner for the join code separately" in text
    assert "huddle" not in text


@patch("email_service.boto3.client")
def test_owner_report_uses_ses_and_escapes_pool_content(mock_client, monkeypatch):
    ses = Mock()
    ses.send_email.return_value = {"MessageId": "report-123"}
    mock_client.return_value = ses
    monkeypatch.setenv("FRONTEND_URL", "https://runmypool.net")

    message_id = send_pool_owner_report("owner@example.com", {
        "pool_id": "pool-1", "pool_name": "Office <script>alert(1)</script>",
        "week": 4, "engaged_members": 8, "members": 10,
        "remaining_entries": 12, "total_entries": 15,
        "weekly_entries_with_picks": 11, "weekly_eligible_entries": 12,
        "weekly_wins": 7, "weekly_losses": 4, "season_picks": 45,
        "forum_messages": 9, "popular_locked_picks": [{"team": "BUF", "picks": 6}],
    })

    assert message_id == "report-123"
    request = ses.send_email.call_args.kwargs
    assert request["Destination"] == {"ToAddresses": ["owner@example.com"]}
    html_body = request["Content"]["Simple"]["Body"]["Html"]["Data"]
    assert "<script>" not in html_body
    assert "Office &lt;script&gt;alert(1)&lt;/script&gt;" in html_body
    assert "BUF (6)" in html_body


@patch("email_service.boto3.client")
def test_member_recap_escapes_names_and_includes_opt_out_path(mock_client, monkeypatch):
    ses = Mock()
    ses.send_email.return_value = {"MessageId": "member-recap-123"}
    mock_client.return_value = ses
    monkeypatch.setenv("FRONTEND_URL", "https://runmypool.net")

    message_id = send_member_weekly_recap("member@example.com", {
        "pool_id": "pool-1", "pool_name": "Office <Pool>", "week": 4,
        "entries": [{"entry_name": "Fast <script>", "pick": "BUF", "result": "win"}],
        "wins": 1, "losses": 0, "pending": 0,
        "remaining_entries": 1, "total_entries": 1,
        "pool_remaining_entries": 12, "pool_total_entries": 15,
    })

    assert message_id == "member-recap-123"
    request = ses.send_email.call_args.kwargs
    assert request["Destination"] == {"ToAddresses": ["member@example.com"]}
    html_body = request["Content"]["Simple"]["Body"]["Html"]["Data"]
    text_body = request["Content"]["Simple"]["Body"]["Text"]["Data"]
    assert "<script>" not in html_body
    assert "Fast &lt;script&gt;" in html_body
    assert "pool/pool-1#weekly-recap" in text_body
