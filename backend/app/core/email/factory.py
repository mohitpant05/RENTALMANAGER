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


def get_email_provider_from_config(config: dict) -> EmailProvider | None:
    provider = config.get("smtp_provider")
    from_addr = config.get("email_from")
    if not provider or not from_addr:
        return None
    if provider == "smtp":
        from app.core.email.gmail import GmailSMTPProvider
        host = config.get("smtp_host")
        port = config.get("smtp_port", 587)
        user = config.get("smtp_user")
        password = config.get("smtp_password")
        if not host or not user or not password:
            return None
        return GmailSMTPProvider(
            host=host, port=int(port), user=user, password=password,
            from_addr=from_addr,
        )
    if provider == "mandrill":
        from app.core.email.mandrill import MandrillProvider
        api_key = config.get("mandrill_api_key")
        if not api_key:
            return None
        return MandrillProvider(api_key=api_key, from_addr=from_addr)
    return None
