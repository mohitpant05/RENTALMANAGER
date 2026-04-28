import uuid
from datetime import datetime, timezone

from app.domains.resources.models import (
    TENANT_RESOURCE_TABLES,
    Resource,
    ResourceAvailability,
    ResourceType,
)


def test_resource_type_model_fields():
    rt = ResourceType(
        name="Apartments",
        slug="apartments",
        availability_model="date_range",
        pricing_model="fixed_per_day",
    )
    assert rt.name == "Apartments"
    assert rt.slug == "apartments"
    assert rt.is_active is True
    assert isinstance(rt.id, uuid.UUID)


def test_resource_model_fields():
    r = Resource(
        type_id=uuid.uuid4(),
        name="Beach House",
        base_price=150.0,
        owner_id=uuid.uuid4(),
    )
    assert r.name == "Beach House"
    assert r.status == "draft"
    assert r.base_price == 150.0
    assert r.version == 1


def test_resource_availability_model_fields():
    ra = ResourceAvailability(
        resource_id=uuid.uuid4(),
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        status="held",
    )
    assert ra.status == "held"
    assert ra.version == 1


def test_tenant_resource_tables_registry():
    expected = {"resource_types", "resources", "resource_availability"}
    assert TENANT_RESOURCE_TABLES == expected


from app.domains.resources.attributes import validate_attributes


def test_validate_required_attribute_present():
    schema = [{"name": "bedrooms", "type": "number", "required": True}]
    errors = validate_attributes({"bedrooms": 3}, schema)
    assert errors == []


def test_validate_required_attribute_missing():
    schema = [{"name": "bedrooms", "type": "number", "required": True}]
    errors = validate_attributes({}, schema)
    assert len(errors) == 1
    assert "bedrooms" in errors[0]


def test_validate_optional_attribute_missing():
    schema = [{"name": "notes", "type": "string", "required": False}]
    errors = validate_attributes({}, schema)
    assert errors == []


def test_validate_number_type():
    schema = [{"name": "seats", "type": "number"}]
    assert validate_attributes({"seats": 4}, schema) == []
    assert len(validate_attributes({"seats": "four"}, schema)) == 1


def test_validate_string_type():
    schema = [{"name": "color", "type": "string"}]
    assert validate_attributes({"color": "red"}, schema) == []
    assert len(validate_attributes({"color": 123}, schema)) == 1


def test_validate_boolean_type():
    schema = [{"name": "wifi", "type": "boolean"}]
    assert validate_attributes({"wifi": True}, schema) == []
    assert len(validate_attributes({"wifi": "yes"}, schema)) == 1


def test_validate_enum_type():
    schema = [{"name": "location", "type": "enum", "options": ["indoor", "outdoor"]}]
    assert validate_attributes({"location": "indoor"}, schema) == []
    assert len(validate_attributes({"location": "rooftop"}, schema)) == 1


def test_validate_tags_type():
    schema = [{"name": "amenities", "type": "tags"}]
    assert validate_attributes({"amenities": ["wifi", "pool"]}, schema) == []
    assert len(validate_attributes({"amenities": "wifi"}, schema)) == 1


def test_validate_unknown_attribute_ignored():
    schema = [{"name": "bedrooms", "type": "number"}]
    errors = validate_attributes({"bedrooms": 3, "extra_field": "val"}, schema)
    assert errors == []


def test_validate_empty_schema():
    errors = validate_attributes({"anything": "goes"}, [])
    assert errors == []


def test_validate_none_schema():
    errors = validate_attributes({"anything": "goes"}, None)
    assert errors == []


from datetime import timedelta

from app.domains.resources.availability.strategy import (
    HoldResult,
    get_availability_provider,
)
from app.domains.resources.availability.date_range import DateRangeProvider


def test_get_availability_provider_date_range():
    provider = get_availability_provider("date_range")
    assert isinstance(provider, DateRangeProvider)


def test_get_availability_provider_unknown_raises():
    try:
        get_availability_provider("unknown_model")
        assert False, "Should have raised"
    except ValueError:
        pass


def test_date_range_validate_times_valid():
    provider = DateRangeProvider()
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=1)
    end = now + timedelta(days=3)
    errors = provider.validate_times(start, end, slot_config=None)
    assert errors == []


def test_date_range_validate_times_end_before_start():
    provider = DateRangeProvider()
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=3)
    end = now + timedelta(days=1)
    errors = provider.validate_times(start, end, slot_config=None)
    assert len(errors) == 1


def test_date_range_validate_times_start_in_past():
    provider = DateRangeProvider()
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)
    end = now + timedelta(days=1)
    errors = provider.validate_times(start, end, slot_config=None)
    assert len(errors) == 1


def test_hold_result_structure():
    result = HoldResult(hold_token="abc-123", expires=datetime.now(timezone.utc))
    assert result.hold_token == "abc-123"
