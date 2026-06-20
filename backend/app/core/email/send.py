from app.celery_app import task_send_email
from app.core.tenancy.context import get_current_tenant


def _extract_smtp_config() -> dict | None:
    ctx = get_current_tenant()
    if ctx is None:
        return None
    config = ctx.tenant.config or {}
    if not config.get("smtp_provider"):
        return None
    return {
        "smtp_provider": config.get("smtp_provider"),
        "smtp_host": config.get("smtp_host"),
        "smtp_port": config.get("smtp_port"),
        "smtp_user": config.get("smtp_user"),
        "smtp_password": config.get("smtp_password"),
        "email_from": config.get("email_from"),
        "mandrill_api_key": config.get("mandrill_api_key"),
    }


def send_email(to: str, subject: str, body: str) -> None:
    smtp_config = _extract_smtp_config()
    task_send_email.delay(to, subject, body, smtp_config)
