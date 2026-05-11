import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import get_current_user, require_permission
from app.core.auth.models import User
from app.core.payments.schemas import MarkPaidRequest, PaymentResponse, RefundRequest
from app.core.payments.service import (
    create_payment_for_booking,
    get_payment_for_booking,
    mark_payment_paid,
    refund_payment,
)
from app.database import get_db

router = APIRouter(prefix="/api/payments", tags=["payments"])


def _require_admin():
    return require_permission("*:*:*")


@router.post("/booking/{booking_id}", response_model=PaymentResponse, status_code=201)
async def create_payment(
    booking_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await create_payment_for_booking(session, booking_id)


@router.get("/booking/{booking_id}", response_model=PaymentResponse | None)
async def get_payment(
    booking_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payment = await get_payment_for_booking(session, booking_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="No payment found for this booking")
    return payment


@router.post("/{payment_id}/mark-paid", response_model=PaymentResponse)
async def mark_paid(
    payment_id: uuid.UUID,
    data: MarkPaidRequest | None = None,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_admin()),
):
    notes = data.notes if data else None
    return await mark_payment_paid(session, payment_id, notes=notes)


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
async def process_refund(
    payment_id: uuid.UUID,
    data: RefundRequest | None = None,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_admin()),
):
    amount = data.amount if data else None
    reason = data.reason if data else None
    return await refund_payment(session, payment_id, amount, reason=reason)
