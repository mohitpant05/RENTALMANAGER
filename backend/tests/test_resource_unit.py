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
from app.domains.resources.availability.time_slot import TimeSlotProvider
from app.domains.resources.availability.hourly import HourlyProvider


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


def test_time_slot_validate_times_valid():
    provider = TimeSlotProvider()
    now = datetime.now(timezone.utc)
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=1, minutes=30)
    slot_config = {"duration_options": ["1h", "1.5h", "2h"], "buffer_between": "30min"}
    errors = provider.validate_times(start, end, slot_config)
    assert errors == []


def test_time_slot_validate_times_invalid_duration():
    provider = TimeSlotProvider()
    now = datetime.now(timezone.utc)
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=3)
    slot_config = {"duration_options": ["1h", "1.5h", "2h"], "buffer_between": "30min"}
    errors = provider.validate_times(start, end, slot_config)
    assert len(errors) == 1


def test_time_slot_validate_no_config():
    provider = TimeSlotProvider()
    now = datetime.now(timezone.utc)
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=1)
    errors = provider.validate_times(start, end, slot_config=None)
    assert errors == []


def test_hourly_validate_times_valid():
    provider = HourlyProvider()
    now = datetime.now(timezone.utc)
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=4)
    errors = provider.validate_times(start, end, slot_config=None)
    assert errors == []


def test_hourly_validate_times_end_before_start():
    provider = HourlyProvider()
    now = datetime.now(timezone.utc)
    start = now + timedelta(hours=5)
    end = now + timedelta(hours=1)
    errors = provider.validate_times(start, end, slot_config=None)
    assert len(errors) == 1


def test_hourly_validate_times_minimum_duration():
    provider = HourlyProvider()
    now = datetime.now(timezone.utc)
    start = now + timedelta(hours=1)
    end = start + timedelta(minutes=15)
    errors = provider.validate_times(start, end, slot_config=None)
    assert len(errors) == 1


def test_get_provider_time_slot():
    provider = get_availability_provider("time_slot")
    assert isinstance(provider, TimeSlotProvider)


def test_get_provider_hourly():
    provider = get_availability_provider("hourly")
    assert isinstance(provider, HourlyProvider)


from app.domains.resources.pricing.strategy import get_pricing_provider
from app.domains.resources.pricing.providers import (
    FixedPerDayProvider,
    FixedPerSlotProvider,
    HourlyPricingProvider,
    TieredProvider,
)


def test_fixed_per_day_pricing():
    provider = FixedPerDayProvider()
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(days=3)
    price = provider.calculate(base_price=100.0, start=start, end=end, config=None)
    assert price == 300.0


def test_fixed_per_day_partial_day_rounds_up():
    provider = FixedPerDayProvider()
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(days=2, hours=6)
    price = provider.calculate(base_price=100.0, start=start, end=end, config=None)
    assert price == 300.0


def test_fixed_per_slot_pricing():
    provider = FixedPerSlotProvider()
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(hours=1, minutes=30)
    price = provider.calculate(base_price=50.0, start=start, end=end, config=None)
    assert price == 50.0


def test_hourly_pricing():
    provider = HourlyPricingProvider()
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(hours=4)
    price = provider.calculate(base_price=25.0, start=start, end=end, config=None)
    assert price == 100.0


def test_hourly_pricing_partial_hour():
    provider = HourlyPricingProvider()
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(hours=2, minutes=30)
    price = provider.calculate(base_price=20.0, start=start, end=end, config=None)
    assert price == 60.0


def test_tiered_pricing():
    provider = TieredProvider()
    config = {
        "tiers": [
            {"min_days": 1, "max_days": 3, "rate_multiplier": 1.0},
            {"min_days": 4, "max_days": 7, "rate_multiplier": 0.85},
            {"min_days": 8, "max_days": None, "rate_multiplier": 0.70},
        ]
    }
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(days=10)
    price = provider.calculate(base_price=100.0, start=start, end=end, config=config)
    # Days 1-3: 3 * 100 * 1.0 = 300
    # Days 4-7: 4 * 100 * 0.85 = 340
    # Days 8-10: 3 * 100 * 0.70 = 210
    assert price == 850.0


def test_tiered_pricing_short_stay():
    provider = TieredProvider()
    config = {
        "tiers": [
            {"min_days": 1, "max_days": 3, "rate_multiplier": 1.0},
            {"min_days": 4, "max_days": 7, "rate_multiplier": 0.85},
        ]
    }
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(days=2)
    price = provider.calculate(base_price=100.0, start=start, end=end, config=config)
    assert price == 200.0


def test_get_pricing_provider_all_models():
    assert isinstance(get_pricing_provider("fixed_per_day"), FixedPerDayProvider)
    assert isinstance(get_pricing_provider("fixed_per_slot"), FixedPerSlotProvider)
    assert isinstance(get_pricing_provider("per_hour"), HourlyPricingProvider)
    assert isinstance(get_pricing_provider("tiered"), TieredProvider)


def test_get_pricing_provider_unknown_raises():
    try:
        get_pricing_provider("unknown")
        assert False, "Should have raised"
    except ValueError:
        pass


from pydantic import ValidationError

from app.domains.resources.schemas import (
    ResourceTypeCreate,
    ResourceTypeUpdate,
)


def test_resource_type_create_valid():
    data = ResourceTypeCreate(
        name="Apartments",
        slug="apartments",
        availability_model="date_range",
        pricing_model="fixed_per_day",
    )
    assert data.name == "Apartments"


def test_resource_type_create_invalid_availability_model():
    try:
        ResourceTypeCreate(
            name="Test",
            slug="test",
            availability_model="invalid_model",
            pricing_model="fixed_per_day",
        )
        assert False, "Should have raised"
    except ValidationError:
        pass


def test_resource_type_create_invalid_pricing_model():
    try:
        ResourceTypeCreate(
            name="Test",
            slug="test",
            availability_model="date_range",
            pricing_model="invalid_model",
        )
        assert False, "Should have raised"
    except ValidationError:
        pass


def test_resource_type_update_partial():
    data = ResourceTypeUpdate(name="Updated Name")
    assert data.name == "Updated Name"
    assert data.slug is None


from app.domains.resources.templates import RESOURCE_TYPE_TEMPLATES


def test_templates_have_required_keys():
    required = {"name", "slug", "availability_model", "pricing_model", "attribute_schema"}
    for slug, tmpl in RESOURCE_TYPE_TEMPLATES.items():
        assert required.issubset(tmpl.keys()), f"Template '{slug}' missing keys"


def test_venues_template():
    tmpl = RESOURCE_TYPE_TEMPLATES["venues"]
    assert tmpl["availability_model"] == "date_range"
    assert tmpl["pricing_model"] == "fixed_per_day"
    attr_names = {a["name"] for a in tmpl["attribute_schema"]}
    assert "bedrooms" in attr_names
    assert "property_type" in attr_names


def test_vehicles_template():
    tmpl = RESOURCE_TYPE_TEMPLATES["vehicles"]
    assert tmpl["availability_model"] == "hourly"
    assert tmpl["pricing_model"] == "per_hour"
    attr_names = {a["name"] for a in tmpl["attribute_schema"]}
    assert "vehicle_type" in attr_names
    assert "seats" in attr_names


def test_cooks_template():
    tmpl = RESOURCE_TYPE_TEMPLATES["cooks"]
    assert tmpl["availability_model"] == "time_slot"
    assert tmpl["pricing_model"] == "fixed_per_slot"
    attr_names = {a["name"] for a in tmpl["attribute_schema"]}
    assert "cuisine_type" in attr_names
