from unittest.mock import Mock, patch

from email_service import send_password_reset_email, send_pool_invitation_email


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
    assert "login?next=%2Fleagues%3Finvite%3Dpool-1" in text
    assert "Ask the commissioner for the join code separately" in text
    assert "huddle" not in text
