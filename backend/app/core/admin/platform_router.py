import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app import logging
from app.config import get_settings as _get_settings
from app.core.admin.models import TenantTheme
from app.core.admin.platform_auth import (
    authenticate_platform_user,
    create_platform_token,
    get_current_platform_user,
)
from app.core.admin.schemas import (
    BootstrapAdminRequest,
    BootstrapAdminResponse,
    DashboardStatsResponse,
    DomainCreate,
    DomainResponse,
    PlatformLoginRequest,
    PlatformSettingResponse,
    PlatformSettingUpdate,
    PlatformTokenResponse,
    StaffUserResponse,
    TenantCreate,
    TenantResponse,
    ThemeResponse,
    ThemeUpdate,
    ValidateKeyRequest,
)
from app.core.auth.models import PlatformUser, Role, User, UserRole
from app.core.auth.password import hash_password
from app.core.tenancy.context import validate_schema_name
from app.core.tenancy.models import PlatformConfig, Tenant, TenantDomain
from app.core.tenancy.provisioning import provision_tenant_schema
from app.database import engine, get_session
from app.rate_limiter import limiter

router = APIRouter(prefix="/api/platform", tags=["platform"])


@router.post("/login", response_model=PlatformTokenResponse)
@limiter.limit("5/15minutes")
async def platform_login(
    request: Request,
    data: PlatformLoginRequest,
    session: AsyncSession = Depends(get_session),
):
    user = await authenticate_platform_user(session, data.email, data.password)
    token = create_platform_token(str(user.id))
    return PlatformTokenResponse(access_token=token)


