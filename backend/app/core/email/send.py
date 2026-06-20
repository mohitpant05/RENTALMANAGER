import logging

from app.celery_app import task_send_email
from app.core.tenancy.context import get_current_tenant

logger = logging.getLogger(__name__)


def _extract_smtp_config() -> dict | None:
    ctx = get_current_tenant()
    if ctx is None:
        logger.debug("No tenant context — skipping tenant SMTP config")
        return None
    config = ctx.tenant.config or {}
    if not config.get("smtp_provider"):
        logger.debug("Tenant %s has no smtp_provider configured", ctx.tenant.slug)
        return None
    logger.info("Using tenant SMTP config (provider=%s) for %s", config["smtp_provider"], ctx.tenant.slug)
    return {
        "smtp_provider": config.get("smtp_provider"),
        "smtp_host": config.get("smtp_host"),
        "smtp_port": config.get("smtp_port"),
        "smtp_user": config.get("smtp_user"),
        "smtp_password": config.get("smtp_password"),
        "email_from": config.get("email_from"),
        "mandrill_api_key": config.get("mandrill_api_key"),
    }


def _get_tenant_id() -> str | None:
    ctx = get_current_tenant()
    if ctx is None:
        return None
    return str(ctx.tenant.id)


def has_email_provider() -> bool:
    from app.core.email.factory import get_email_provider, get_email_provider_from_config

    smtp_config = _extract_smtp_config()
    if smtp_config and get_email_provider_from_config(smtp_config):
        return True
    if get_email_provider():
        return True
    return False


def send_email(to: str, subject: str, body: str) -> bool:
    smtp_config = _extract_smtp_config()
    tenant_id = _get_tenant_id()
    logger.info("Queuing email to=%s subject=%r smtp_config=%s tenant=%s", to, subject, "tenant" if smtp_config else "env/none", tenant_id or "none")
    task_send_email.delay(to, subject, body, smtp_config, tenant_id)
    return True
