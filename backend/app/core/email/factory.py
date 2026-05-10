from app.config import get_settings
from app.core.email.provider import EmailProvider


def get_email_provider() -> EmailProvider | None:
    settings = get_settings()
    if not settings.email_provider or not settings.email_from:
        return None
    if settings.email_provider == "console":
        from app.core.email.console import ConsoleEmailProvider
        return ConsoleEmailProvider(from_addr=settings.email_from)
    if settings.email_provider == "gmail":
        from app.core.email.gmail import GmailSMTPProvider
        if not settings.smtp_user or not settings.smtp_password:
            return None
        return GmailSMTPProvider(
            host=settings.smtp_host, port=settings.smtp_port,
            user=settings.smtp_user, password=settings.smtp_password,
            from_addr=settings.email_from,
        )
    if settings.email_provider == "mandrill":
        from app.core.email.mandrill import MandrillProvider
        if not settings.mandrill_api_key:
            return None
        return MandrillProvider(api_key=settings.mandrill_api_key, from_addr=settings.email_from)
    return None
