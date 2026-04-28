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
            raise ValueError(
                "direction must be 'customer_to_resource' or 'lister_to_customer'"
            )
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
