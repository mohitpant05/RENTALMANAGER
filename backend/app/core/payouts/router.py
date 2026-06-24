import uuid

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import require_permission
from app.core.auth.models import User
from app.core.payouts.schemas import (
    OwnerBalance,
    PayoutCreate,
    PayoutItemResponse,
    PayoutResponse,
)
from app.core.payouts.service import (
    create_payout,
    get_owner_balances,
    get_payout,
    get_payout_items,
    get_unsettled_bookings,
    list_payouts,
    settle_payout,
)
from app.database import get_db
from app.domains.bookings.schemas import BookingResponse

router = APIRouter(prefix="/api/payouts", tags=["payouts"])


@router.get("/balances", response_model=list[OwnerBalance])
async def owner_balances(
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("settings:*:manage")),
):
    return await get_owner_balances(session)


@router.get("/owner/{owner_id}/bookings", response_model=list[BookingResponse])
async def unsettled_bookings(
    owner_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("settings:*:manage")),
):
    return await get_unsettled_bookings(session, owner_id)


@router.post("", response_model=PayoutResponse, status_code=201)
async def create_new_payout(
    data: PayoutCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("settings:*:manage")),
):
    payout = await create_payout(
        session, data.owner_id, data.period_start, data.period_end,
        admin_id=user.id, currency=data.currency, notes=data.notes,
    )
    items = await get_payout_items(session, payout.id)
    resp = PayoutResponse.model_validate(payout)
    resp.items = [PayoutItemResponse.model_validate(i) for i in items]
    return resp


@router.post("/{payout_id}/settle", response_model=PayoutResponse)
async def settle(
    payout_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("settings:*:manage")),
):
    payout = await settle_payout(session, payout_id, user.id)
    items = await get_payout_items(session, payout.id)
    resp = PayoutResponse.model_validate(payout)
    resp.items = [PayoutItemResponse.model_validate(i) for i in items]
    return resp


@router.get("", response_model=list[PayoutResponse])
async def list_all_payouts(
    owner_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("settings:*:manage")),
):
    return await list_payouts(session, owner_id, status, offset, limit)


@router.get("/{payout_id}", response_model=PayoutResponse)
async def get_one_payout(
    payout_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("settings:*:manage")),
):
    payout = await get_payout(session, payout_id)
    items = await get_payout_items(session, payout_id)
    resp = PayoutResponse.model_validate(payout)
    resp.items = [PayoutItemResponse.model_validate(i) for i in items]
    return resp
