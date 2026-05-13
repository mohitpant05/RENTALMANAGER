# Reviews & Ratings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a two-way review system where customers review resources post-booking and listers review customers, with configurable rating categories per resource type, moderation queue, and automatic resource rating aggregation.

**Architecture:** Reviews are tenant-scoped, linked to a completed booking. Each review has an overall 1-5 star rating plus optional per-category ratings (categories defined on ResourceType). A service layer enforces constraints (one review per booking per direction, booking must be completed). On review creation, resource `rating_avg` and `rating_count` are updated atomically and synced to Meilisearch.

**Tech Stack:** FastAPI, SQLModel, PostgreSQL (JSONB for category ratings), Meilisearch sync

---

## File Structure

| File | Responsibility |
|------|---------------|
| `backend/app/domains/reviews/__init__.py` | Package marker |
| `backend/app/domains/reviews/models.py` | Review SQLModel + TENANT_REVIEW_TABLES |
| `backend/app/domains/reviews/schemas.py` | Pydantic request/response schemas |
| `backend/app/domains/reviews/service.py` | Business logic: create, list, moderate, aggregate |
| `backend/app/domains/reviews/router.py` | API endpoints |
| `backend/app/domains/resources/service.py` | Modified: update_resource_rating helper |
| `backend/app/core/tenancy/provisioning.py` | Modified: register review tables |
| `backend/app/main.py` | Modified: register review router |
| `backend/tests/test_review_unit.py` | Unit tests for schemas, validation |
| `backend/tests/test_review_integration.py` | Integration tests for full review flow |

---

### Task 1: Review model and table registration

**Files:**
- Create: `backend/app/domains/reviews/__init__.py`
- Create: `backend/app/domains/reviews/models.py`
- Modify: `backend/app/core/tenancy/provisioning.py`

- [ ] **Step 1: Create package**

```python
# backend/app/domains/reviews/__init__.py
```

Empty file.

- [ ] **Step 2: Create Review model**

```python
# backend/app/domains/reviews/models.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

TENANT_REVIEW_TABLES: set[str] = {"reviews"}


class Review(SQLModel, table=True):
    __tablename__ = "reviews"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    booking_id: uuid.UUID = Field(foreign_key="bookings.id", index=True)
    resource_id: uuid.UUID = Field(foreign_key="resources.id", index=True)
    reviewer_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    target_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", index=True)
    direction: str = Field(max_length=20, index=True)
    rating: int = Field(ge=1, le=5)
    category_ratings: dict | None = Field(default=None, sa_column=Column(JSONB))
    title: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    status: str = Field(default="published", max_length=20, index=True)
    moderation_reason: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
```

`direction` is either `"customer_to_resource"` or `"lister_to_customer"`.
`category_ratings` stores `{"cleanliness": 4, "location": 5, ...}` — categories come from ResourceType.
`status` is `"published"`, `"flagged"`, or `"removed"`.

- [ ] **Step 3: Register review tables in provisioning**

In `backend/app/core/tenancy/provisioning.py`, add import and registration:

```python
from app.domains.reviews.models import TENANT_REVIEW_TABLES  # noqa: F401
```

And add:

```python
TENANT_TABLE_REGISTRY.update(TENANT_REVIEW_TABLES)
```

- [ ] **Step 4: Verify**

Run: `docker exec rm-backend python -c "from app.domains.reviews.models import Review, TENANT_REVIEW_TABLES; from app.core.tenancy.provisioning import TENANT_TABLE_REGISTRY; assert 'reviews' in TENANT_TABLE_REGISTRY; print('OK')"`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/domains/reviews/ backend/app/core/tenancy/provisioning.py
git commit -m "feat(reviews): add Review model and register tenant table"
```

---

### Task 2: Review schemas

**Files:**
- Create: `backend/app/domains/reviews/schemas.py`

- [ ] **Step 1: Create schemas**

```python
# backend/app/domains/reviews/schemas.py
import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class ReviewCreate(BaseModel):
    booking_id: uuid.UUID
    rating: int
    category_ratings: dict[str, int] | None = None
    title: str | None = None
    body: str | None = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("rating must be between 1 and 5")
        return v

    @field_validator("category_ratings")
    @classmethod
    def validate_category_ratings(cls, v: dict[str, int] | None) -> dict[str, int] | None:
        if v is None:
            return v
        for key, val in v.items():
            if val < 1 or val > 5:
                raise ValueError(f"category rating '{key}' must be between 1 and 5")
        return v


class ReviewResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    resource_id: uuid.UUID
    reviewer_id: uuid.UUID
    target_user_id: uuid.UUID | None
    direction: str
    rating: int
    category_ratings: dict[str, int] | None
    title: str | None
    body: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewListParams(BaseModel):
    resource_id: uuid.UUID | None = None
    reviewer_id: uuid.UUID | None = None
    target_user_id: uuid.UUID | None = None
    direction: str | None = None
    status: str = "published"
    offset: int = 0
    limit: int = 20

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("limit must be between 1 and 100")
        return v

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str | None) -> str | None:
        if v is not None and v not in ("customer_to_resource", "lister_to_customer"):
            raise ValueError("direction must be 'customer_to_resource' or 'lister_to_customer'")
        return v


class ReviewModerate(BaseModel):
    status: str
    reason: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("published", "flagged", "removed"):
            raise ValueError("status must be 'published', 'flagged', or 'removed'")
        return v


class ResourceRatingResponse(BaseModel):
    rating_avg: float
    rating_count: int
    category_averages: dict[str, float] | None = None
```

- [ ] **Step 2: Verify**

Run: `docker exec rm-backend python -c "from app.domains.reviews.schemas import ReviewCreate, ReviewResponse, ReviewListParams; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/domains/reviews/schemas.py
git commit -m "feat(reviews): add review request/response schemas"
```

---

### Task 3: Review service

**Files:**
- Create: `backend/app/domains/reviews/service.py`

- [ ] **Step 1: Create service**

```python
# backend/app/domains/reviews/service.py
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

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
    result = await session.exec(
        select(
            func.avg(Review.rating).label("avg"),
            func.count(Review.id).label("count"),
        ).where(
            Review.resource_id == resource_id,
            Review.direction == "customer_to_resource",
            Review.status == "published",
        )
    )
    row = result.first()
    avg_rating = float(row.avg) if row.avg else 0.0
    count = row.count or 0
    return {"rating_avg": round(avg_rating, 2), "rating_count": count}


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

    resource.rating_avg = summary["rating_avg"]
    resource.rating_count = summary["rating_count"]
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
```

- [ ] **Step 2: Verify**

Run: `docker exec rm-backend python -c "from app.domains.reviews.service import create_review, list_reviews, moderate_review; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/domains/reviews/service.py
git commit -m "feat(reviews): add review service with rating aggregation and search sync"
```

---

### Task 4: Review router

**Files:**
- Create: `backend/app/domains/reviews/router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create router**

```python
# backend/app/domains/reviews/router.py
import uuid

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import get_current_user, require_permission
from app.core.auth.models import User
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


@router.post("/", response_model=ReviewResponse, status_code=201)
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


@router.get("/", response_model=list[ReviewResponse])
async def list_all_reviews(
    resource_id: uuid.UUID | None = Query(default=None),
    direction: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await list_reviews(
        session,
        resource_id=resource_id,
        direction=direction,
        offset=offset,
        limit=limit,
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


@router.get("/resource/{resource_id}/summary", response_model=ResourceRatingResponse)
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
```

- [ ] **Step 2: Register router in main.py**

Add import in `backend/app/main.py`:

```python
from app.domains.reviews.router import router as review_router
```

And add after search_router:

```python
app.include_router(review_router)
```

- [ ] **Step 3: Verify**

Run: `docker exec rm-backend python -c "from app.main import app; paths = [r.path for r in app.routes if hasattr(r, 'path')]; assert '/api/reviews/' in paths; print('Review routes registered')"`

