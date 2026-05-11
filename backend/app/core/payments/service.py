import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.payments.models import Payment
from app.core.payments.provider import get_provider
from app.core.tenancy.context import get_current_tenant
from app.domains.bookings.models import Booking


def _get_payment_config() -> tuple[str, dict]:
    ctx = get_current_tenant()
    if ctx is None:
        raise HTTPException(status_code=400, detail="No tenant context")
    config = ctx.tenant.config or {}
    provider_name = config.get("payment_provider", "manual")
    return provider_name, config


async def create_payment_for_booking(
    session: AsyncSession,
    booking_id: uuid.UUID,
) -> Payment:
    result = await session.exec(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    existing = await session.exec(
        select(Payment).where(Payment.booking_id == booking_id)
    )
    if existing.first() is not None:
        raise HTTPException(status_code=409, detail="Payment already exists for this booking")

    provider_name, config = _get_payment_config()
    provider = get_provider(provider_name, config)

    result_data = await provider.create_payment(
        amount=booking.customer_total,
        currency=booking.currency,
        metadata={"booking_id": str(booking_id)},
    )

    payment = Payment(
        booking_id=booking_id,
        amount=booking.customer_total,
        currency=booking.currency,
        provider=provider_name,
        status="pending" if result_data.success else "failed",
        provider_ref=result_data.provider_ref,
        provider_data=result_data.provider_data,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def get_payment_for_booking(
    session: AsyncSession,
    booking_id: uuid.UUID,
) -> Payment | None:
    result = await session.exec(
        select(Payment).where(Payment.booking_id == booking_id)
    )
    return result.first()


async def mark_payment_paid(
    session: AsyncSession,
    payment_id: uuid.UUID,
    notes: str | None = None,
) -> Payment:
    result = await session.exec(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.first()
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status != "pending":
        raise HTTPException(
            status_code=409, detail=f"Cannot mark as paid: status is '{payment.status}'"
        )

    payment.status = "paid"
    payment.paid_at = datetime.now(UTC)
    payment.updated_at = datetime.now(UTC)
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def refund_payment(
    session: AsyncSession,
    payment_id: uuid.UUID,
    amount: float | None = None,
    reason: str | None = None,
) -> Payment:
    result = await session.exec(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.first()
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status != "paid":
        raise HTTPException(
            status_code=409, detail=f"Cannot refund: status is '{payment.status}'"
        )

    refund_amount = amount if amount is not None else payment.amount
    if refund_amount > payment.amount:
        raise HTTPException(status_code=400, detail="Refund amount exceeds payment amount")

    provider_name, config = _get_payment_config()
    provider = get_provider(provider_name, config)

    if payment.provider_ref:
        refund_result = await provider.refund_payment(payment.provider_ref, refund_amount)
        if not refund_result.success:
            raise HTTPException(
                status_code=502, detail=f"Provider refund failed: {refund_result.error}"
            )

    payment.refund_amount = refund_amount
    payment.refunded_at = datetime.now(UTC)
    payment.status = "refunded" if refund_amount >= payment.amount else "partially_refunded"
    payment.updated_at = datetime.now(UTC)
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment
