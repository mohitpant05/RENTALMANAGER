from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import require_permission
from app.core.auth.models import User
from app.core.payments.refunds_schemas import (
    BulkRefundSettleRequest,
    BulkRefundSettleResponse,
    RefundPendingItem,
)
from app.core.payments.refunds_service import (
    bulk_settle_refunds,
    list_refund_pending,
    list_settled_refunds,
)
from app.database import get_db

router = APIRouter(prefix="/api/admin/refunds", tags=["admin-refunds"])


@router.get("/pending", response_model=list[RefundPendingItem])
async def get_refund_pending(
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("settings:*:manage")),
):
    return await list_refund_pending(session)


@router.post("/settle", response_model=BulkRefundSettleResponse)
async def settle_refunds(
    data: BulkRefundSettleRequest,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("settings:*:manage")),
):
    results = await bulk_settle_refunds(session, data.items)
    settled = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    return BulkRefundSettleResponse(results=results, settled_count=settled, failed_count=failed)


@router.get("/settled", response_model=list[RefundPendingItem])
async def get_settled_refunds(
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("settings:*:manage")),
):
    return await list_settled_refunds(session)
