import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.notifications.models import Notification


async def notify(
    session: AsyncSession,
    user_id: uuid.UUID,
    event_type: str,
    title: str,
    body: str,
    payload: dict | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        event_type=event_type,
        title=title,
        body=body,
        payload=payload,
    )
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    return notification


async def notify_many(
    session: AsyncSession,
    user_ids: list[uuid.UUID],
    event_type: str,
    title: str,
    body: str,
    payload: dict | None = None,
) -> int:
    notifications = [
        Notification(
            user_id=uid,
            event_type=event_type,
            title=title,
            body=body,
            payload=payload,
        )
        for uid in user_ids
    ]
    session.add_all(notifications)
    await session.commit()
    return len(notifications)


async def list_notifications(
    session: AsyncSession,
    user_id: uuid.UUID,
    unread_only: bool = False,
    offset: int = 0,
    limit: int = 20,
) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.offset(offset).limit(limit).order_by(Notification.created_at.desc())
    result = await session.exec(stmt)
    return list(result.all())


async def get_unread_count(session: AsyncSession, user_id: uuid.UUID) -> int:
    result = await session.exec(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    )
    return result.first() or 0


async def mark_read(
    session: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID
) -> Notification:
    result = await session.exec(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.first()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your notification")
    notification.is_read = True
    notification.read_at = datetime.now(UTC)
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    return notification


async def mark_all_read(session: AsyncSession, user_id: uuid.UUID) -> int:
    result = await session.exec(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    )
    notifications = list(result.all())
    now = datetime.now(UTC)
    for n in notifications:
        n.is_read = True
        n.read_at = now
        session.add(n)
    await session.commit()
    return len(notifications)
