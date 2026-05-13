from unittest.mock import MagicMock, patch


def test_factory_returns_none_when_no_config():
    from app.core.email.factory import get_email_provider
    with patch("app.core.email.factory.get_settings") as mock:
        mock.return_value = MagicMock(email_provider="", email_from="")
        provider = get_email_provider()
        assert provider is None


def test_factory_returns_gmail_provider():
    from app.core.email.factory import get_email_provider
    from app.core.email.gmail import GmailSMTPProvider
    with patch("app.core.email.factory.get_settings") as mock:
        mock.return_value = MagicMock(
            email_provider="gmail", email_from="test@gmail.com",
            smtp_host="smtp.gmail.com", smtp_port=587,
            smtp_user="user", smtp_password="pass",
        )
        provider = get_email_provider()
        assert isinstance(provider, GmailSMTPProvider)


def test_factory_returns_mandrill_provider():
    from app.core.email.factory import get_email_provider
    from app.core.email.mandrill import MandrillProvider
    with patch("app.core.email.factory.get_settings") as mock:
        mock.return_value = MagicMock(
            email_provider="mandrill", email_from="test@example.com",
            mandrill_api_key="test-key",
        )
        provider = get_email_provider()
        assert isinstance(provider, MandrillProvider)


def test_gmail_provider_sends_email():
    from app.core.email.gmail import GmailSMTPProvider
    provider = GmailSMTPProvider(
        host="smtp.gmail.com", port=587,
        user="user@gmail.com", password="pass",
        from_addr="noreply@example.com",
    )
    with patch("app.core.email.gmail.smtplib.SMTP") as mock_smtp:
        instance = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        result = provider.send("to@test.com", "Subject", "Body")
        assert result is True
        instance.starttls.assert_called_once()
        instance.login.assert_called_once_with("user@gmail.com", "pass")
        instance.sendmail.assert_called_once()


def test_mandrill_provider_sends_email():
    from app.core.email.mandrill import MandrillProvider
    provider = MandrillProvider(api_key="test-key", from_addr="noreply@example.com")
    with patch("app.core.email.mandrill.httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        result = provider.send("to@test.com", "Subject", "Body")
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["message"]["to"][0]["email"] == "to@test.com"


def test_send_email_task_skips_when_no_provider():
    from app.celery_app import task_send_email
    with patch("app.celery_app.get_email_provider", return_value=None):
        result = task_send_email("to@test.com", "Subject", "Body")
        assert result is None


def test_send_email_task_calls_provider():
    from app.celery_app import task_send_email
    mock_provider = MagicMock()
    mock_provider.send.return_value = True
    with patch("app.celery_app.get_email_provider", return_value=mock_provider):
        task_send_email("to@test.com", "Subject", "Body")
        mock_provider.send.assert_called_once_with("to@test.com", "Subject", "Body")