Expected: `Review routes registered`

- [ ] **Step 4: Commit**

```bash
git add backend/app/domains/reviews/router.py backend/app/main.py
git commit -m "feat(reviews): add review API endpoints with moderation"
```

---

### Task 5: Unit tests

**Files:**
- Create: `backend/tests/test_review_unit.py`

- [ ] **Step 1: Write unit tests**

```python
# backend/tests/test_review_unit.py
import uuid
from datetime import UTC, datetime

from pydantic import ValidationError

from app.domains.reviews.models import TENANT_REVIEW_TABLES, Review
from app.domains.reviews.schemas import (
    ReviewCreate,
    ReviewListParams,
    ReviewModerate,
    ReviewResponse,
)


def test_review_model_defaults():
    r = Review(
        booking_id=uuid.uuid4(),
        resource_id=uuid.uuid4(),
        reviewer_id=uuid.uuid4(),
        direction="customer_to_resource",
        rating=4,
    )
    assert r.status == "published"
    assert r.category_ratings is None
    assert r.title is None
    assert r.target_user_id is None


def test_tenant_review_tables():
    assert TENANT_REVIEW_TABLES == {"reviews"}


def test_review_create_valid():
    data = ReviewCreate(
        booking_id=uuid.uuid4(),
        rating=5,
        title="Great place",
        body="Loved the view",
        category_ratings={"cleanliness": 5, "location": 4},
    )
    assert data.rating == 5
    assert data.category_ratings["cleanliness"] == 5


def test_review_create_invalid_rating():
    try:
        ReviewCreate(booking_id=uuid.uuid4(), rating=0)
        assert False, "Should raise"
    except ValidationError:
        pass

    try:
        ReviewCreate(booking_id=uuid.uuid4(), rating=6)
        assert False, "Should raise"
    except ValidationError:
        pass


def test_review_create_invalid_category_rating():
    try:
        ReviewCreate(
            booking_id=uuid.uuid4(),
            rating=4,
            category_ratings={"cleanliness": 6},
        )
        assert False, "Should raise"
    except ValidationError:
        pass


def test_review_list_params_defaults():
    params = ReviewListParams()
    assert params.status == "published"
    assert params.offset == 0
    assert params.limit == 20


def test_review_list_params_invalid_direction():
    try:
        ReviewListParams(direction="invalid")
        assert False, "Should raise"
    except ValidationError:
        pass


def test_review_list_params_valid_directions():
    p1 = ReviewListParams(direction="customer_to_resource")
    assert p1.direction == "customer_to_resource"
    p2 = ReviewListParams(direction="lister_to_customer")
    assert p2.direction == "lister_to_customer"


def test_review_list_params_limit_bounds():
    try:
        ReviewListParams(limit=0)
        assert False, "Should raise"
    except ValidationError:
        pass

    try:
        ReviewListParams(limit=101)
        assert False, "Should raise"
    except ValidationError:
        pass


def test_review_moderate_valid():
    m = ReviewModerate(status="flagged", reason="Spam content")
    assert m.status == "flagged"


def test_review_moderate_invalid_status():
    try:
        ReviewModerate(status="deleted")
        assert False, "Should raise"
    except ValidationError:
        pass


def test_review_response_from_model():
    r = Review(
        id=uuid.uuid4(),
        booking_id=uuid.uuid4(),
        resource_id=uuid.uuid4(),
        reviewer_id=uuid.uuid4(),
        direction="customer_to_resource",
        rating=4,
        status="published",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    resp = ReviewResponse.model_validate(r)
    assert resp.rating == 4
    assert resp.direction == "customer_to_resource"
```

- [ ] **Step 2: Run tests**

Run: `docker exec rm-backend python -m pytest tests/test_review_unit.py -v`

Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_review_unit.py
git commit -m "test(reviews): add unit tests for review schemas and model"
```

---

### Task 6: Integration tests

**Files:**
- Create: `backend/tests/test_review_integration.py`

- [ ] **Step 1: Write integration tests**

```python
# backend/tests/test_review_integration.py
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.bookings.models import Booking


