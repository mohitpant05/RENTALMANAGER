import uuid
from datetime import UTC, datetime

from pydantic import ValidationError

from app.core.search.client import get_index_uid
from app.core.search.query import _build_filter_string
from app.core.search.schemas import SearchRequest, SearchResponse
from app.core.search.sync import build_document


def test_get_index_uid_basic():
    uid = get_index_uid("abc-123", "venues")
    assert uid == "t_abc_123_venues"


def test_get_index_uid_complex_slug():
    uid = get_index_uid("tenant-uuid-here", "electric-bikes")
    assert uid == "t_tenant_uuid_here_electric_bikes"


def test_build_document_basic():
    doc = build_document(
        resource_id=uuid.UUID("12345678-1234-1234-1234-123456789012"),
        name="Beach House",
        description="A nice place",
        location_lat=40.7,
        location_lng=-74.0,
        location_address="123 Main St",
        attributes={"bedrooms": 3, "pet_friendly": True},
        base_price=150.0,
        currency="USD",
        status="active",
        rating_avg=4.5,
        rating_count=10,
        type_slug="venues",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert doc["id"] == "12345678-1234-1234-1234-123456789012"
    assert doc["name"] == "Beach House"
    assert doc["_geo"] == {"lat": 40.7, "lng": -74.0}
    assert doc["attr_bedrooms"] == 3
    assert doc["attr_pet_friendly"] is True
    assert doc["base_price"] == 150.0
    assert doc["type_slug"] == "venues"


def test_build_document_no_geo():
    doc = build_document(
        resource_id=uuid.uuid4(),
        name="Service",
        description=None,
        location_lat=None,
        location_lng=None,
        location_address=None,
        attributes=None,
        base_price=50.0,
        currency="USD",
        status="active",
        rating_avg=0.0,
        rating_count=0,
        type_slug="cooks",
        created_at=datetime.now(UTC),
    )
    assert "_geo" not in doc
    assert doc["description"] == ""


def test_build_document_no_attributes():
    doc = build_document(
        resource_id=uuid.uuid4(),
        name="Item",
        description="Desc",
        location_lat=None,
        location_lng=None,
        location_address=None,
        attributes=None,
        base_price=10.0,
        currency="EUR",
        status="active",
        rating_avg=3.0,
        rating_count=5,
        type_slug="vehicles",
        created_at=datetime.now(UTC),
    )
    attr_keys = [k for k in doc.keys() if k.startswith("attr_")]
    assert attr_keys == []


def test_build_filter_string_range():
    filters = {"base_price": {"min": 50, "max": 200}}
    parts = _build_filter_string(filters)
    assert "base_price >= 50" in parts
    assert "base_price <= 200" in parts


def test_build_filter_string_list():
    filters = {"amenities": ["pool", "wifi"]}
    parts = _build_filter_string(filters)
    assert len(parts) == 1
    assert "OR" in parts[0]


def test_build_filter_string_exact():
    filters = {"pet_friendly": "true"}
    parts = _build_filter_string(filters)
    assert parts == ['attr_pet_friendly = "true"']


def test_build_filter_string_empty():
    assert _build_filter_string(None) == []
    assert _build_filter_string({}) == []


def test_search_request_defaults():
    req = SearchRequest(resource_type_slug="venues")
    assert req.q == ""
    assert req.offset == 0
    assert req.limit == 20
    assert req.sort_order == "asc"


def test_search_request_limit_validation():
    try:
        SearchRequest(resource_type_slug="venues", limit=0)
        assert False, "Should raise"
    except ValidationError:
        pass

    try:
        SearchRequest(resource_type_slug="venues", limit=101)
        assert False, "Should raise"
    except ValidationError:
        pass


def test_search_request_sort_order_validation():
    try:
        SearchRequest(resource_type_slug="venues", sort_order="invalid")
        assert False, "Should raise"
    except ValidationError:
        pass


def test_search_response_model():
    resp = SearchResponse(
        hits=[],
        query="test",
        processing_time_ms=5,
        estimated_total_hits=0,
        offset=0,
        limit=20,
    )
    assert resp.hits == []
    assert resp.processing_time_ms == 5
