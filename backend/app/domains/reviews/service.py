import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.notifications.events import (
    REVIEW_RECEIVED,
    review_received_payload,
)
from app.core.notifications.service import notify as notify_user
from app.core.search.sync import build_document, sync_resource
from app.core.tenancy.context import get_current_tenant
from app.domains.bookings.models import Booking
from app.domains.resources.models import Resource, ResourceType
from app.domains.reviews.models import Review
from app.domains.reviews.schemas import ReviewCreate


async def create_review(
    session: AsyncSession,
    data: ReviewCreate,
    reviewer_id: uuid.UUID,
    direction: str = "customer_to_resource",
) -> Review:
    result = await session.exec(
        select(Booking).where(Booking.id == data.booking_id)
    )
    booking = result.first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status != "completed":
        raise HTTPException(
            status_code=400, detail="Can only review completed bookings"
        )

    if direction == "customer_to_resource" and booking.user_id != reviewer_id:
        raise HTTPException(status_code=403, detail="Not the booking customer")

    if direction == "lister_to_customer":
        result = await session.exec(
            select(Resource).where(Resource.id == booking.resource_id)
        )
        resource = result.first()
        if resource is None or resource.owner_id != reviewer_id:
            raise HTTPException(status_code=403, detail="Not the resource owner")

    result = await session.exec(
        select(Review).where(
            Review.booking_id == data.booking_id,
            Review.reviewer_id == reviewer_id,
            Review.direction == direction,
        )
    )
    if result.first() is not None:
        raise HTTPException(
            status_code=409, detail="Already reviewed this booking"
        )

    target_user_id = None
    if direction == "lister_to_customer":
        target_user_id = booking.user_id

    review = Review(
        booking_id=data.booking_id,
        resource_id=booking.resource_id,
        reviewer_id=reviewer_id,
        target_user_id=target_user_id,
        direction=direction,
        rating=data.rating,
        category_ratings=data.category_ratings,
        title=data.title,
        body=data.body,
    )
    session.add(review)
    await session.commit()
    await session.refresh(review)

    if direction == "customer_to_resource":
        await _update_resource_rating(session, booking.resource_id)

    try:
        result = await session.exec(
            select(Resource).where(Resource.id == booking.resource_id)
        )
        resource = result.first()
        if resource:
            await notify_user(
                session, resource.owner_id, REVIEW_RECEIVED,
                "New Review", f"You received a {review.rating}-star review",
                review_received_payload(str(review.id), resource.name, review.rating),
            )
    except Exception as e:
        print(f"Failed to send review notification: {e}")

    return review


async def list_reviews(
    session: AsyncSession,
    resource_id: uuid.UUID | None = None,
    reviewer_id: uuid.UUID | None = None,
    target_user_id: uuid.UUID | None = None,
    direction: str | None = None,
    status_filter: str = "published",
    offset: int = 0,
    limit: int = 20,
) -> list[Review]:
    stmt = select(Review)
    if resource_id:
        stmt = stmt.where(Review.resource_id == resource_id)
    if reviewer_id:
        stmt = stmt.where(Review.reviewer_id == reviewer_id)
    if target_user_id:
        stmt = stmt.where(Review.target_user_id == target_user_id)
    if direction:
        stmt = stmt.where(Review.direction == direction)
    stmt = stmt.where(Review.status == status_filter)
    stmt = stmt.offset(offset).limit(limit).order_by(Review.created_at.desc())
    result = await session.exec(stmt)
    return list(result.all())


async def get_review(session: AsyncSession, review_id: uuid.UUID) -> Review:
    result = await session.exec(
        select(Review).where(Review.id == review_id)
    )
    review = result.first()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


async def moderate_review(
    session: AsyncSession,
    review_id: uuid.UUID,
    new_status: str,
    reason: str | None = None,
) -> Review:
    review = await get_review(session, review_id)
    old_status = review.status
    review.status = new_status
    review.moderation_reason = reason
    review.updated_at = datetime.now(UTC)
    session.add(review)
    await session.commit()
    await session.refresh(review)

    if review.direction == "customer_to_resource":
        if old_status == "published" and new_status != "published":
            await _update_resource_rating(session, review.resource_id)
        elif old_status != "published" and new_status == "published":
            await _update_resource_rating(session, review.resource_id)

    return review


async def get_resource_rating_summary(
    session: AsyncSession, resource_id: uuid.UUID
) -> dict:
    agg = await session.exec(
        select(
            func.avg(Review.rating).label("avg"),
            func.count(Review.id).label("count"),
        ).where(
            Review.resource_id == resource_id,
            Review.direction == "customer_to_resource",
            Review.status == "published",
        )
    )
    row = agg.first()
    avg_rating = float(row.avg) if row.avg else 0.0
    total_count = row.count or 0

    dist_rows = await session.exec(
        select(Review.rating, func.count(Review.id).label("cnt"))
        .where(
            Review.resource_id == resource_id,
            Review.direction == "customer_to_resource",
            Review.status == "published",
        )
        .group_by(Review.rating)
    )
    distribution = {str(r.rating): r.cnt for r in dist_rows.all()}
    for i in range(1, 6):
        distribution.setdefault(str(i), 0)

    return {"average": round(avg_rating, 2), "count": total_count, "distribution": distribution}


async def _update_resource_rating(
    session: AsyncSession, resource_id: uuid.UUID
) -> None:
    summary = await get_resource_rating_summary(session, resource_id)

    result = await session.exec(
        select(Resource).where(Resource.id == resource_id)
    )
    resource = result.first()
    if resource is None:
        return

    resource.rating_avg = summary["average"]
    resource.rating_count = summary["count"]
    resource.updated_at = datetime.now(UTC)
    session.add(resource)
    await session.commit()
    await session.refresh(resource)

    tenant_ctx = get_current_tenant()
    if tenant_ctx:
        rt_result = await session.exec(
            select(ResourceType).where(ResourceType.id == resource.type_id)
        )
        rt = rt_result.first()
        if rt:
            doc = build_document(
                resource.id, resource.name, resource.description,
                resource.location_lat, resource.location_lng, resource.location_address,
                resource.attributes, resource.base_price, resource.currency,
                resource.status, resource.rating_avg, resource.rating_count,
                rt.slug, resource.created_at,
            )
            sync_resource(str(tenant_ctx.tenant.id), rt.slug, doc)
