import uuid
from datetime import UTC, datetime

from app.core.admin.models import TenantTheme
from app.core.admin.schemas import (
    DomainCreate,
    PlatformLoginRequest,
    StaffInvite,
    TenantConfigUpdate,
    TenantCreate,
    ThemeResponse,
    ThemeUpdate,
)


def test_tenant_theme_model_defaults():
    t = TenantTheme(tenant_id=uuid.uuid4())
    assert t.brand == {}
    assert t.colors == {}
    assert t.typography == {}
    assert t.components == {}
    assert t.features == {}


def test_theme_update_partial():
    data = ThemeUpdate(colors={"primary": "#ff0000"})
    assert data.brand is None
    assert data.colors == {"primary": "#ff0000"}


def test_theme_response_from_model():
    t = TenantTheme(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        brand={"name": "TestBrand"},
        colors={"primary": "#000"},
        typography={},
        components={},
        features={},
        updated_at=datetime.now(UTC),
    )
    resp = ThemeResponse.model_validate(t)
    assert resp.brand["name"] == "TestBrand"


def test_tenant_config_update_partial():
    data = TenantConfigUpdate(name="New Name")
    assert data.name == "New Name"
    assert data.base_currency is None
    assert data.timezone is None
    assert data.config is None


def test_domain_create():
    d = DomainCreate(domain="rentals.example.com", is_primary=True)
    assert d.domain == "rentals.example.com"
    assert d.is_primary is True


def test_staff_invite_defaults():
    s = StaffInvite(email="staff@test.com", full_name="Staff", password="pass123")
    assert s.user_type == "staff"
    assert s.role_slugs == []


def test_tenant_create():
    t = TenantCreate(name="My Rentals", slug="my-rentals")
    assert t.base_currency == "USD"
    assert t.timezone == "UTC"


def test_platform_login_request():
    r = PlatformLoginRequest(email="admin@platform.com", password="secret")
    assert r.email == "admin@platform.com"
