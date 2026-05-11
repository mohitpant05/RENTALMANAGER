import uuid

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.admin.schemas import (
    DeactivationImpactResponse,
    DomainCreate,
    DomainResponse,
    StaffInvite,
    StaffUserResponse,
    TenantConfigUpdate,
    TenantResponse,
    ThemeResponse,
    ThemeUpdate,
)
from app.core.admin.service import (
    activate_user,
    add_domain,
    deactivate_user,
    get_deactivation_impact,
    get_theme,
    invite_staff,
    list_domains,
    list_staff,
    remove_domain,
    update_tenant_config,
    update_theme,
)
from app.core.auth.dependencies import require_permission
from app.core.auth.models import User
from app.core.tenancy.context import get_current_tenant
from app.database import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin():
    return require_permission("*:*:*")


@router.get("/tenant", response_model=TenantResponse)
async def get_tenant_info(user: User = Depends(_require_admin())):
    ctx = get_current_tenant()
    return TenantResponse.from_tenant(ctx.tenant)


@router.patch("/tenant", response_model=TenantResponse)
async def patch_tenant(
    data: TenantConfigUpdate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(_require_admin()),
):
    ctx = get_current_tenant()
    tenant = await update_tenant_config(
        session,
        ctx.tenant,
        name=data.name,
        base_currency=data.base_currency,
        tz=data.timezone,
        config=data.config,
    )
    return TenantResponse.from_tenant(tenant)


@router.get("/theme", response_model=ThemeResponse)
async def get_tenant_theme(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(_require_admin()),
):
    ctx = get_current_tenant()
    theme = await get_theme(session, ctx.tenant.id)
    return ThemeResponse.model_validate(theme)


@router.put("/theme", response_model=ThemeResponse)
async def update_tenant_theme(
    data: ThemeUpdate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(_require_admin()),
):
    ctx = get_current_tenant()
    theme = await update_theme(session, ctx.tenant.id, data)
    return ThemeResponse.model_validate(theme)


@router.get("/domains", response_model=list[DomainResponse])
async def list_tenant_domains(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(_require_admin()),
):
    ctx = get_current_tenant()
    domains = await list_domains(session, ctx.tenant.id)
    return [DomainResponse.model_validate(d) for d in domains]


@router.post("/domains", response_model=DomainResponse, status_code=201)
async def add_tenant_domain(
    data: DomainCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(_require_admin()),
):
    ctx = get_current_tenant()
    domain = await add_domain(session, ctx.tenant.id, data)
    return DomainResponse.model_validate(domain)


@router.delete("/domains/{domain_id}", status_code=204)
async def delete_tenant_domain(
    domain_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(_require_admin()),
):
    ctx = get_current_tenant()
    await remove_domain(session, ctx.tenant.id, domain_id)


@router.get("/staff", response_model=list[StaffUserResponse])
async def list_tenant_staff(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(_require_admin()),
):
    staff = await list_staff(session)
    return [StaffUserResponse(**s) for s in staff]


@router.post("/staff", response_model=StaffUserResponse, status_code=201)
async def invite_tenant_staff(
    data: StaffInvite,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(_require_admin()),
):
    tenant_ctx = get_current_tenant()
    new_user = await invite_staff(
        session, data,
        tenant_id=str(tenant_ctx.tenant.id),
        tenant_slug=tenant_ctx.tenant.slug,
    )
    return StaffUserResponse.model_validate(new_user)


@router.post("/staff/{user_id}/deactivate", response_model=StaffUserResponse)
async def deactivate_staff(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(_require_admin()),
):
    deactivated = await deactivate_user(session, user_id)
    return StaffUserResponse.model_validate(deactivated)


@router.post("/staff/{user_id}/activate", response_model=StaffUserResponse)
async def activate_staff(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(_require_admin()),
):
    activated = await activate_user(session, user_id)
    return StaffUserResponse.model_validate(activated)


@router.get("/staff/{user_id}/deactivation-impact", response_model=DeactivationImpactResponse)
async def staff_deactivation_impact(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_admin()),
):
    return await get_deactivation_impact(session, user_id)
