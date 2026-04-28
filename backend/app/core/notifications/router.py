import uuid

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.auth.models import User
from app.core.notifications.schemas import (
    MarkAllReadResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.core.notifications.service import (
    get_unread_count,
    list_notifications,
    mark_all_read,
    mark_read,
)
from app.database import get_db

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/", response_model=list[NotificationResponse])
async def list_my_notifications(
    unread_only: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await list_notifications(
        session, user.id, unread_only=unread_only, offset=offset, limit=limit
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_my_unread_count(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    count = await get_unread_count(session, user.id)
    return UnreadCountResponse(count=count)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await mark_read(session, notification_id, user.id)


@router.post("/read-all", response_model=MarkAllReadResponse)
async def mark_all_notifications_read(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    count = await mark_all_read(session, user.id)
    return MarkAllReadResponse(marked=count)
