from unittest.mock import Mock, patch

from email_service import send_password_reset_email


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
