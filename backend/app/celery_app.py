import asyncio
import logging

from celery import Celery

from app.config import get_settings
from app.core.email.factory import get_email_provider, get_email_provider_from_config

logger = logging.getLogger(__name__)

settings = get_settings()

celery = Celery(
    "rentmanager",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_task_session_factory():
    """Create a fresh engine + session factory per task invocation.

    Celery prefork workers inherit the parent's connection pool after fork.
    Two workers sharing one asyncpg pool causes 'another operation is in
    progress'. A fresh engine per task avoids this entirely.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlmodel.ext.asyncio.session import AsyncSession

    task_engine = create_async_engine(
        settings.database_url,
        pool_size=5,
        max_overflow=2,
    )
    factory = async_sessionmaker(
        task_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return task_engine, factory


async def _run_for_all_tenants(task_fn):
    from sqlalchemy import text as sa_text
    from sqlmodel import select

    from app.core.tenancy.context import validate_schema_name
    from app.core.tenancy.models import Tenant

    task_engine, factory = _make_task_session_factory()
    try:
        async with factory() as session:
            result = await session.exec(
                select(Tenant).where(Tenant.is_active.is_(True))
            )
            tenants = list(result.all())

        total = 0
        for tenant in tenants:
            validate_schema_name(tenant.schema_name)
            async with factory() as session:
                await session.execute(
                    sa_text(
                        f"SET search_path TO {tenant.schema_name}, public"
                    )
                )
                count = await task_fn(session)
                total += count
                await session.execute(sa_text("SET search_path TO public"))
        return total
    finally:
        await task_engine.dispose()


@celery.task(name="bookings.cleanup_expired_holds")
def task_cleanup_expired_holds():
    from app.domains.bookings.tasks import cleanup_expired_holds
    return _run_async(_run_for_all_tenants(cleanup_expired_holds))


@celery.task(name="bookings.activate_confirmed")
def task_activate_confirmed():
    from app.domains.bookings.tasks import activate_confirmed_bookings
    return _run_async(_run_for_all_tenants(activate_confirmed_bookings))


@celery.task(name="bookings.complete_active")
def task_complete_active():
    from app.domains.bookings.tasks import complete_active_bookings
    return _run_async(_run_for_all_tenants(complete_active_bookings))


@celery.task(name="search.full_reindex")
def task_full_reindex():
    async def _do_reindex():
        from sqlalchemy import text as sa_text
        from sqlmodel import select

        from app.core.search.tasks import full_reindex
        from app.core.tenancy.context import validate_schema_name
        from app.core.tenancy.models import Tenant

        task_engine, factory = _make_task_session_factory()
        try:
            async with factory() as session:
                result = await session.exec(
                    select(Tenant).where(Tenant.is_active.is_(True))
                )
                tenants = list(result.all())

            total = 0
            for tenant in tenants:
                validate_schema_name(tenant.schema_name)
                async with factory() as session:
                    await session.execute(
                        sa_text(
                            f"SET search_path TO {tenant.schema_name}, public"
                        )
                    )
                    count = await full_reindex(session, str(tenant.id))
                    total += count
                    await session.execute(
                        sa_text("SET search_path TO public")
                    )
            return total
        finally:
            await task_engine.dispose()

    return _run_async(_do_reindex())


@celery.task(name="currency.refresh_rates")
def task_refresh_currency_rates():
    async def _do_refresh():
        from app.core.currency.service import refresh_rates_cache
        return await refresh_rates_cache()

    return _run_async(_do_refresh())


@celery.task(name="email.send", bind=True, max_retries=3, queue="email")
def task_send_email(self, to: str, subject: str, body: str, smtp_config: dict | None = None):
    provider = None
    if smtp_config:
        provider = get_email_provider_from_config(smtp_config)
    if provider is None:
        provider = get_email_provider()
    if provider is None:
        logger.warning("No email provider configured, skipping email to %s", to)
        return None
    try:
        return provider.send(to, subject, body)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


celery.conf.beat_schedule = {
    "cleanup-expired-holds": {
        "task": "bookings.cleanup_expired_holds",
        "schedule": 60.0,
    },
    "activate-confirmed-bookings": {
        "task": "bookings.activate_confirmed",
        "schedule": 60.0,
    },
    "complete-active-bookings": {
        "task": "bookings.complete_active",
        "schedule": 60.0,
    },
    "search-full-reindex": {
        "task": "search.full_reindex",
        "schedule": 86400.0,
    },
    "refresh-currency-rates": {
        "task": "currency.refresh_rates",
        "schedule": 43200.0,  # 12 hours
    },
}
