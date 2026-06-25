import uuid

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import get_current_user, get_optional_user, require_permission
from app.core.auth.models import User
from app.core.auth.scoping import resolve_data_scope
from app.database import get_db
from app.domains.reviews.schemas import (
    ResourceRatingResponse,
    ReviewCreate,
    ReviewModerate,
    ReviewResponse,
)
from app.domains.reviews.service import (
    create_review,
    get_resource_rating_summary,
    get_review,
    list_reviews,
    moderate_review,
)

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("", response_model=ReviewResponse, status_code=201)
async def create_resource_review(
    data: ReviewCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await create_review(session, data, user.id, direction="customer_to_resource")


@router.post("/lister", response_model=ReviewResponse, status_code=201)
async def create_lister_review(
    data: ReviewCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await create_review(session, data, user.id, direction="lister_to_customer")


@router.get("", response_model=list[ReviewResponse])
async def list_all_reviews(
    resource_id: uuid.UUID | None = Query(default=None),
    direction: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    scope_owner_ids = None
    if user is not None:
        scope = await resolve_data_scope(session, user)
        scope_owner_ids = scope.owner_ids if scope.is_scoped else None
    return await list_reviews(
        session,
        resource_id=resource_id,
        direction=direction,
        offset=offset,
        limit=limit,
        scope_owner_ids=scope_owner_ids,
    )


@router.get("/my", response_model=list[ReviewResponse])
async def list_my_reviews(
    direction: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await list_reviews(
        session,
        reviewer_id=user.id,
        direction=direction,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/resource/{resource_id}/summary", response_model=ResourceRatingResponse
)
async def get_rating_summary(
    resource_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    return await get_resource_rating_summary(session, resource_id)


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_one_review(
    review_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await get_review(session, review_id)


@router.post("/{review_id}/moderate", response_model=ReviewResponse)
async def moderate_one_review(
    review_id: uuid.UUID,
    data: ReviewModerate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("reviews:*:moderate")),
):
    return await moderate_review(session, review_id, data.status, data.reason)