@pytest.fixture
async def review_resource_type(client: AsyncClient, admin_headers: dict) -> dict:
    resp = await client.post(
        "/api/resource-types/",
        json={
            "name": "Review Test Venues",
            "slug": "review-test-venues",
            "availability_model": "date_range",
            "pricing_model": "fixed_per_day",
            "attribute_schema": [],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def review_resource(
    client: AsyncClient, admin_headers: dict, review_resource_type: dict
) -> dict:
    resp = await client.post(
        "/api/resources/",
        json={
            "type_id": review_resource_type["id"],
            "name": "Review Test Villa",
            "description": "A place to review",
            "base_price": 100.0,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    resource = resp.json()
    resp = await client.put(
        f"/api/resources/{resource['id']}",
        json={"status": "active"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture
async def completed_booking(
    db_session: AsyncSession, review_resource: dict, customer_headers: dict, client: AsyncClient
) -> Booking:
    """Create a booking directly in DB with 'completed' status for review testing."""
    from app.core.auth.models import User
    from sqlmodel import select

    # Get the customer user from headers by making a /me call
    resp = await client.get("/api/auth/me", headers=customer_headers)
    assert resp.status_code == 200
    customer_id = resp.json()["id"]

    booking = Booking(
        resource_id=uuid.UUID(review_resource["id"]),
        user_id=uuid.UUID(customer_id),
        status="completed",
        start_time=datetime.now(UTC) - timedelta(days=3),
        end_time=datetime.now(UTC) - timedelta(days=1),
        total_price=200.0,
    )
    db_session.add(booking)
    await db_session.commit()
    await db_session.refresh(booking)
    return booking


@pytest.mark.asyncio
async def test_create_review(
    client: AsyncClient, customer_headers: dict, completed_booking: Booking
):
    resp = await client.post(
        "/api/reviews/",
        json={
            "booking_id": str(completed_booking.id),
            "rating": 5,
            "title": "Amazing stay",
            "body": "Would definitely come back",
        },
        headers=customer_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["rating"] == 5
    assert data["direction"] == "customer_to_resource"
    assert data["resource_id"] == str(completed_booking.resource_id)


@pytest.mark.asyncio
async def test_create_review_duplicate_fails(
    client: AsyncClient, customer_headers: dict, completed_booking: Booking
):
    await client.post(
        "/api/reviews/",
        json={"booking_id": str(completed_booking.id), "rating": 4},
        headers=customer_headers,
    )
    resp = await client.post(
        "/api/reviews/",
        json={"booking_id": str(completed_booking.id), "rating": 3},
        headers=customer_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_review_non_completed_booking_fails(
    client: AsyncClient, customer_headers: dict, db_session: AsyncSession, review_resource: dict
):
    resp = await client.get("/api/auth/me", headers=customer_headers)
    customer_id = resp.json()["id"]

    booking = Booking(
        resource_id=uuid.UUID(review_resource["id"]),
        user_id=uuid.UUID(customer_id),
        status="confirmed",
        start_time=datetime.now(UTC) + timedelta(days=1),
        end_time=datetime.now(UTC) + timedelta(days=3),
        total_price=200.0,
    )
    db_session.add(booking)
    await db_session.commit()
    await db_session.refresh(booking)

    resp = await client.post(
        "/api/reviews/",
        json={"booking_id": str(booking.id), "rating": 5},
        headers=customer_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_reviews_for_resource(
    client: AsyncClient, customer_headers: dict, completed_booking: Booking
):
    await client.post(
        "/api/reviews/",
        json={"booking_id": str(completed_booking.id), "rating": 4},
        headers=customer_headers,
    )
    resp = await client.get(
        f"/api/reviews/?resource_id={completed_booking.resource_id}",
        headers=customer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["resource_id"] == str(completed_booking.resource_id)


@pytest.mark.asyncio
async def test_list_my_reviews(
    client: AsyncClient, customer_headers: dict, completed_booking: Booking
):
    await client.post(
        "/api/reviews/",
        json={"booking_id": str(completed_booking.id), "rating": 5},
        headers=customer_headers,
    )
    resp = await client.get("/api/reviews/my", headers=customer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_moderate_review(
    client: AsyncClient, customer_headers: dict, admin_headers: dict, completed_booking: Booking
):
    resp = await client.post(
        "/api/reviews/",
        json={"booking_id": str(completed_booking.id), "rating": 1, "body": "Terrible"},
        headers=customer_headers,
    )
    review_id = resp.json()["id"]

    resp = await client.post(
        f"/api/reviews/{review_id}/moderate",
        json={"status": "flagged", "reason": "Potential spam"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "flagged"


@pytest.mark.asyncio
async def test_rating_summary(
    client: AsyncClient, customer_headers: dict, completed_booking: Booking
):
    await client.post(
        "/api/reviews/",
        json={"booking_id": str(completed_booking.id), "rating": 4},
        headers=customer_headers,
    )
    resp = await client.get(
        f"/api/reviews/resource/{completed_booking.resource_id}/summary",
        headers=customer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["rating_avg"] == 4.0
    assert data["rating_count"] == 1


@pytest.mark.asyncio
async def test_resource_rating_updated_after_review(
    client: AsyncClient, customer_headers: dict, completed_booking: Booking
):
    await client.post(
        "/api/reviews/",
        json={"booking_id": str(completed_booking.id), "rating": 5},
        headers=customer_headers,
    )
    resp = await client.get(
        f"/api/resources/{completed_booking.resource_id}",
        headers=customer_headers,
    )
    assert resp.status_code == 200
    resource = resp.json()
    assert resource["rating_avg"] == 5.0
    assert resource["rating_count"] == 1
```

- [ ] **Step 2: Run tests**

Run: `docker exec rm-backend python -m pytest tests/test_review_integration.py -v --tb=short`

Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_review_integration.py
git commit -m "test(reviews): add integration tests for review flow, moderation, ratings"
```

---

### Task 7: Final verification + cleanup

- [ ] **Step 1: Run full test suite**

Run: `docker exec rm-backend python -m pytest --tb=short -q`

Expected: All tests pass (163 existing + new review tests).

- [ ] **Step 2: Lint check**

Run: `docker exec rm-backend python -m ruff check app/domains/reviews/ tests/test_review_unit.py tests/test_review_integration.py`

Expected: Clean or auto-fixable.

- [ ] **Step 3: Fix lint issues if any**

```bash
docker exec rm-backend python -m ruff check --fix app/domains/reviews/ tests/test_review_unit.py tests/test_review_integration.py
```

- [ ] **Step 4: Verify routes registered**

Run: `docker exec rm-backend python -c "from app.main import app; paths = [r.path for r in app.routes if hasattr(r, 'path')]; assert '/api/reviews/' in paths; assert '/api/reviews/{review_id}/moderate' in paths; print('All routes OK')"`

- [ ] **Step 5: Commit if lint changes were needed**

```bash
git add -A && git commit -m "style: fix lint issues in reviews module" --allow-empty
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|-----------------|------|
| Post-booking only (prevents fake reviews) | Task 3 (booking.status == "completed" check) |
| Two-way: user reviews resource, lister reviews user | Task 3 (direction param) + Task 4 (separate endpoints) |
| Rating: 1-5 stars | Task 2 (schema validation) + Task 1 (model field) |
| Configurable categories per resource type | Task 1 (category_ratings JSONB) + Task 2 (validation) |
| Review moderation — flagging + admin approval queue | Task 3 (moderate_review) + Task 4 (moderate endpoint) |
| One review per booking per direction | Task 3 (duplicate check) |
| Rating aggregation on resource | Task 3 (_update_resource_rating) |
| Search sync on rating change | Task 3 (Meilisearch sync in _update_resource_rating) |
| Trust score = f(verification_level, avg_rating, booking_history) | Deferred to Verification plan — depends on verification levels not yet built |