@router.get("/tenants", response_model=list[TenantResponse])
async def list_tenants(
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(select(Tenant))
    tenants = list(result.all())
    return [TenantResponse.model_validate(t) for t in tenants]


@router.post("/tenants", response_model=TenantResponse, status_code=201)
async def create_tenant(
    data: TenantCreate,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(select(Tenant).where(Tenant.slug == data.slug))
    if result.first() is not None:
        raise HTTPException(status_code=409, detail="Slug already taken")

    tenant_id = uuid.uuid4()
    schema_name = f"tenant_{str(tenant_id).replace('-', '_')}"
    tenant = Tenant(
        id=tenant_id,
        name=data.name,
        slug=data.slug,
        schema_name=schema_name,
        base_currency=data.base_currency,
        timezone=data.timezone,
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)

    await provision_tenant_schema(engine, session, str(tenant_id))
    return TenantResponse.model_validate(tenant)


@router.get("/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.first()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse.model_validate(tenant)


@router.post("/tenants/{tenant_id}/deactivate", response_model=TenantResponse)
async def deactivate_tenant(
    tenant_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.first()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.is_active = False
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return TenantResponse.model_validate(tenant)


@router.post("/tenants/{tenant_id}/activate", response_model=TenantResponse)
async def activate_tenant(
    tenant_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.first()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.is_active = True
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return TenantResponse.model_validate(tenant)


@router.patch("/tenants/{tenant_id}/config", response_model=TenantResponse)
async def update_tenant_config_platform(
    tenant_id: uuid.UUID,
    payload: dict,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    try:
        result = await session.exec(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.first()
        if tenant is None:
            raise HTTPException(status_code=404, detail="Tenant not found")
        existing = dict(tenant.config) if tenant.config else {}
        existing.update(payload)
        tenant.config = existing
        tenant.updated_at = datetime.now(UTC)
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        return TenantResponse.model_validate(tenant)
    except HTTPException:
        raise
    except Exception as error:
        logging.log("update_tenant_config_platform", {"EVENT": "update_tenant_config_error", "ERROR": error})
        raise HTTPException(status_code=500, detail="Failed to update tenant config")


@router.get("/tenants/{tenant_id}/domains", response_model=list[DomainResponse])
async def list_tenant_domains(
    tenant_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(select(Tenant).where(Tenant.id == tenant_id))
    if result.first() is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    result = await session.exec(
        select(TenantDomain).where(TenantDomain.tenant_id == tenant_id)
    )
    return [DomainResponse.model_validate(d) for d in result.all()]


@router.post("/tenants/{tenant_id}/domains", response_model=DomainResponse, status_code=201)
async def add_tenant_domain(
    tenant_id: uuid.UUID,
    data: DomainCreate,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(select(Tenant).where(Tenant.id == tenant_id))
    if result.first() is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    result = await session.exec(
        select(TenantDomain).where(TenantDomain.domain == data.domain)
    )
    if result.first() is not None:
        raise HTTPException(status_code=409, detail="Domain already registered")
    domain = TenantDomain(
        tenant_id=tenant_id,
        domain=data.domain,
        is_primary=data.is_primary,
    )
    session.add(domain)
    await session.commit()
    await session.refresh(domain)
    return DomainResponse.model_validate(domain)


@router.put("/tenants/{tenant_id}/domains/{domain_id}", response_model=DomainResponse)
async def update_tenant_domain(
    tenant_id: uuid.UUID,
    domain_id: uuid.UUID,
    data: DomainCreate,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(
        select(TenantDomain).where(
            TenantDomain.id == domain_id, TenantDomain.tenant_id == tenant_id
        )
    )
    domain = result.first()
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    existing = await session.exec(
        select(TenantDomain).where(
            TenantDomain.domain == data.domain, TenantDomain.id != domain_id
        )
    )
    if existing.first() is not None:
        raise HTTPException(status_code=409, detail="Domain already registered")
    domain.domain = data.domain
    domain.is_primary = data.is_primary
    session.add(domain)
    await session.commit()
    await session.refresh(domain)
    return DomainResponse.model_validate(domain)


@router.delete("/tenants/{tenant_id}/domains/{domain_id}", status_code=204)
async def delete_tenant_domain(
    tenant_id: uuid.UUID,
    domain_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(
        select(TenantDomain).where(
            TenantDomain.id == domain_id, TenantDomain.tenant_id == tenant_id
        )
    )
    domain = result.first()
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    await session.delete(domain)
    await session.commit()


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def dashboard_stats(
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(select(Tenant))
    tenants = list(result.all())

    active = sum(1 for t in tenants if t.is_active)
    total_users = 0
    total_bookings = 0

    for tenant in tenants:
        if not tenant.is_active:
            continue
        try:
            validate_schema_name(tenant.schema_name)
            row = await session.execute(
                text(f"SELECT COUNT(*) FROM {tenant.schema_name}.users")
            )
            total_users += row.scalar() or 0
            row = await session.execute(
                text(f"SELECT COUNT(*) FROM {tenant.schema_name}.bookings")
            )
            total_bookings += row.scalar() or 0
        except Exception:
            continue

    from app.main import _ping_meilisearch, _ping_minio, _ping_postgres, _ping_redis

    services = {
        "postgres": await _ping_postgres(),
        "redis": await _ping_redis(),
        "meilisearch": await _ping_meilisearch(),
        "minio": await _ping_minio(),
    }

    return DashboardStatsResponse(
        total_tenants=len(tenants),
        active_tenants=active,
        inactive_tenants=len(tenants) - active,
        total_users=total_users,
        total_bookings=total_bookings,
        services=services,
    )


@router.get("/settings", response_model=list[PlatformSettingResponse])
async def list_settings(
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(select(PlatformConfig))
    return list(result.all())


@router.put("/settings/{key}", response_model=PlatformSettingResponse)
async def upsert_setting(
    key: str,
    data: PlatformSettingUpdate,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(
        select(PlatformConfig).where(PlatformConfig.key == key)
    )
    setting = result.first()
    if setting is None:
        setting = PlatformConfig(key=key, value=data.value, description=data.description)
        session.add(setting)
    else:
        setting.value = data.value
        if data.description is not None:
            setting.description = data.description
        setting.updated_at = datetime.now(UTC)
        session.add(setting)
    await session.commit()
    await session.refresh(setting)
    return setting


@router.post("/validate-key")
async def validate_secret_key(data: ValidateKeyRequest):
    settings = _get_settings()
    import logging
    logging.getLogger("app.platform").warning(
        "validate-key: received=%r expected=%r match=%s",
        data.key, settings.superadmin_secret_key,
        data.key == settings.superadmin_secret_key,
    )
    if data.key != settings.superadmin_secret_key:
        raise HTTPException(status_code=404, detail="Not found")
    return {"valid": True}


@router.get("/tenants/{tenant_id}/theme", response_model=ThemeResponse)
async def get_tenant_theme(
    tenant_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(
        select(TenantTheme).where(TenantTheme.tenant_id == tenant_id)
    )
    theme = result.first()
    if theme is None:
        raise HTTPException(status_code=404, detail="Theme not found")
    return ThemeResponse.model_validate(theme)


@router.put("/tenants/{tenant_id}/theme", response_model=ThemeResponse)
async def update_tenant_theme(
    tenant_id: uuid.UUID,
    data: ThemeUpdate,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(
        select(TenantTheme).where(TenantTheme.tenant_id == tenant_id)
    )
    theme = result.first()
    if theme is None:
        theme = TenantTheme(tenant_id=tenant_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(theme, field, value)
    theme.updated_at = datetime.now(UTC)
    session.add(theme)
    await session.commit()
    await session.refresh(theme)
    return ThemeResponse.model_validate(theme)


@router.post("/bootstrap-admin", response_model=BootstrapAdminResponse, status_code=201)
async def bootstrap_admin(
    data: BootstrapAdminRequest,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(select(Tenant).where(Tenant.id == data.tenant_id))
    tenant = result.first()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    schema = tenant.schema_name

    # Ensure domain is mapped to this tenant
    result = await session.exec(
        select(TenantDomain).where(TenantDomain.domain == data.domain)
    )
    existing_domain = result.first()
    if existing_domain is None:
        domain_record = TenantDomain(
            tenant_id=tenant.id,
            domain=data.domain,
            is_primary=True,
            is_verified=True,
        )
        session.add(domain_record)
        await session.flush()
    elif existing_domain.tenant_id != tenant.id:
        raise HTTPException(
            status_code=409,
            detail=f"Domain '{data.domain}' belongs to a different tenant",
        )

    validate_schema_name(schema)
    try:
        await session.execute(text(f"SET search_path TO {schema}, public"))

        result = await session.exec(select(User).where(User.email == data.email))
        if result.first() is not None:
            raise HTTPException(status_code=409, detail="Email already registered in this tenant")

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            user_type="admin",
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.flush()

        result = await session.exec(select(Role).where(Role.slug == "admin"))
        admin_role = result.first()
        if admin_role is None:
            raise HTTPException(status_code=500, detail="Admin role not found — run tenant provisioning first")

        user_role = UserRole(user_id=user.id, role_id=admin_role.id)
        session.add(user_role)

        await session.commit()
    finally:
        await session.execute(text("SET search_path TO public"))

    return BootstrapAdminResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        domain=data.domain,
        roles=["admin"],
    )
