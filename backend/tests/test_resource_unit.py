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
