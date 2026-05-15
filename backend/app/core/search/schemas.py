from pydantic import BaseModel, field_validator


class SearchRequest(BaseModel):
    q: str = ""
    resource_type_slug: str | None = None
    filters: dict | None = None
    geo_lat: float | None = None
    geo_lng: float | None = None
    geo_radius_km: float | None = None
    sort_by: str | None = None
    sort_order: str = "asc"
    offset: int = 0
    limit: int = 20

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        if v not in ("asc", "desc"):
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("limit must be between 1 and 100")
        return v


class SearchHit(BaseModel):
    id: str
    name: str
    description: str
    location_address: str
    base_price: float
    currency: str
    status: str
    rating_avg: float
    rating_count: int
    type_slug: str
    geo: dict | None = None
    attributes: dict | None = None


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    query: str
    processing_time_ms: int
    estimated_total_hits: int
    offset: int
    limit: int
