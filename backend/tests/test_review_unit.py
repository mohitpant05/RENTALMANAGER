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


def test_review_create_invalid_rating_low():
    try:
        ReviewCreate(booking_id=uuid.uuid4(), rating=0)
        assert False, "Should raise"
    except ValidationError:
        pass


def test_review_create_invalid_rating_high():
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
