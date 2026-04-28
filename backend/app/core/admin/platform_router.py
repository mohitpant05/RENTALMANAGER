import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.admin.platform_auth import (
    authenticate_platform_user,
    create_platform_token,
    get_current_platform_user,
)
from app.core.admin.schemas import (
    PlatformLoginRequest,
    PlatformTokenResponse,
    TenantCreate,
    TenantResponse,
)
from app.core.auth.models import PlatformUser
from app.core.tenancy.models import Tenant
from app.core.tenancy.provisioning import provision_tenant_schema
from app.database import engine, get_session

router = APIRouter(prefix="/api/platform", tags=["platform"])


@router.post("/login", response_model=PlatformTokenResponse)
async def platform_login(
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
