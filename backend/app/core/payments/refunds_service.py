import logging
import uuid
from datetime import UTC, datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.models import User
from app.core.payments.models import Payment
from app.core.payments.provider import get_provider
from app.core.payments.refunds_schemas import (
    RefundPendingItem,
    RefundSettleRequest,
    RefundSettleResult,
)
from app.core.tenancy.context import get_current_tenant
from app.domains.bookings.models import Booking
from app.domains.resources.models import Resource

_logger = logging.getLogger("app.payments.refunds")


async def list_refund_pending(session: AsyncSession) -> list[RefundPendingItem]:
    stmt = (
        select(Booking, Payment, User, Resource)
        .join(Payment, Payment.booking_id == Booking.id)
        .join(User, User.id == Booking.user_id)
        .join(Resource, Resource.id == Booking.resource_id)
        .where(
            Booking.status == "cancelled",
            Booking.refund_percent.isnot(None),
            Booking.refund_percent > 0,
            Payment.status == "paid",
            Payment.refund_amount.is_(None),
        )
        .order_by(Booking.cancelled_at.desc())
    )
    results = await session.exec(stmt)
    items = []
    for booking, payment, user, resource in results.all():
        refund_pct = booking.refund_percent or 0
        items.append(RefundPendingItem(
            booking_id=booking.id,
            payment_id=payment.id,
            customer_name=user.full_name or user.email,
            customer_email=user.email,
            resource_name=resource.name,
            cancelled_at=booking.cancelled_at,
            start_time=booking.start_time,
            booking_amount=payment.amount,
            currency=payment.currency,
            refund_percent=refund_pct,
            refund_amount=round(payment.amount * refund_pct / 100, 2),
            payment_status=payment.status,
            provider=payment.provider,
        ))
    return items


async def list_settled_refunds(session: AsyncSession) -> list[RefundPendingItem]:
    stmt = (
        select(Booking, Payment, User, Resource)
        .join(Payment, Payment.booking_id == Booking.id)
        .join(User, User.id == Booking.user_id)
        .join(Resource, Resource.id == Booking.resource_id)
        .where(
            Booking.status == "cancelled",
            Payment.status.in_(["refunded", "partially_refunded"]),
            Payment.refund_amount.isnot(None),
        )
        .order_by(Payment.refunded_at.desc())
    )
    results = await session.exec(stmt)
    items = []
    for booking, payment, user, resource in results.all():
        items.append(RefundPendingItem(
            booking_id=booking.id,
            payment_id=payment.id,
            customer_name=user.full_name or user.email,
            customer_email=user.email,
            resource_name=resource.name,
            cancelled_at=booking.cancelled_at,
            start_time=booking.start_time,
            booking_amount=payment.amount,
            currency=payment.currency,
            refund_percent=booking.refund_percent or 0,
            refund_amount=payment.refund_amount or 0,
            payment_status=payment.status,
            provider=payment.provider,
        ))
    return items


async def settle_refund(
    session: AsyncSession,
    payment_id: uuid.UUID,
    override_percent: float | None = None,
    commit: bool = True,
) -> RefundSettleResult:
    result = await session.exec(
        select(Payment)
        .where(Payment.id == payment_id)
        .with_for_update()
    )
    payment = result.first()
    if payment is None:
        return RefundSettleResult(payment_id=payment_id, success=False, error="Payment not found")

    if payment.status != "paid":
        return RefundSettleResult(
            payment_id=payment_id, success=False,
            error=f"Payment status is '{payment.status}', expected 'paid'",
        )

    booking_result = await session.exec(
        select(Booking).where(Booking.id == payment.booking_id)
    )
    booking = booking_result.first()
    if booking is None:
        return RefundSettleResult(payment_id=payment_id, success=False, error="Booking not found")

    refund_pct = override_percent if override_percent is not None else (booking.refund_percent or 0)
    if refund_pct <= 0:
        return RefundSettleResult(payment_id=payment_id, success=False, error="Refund percent is 0")

    refund_amount = round(payment.amount * refund_pct / 100, 2)

    ctx = get_current_tenant()
    config = (ctx.tenant.config or {}) if ctx else {}

    provider_name = payment.provider
    provider = get_provider(provider_name, config)

    if payment.provider_ref and provider_name != "manual":
        refund_result = await provider.refund_payment(payment.provider_ref, refund_amount)
        if not refund_result.success:
            return RefundSettleResult(
                payment_id=payment_id, success=False,
                error=f"Provider refund failed: {refund_result.error}",
            )

    payment.refund_amount = refund_amount
    payment.refunded_at = datetime.now(UTC)
    payment.status = "refunded" if refund_pct >= 100 else "partially_refunded"
    payment.updated_at = datetime.now(UTC)
    session.add(payment)

    if commit:
        try:
            await session.commit()
            await session.refresh(payment)
        except Exception:
            await session.rollback()
            _logger.critical(
                "Refund committed at provider but DB commit failed for payment %s — "
                "manual reconciliation required",
                payment_id,
            )
            return RefundSettleResult(
                payment_id=payment_id, success=False,
                error="Refund was sent to provider but DB update failed — contact support",
            )

    return RefundSettleResult(payment_id=payment_id, success=True, refund_amount=refund_amount)


async def bulk_settle_refunds(
    session: AsyncSession,
    items: list[RefundSettleRequest],
) -> list[RefundSettleResult]:
    results: list[RefundSettleResult] = []
    for item in items:
        result = await settle_refund(session, item.payment_id, item.override_percent, commit=False)
        results.append(result)

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        _logger.critical(
            "Bulk refund commit failed after %d provider calls — manual reconciliation required",
            sum(1 for r in results if r.success),
        )
        results = [
            RefundSettleResult(
                payment_id=r.payment_id, success=False,
                error="Refund was sent to provider but DB update failed — contact support",
            ) if r.success else r
            for r in results
        ]

    return results
