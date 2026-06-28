import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.admin.schemas import (
    CustomerCreate,
    CustomerResponse,
    DeactivationImpactResponse,
    DomainCreate,
    DomainResponse,
    ResetPasswordRequest,
    StaffInvite,
    StaffInviteResponse,
    StaffUserResponse,
    TenantConfigUpdate,
    TenantResponse,
    TestEmailRequest,
    ThemeResponse,
    ThemeUpdate,
)
from app.core.admin.service import (
    activate_customer,
    activate_user,
    add_domain,
    create_customer,
    deactivate_customer,
    deactivate_user,
    delete_staff,
    get_deactivation_impact,
    reset_staff_password,
    get_theme,
    invite_staff,
    list_customers,
    list_domains,
    list_staff,
    remove_domain,
    update_tenant_config,
    update_theme,
)
from app.core.auth.dependencies import require_permission
from app.core.auth.models import User
from app.core.auth.scoping import resolve_data_scope
from app.core.tenancy.context import get_current_tenant
from app.database import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/tenant", response_model=TenantResponse)
async def get_tenant_info(user: User = Depends(require_permission("settings:*:manage"))):
    ctx = get_current_tenant()
    return TenantResponse.from_tenant(ctx.tenant)


@router.patch("/tenant", response_model=TenantResponse)
async def patch_tenant(
    data: TenantConfigUpdate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("settings:*:manage")),
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
    user: User = Depends(require_permission("theme:*:read")),
):
    ctx = get_current_tenant()
    theme = await get_theme(session, ctx.tenant.id)
    return ThemeResponse.model_validate(theme)


@router.put("/theme", response_model=ThemeResponse)
async def update_tenant_theme(
    data: ThemeUpdate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("theme:*:edit")),
):
    ctx = get_current_tenant()
    theme = await update_theme(session, ctx.tenant.id, data)
    return ThemeResponse.model_validate(theme)


@router.get("/domains", response_model=list[DomainResponse])
async def list_tenant_domains(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("settings:*:manage")),
):
    ctx = get_current_tenant()
    domains = await list_domains(session, ctx.tenant.id)
    return [DomainResponse.model_validate(d) for d in domains]


@router.post("/domains", response_model=DomainResponse, status_code=201)
async def add_tenant_domain(
    data: DomainCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("settings:*:manage")),
):
    ctx = get_current_tenant()
    domain = await add_domain(session, ctx.tenant.id, data)
    return DomainResponse.model_validate(domain)


@router.delete("/domains/{domain_id}", status_code=204)
async def delete_tenant_domain(
    domain_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("settings:*:manage")),
):
    ctx = get_current_tenant()
    await remove_domain(session, ctx.tenant.id, domain_id)


@router.post("/email/test")
async def test_email(
    data: TestEmailRequest,
    user: User = Depends(require_permission("settings:*:manage")),
):
    from app.core.email.factory import get_email_provider, get_email_provider_from_config

    ctx = get_current_tenant()
    config = ctx.tenant.config or {}
    provider = None
    if config.get("smtp_provider"):
        provider = get_email_provider_from_config(config)
    if provider is None:
        provider = get_email_provider()
    if provider is None:
        raise HTTPException(status_code=400, detail="No email provider configured")
    try:
        provider.send(
            data.to,
            "RentManager — Test Email",
            "This is a test email from RentManager.\n\nYour SMTP configuration is working correctly.",
        )
        return {"status": "sent"}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Email send failed: {exc}")


@router.get("/staff", response_model=list[StaffUserResponse])
async def list_tenant_staff(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("staff:*:manage")),
):
    staff = await list_staff(session)
    return [StaffUserResponse(**s) for s in staff]


@router.post("/staff", response_model=StaffInviteResponse, status_code=201)
async def invite_tenant_staff(
    data: StaffInvite,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("staff:*:invite")),
):
    from app.core.notifications.events import EMAIL_FAILED, STAFF_INVITED
    from app.core.notifications.service import notify

    if user.user_type != "admin":
        if data.user_type == "admin":
            raise HTTPException(
                status_code=403, detail="Only admins can create admin users"
            )
        if data.role_slugs:
            from app.core.admin.roles_service import get_user_role_slugs
            caller_roles = await get_user_role_slugs(session, user.id)
            disallowed = set(data.role_slugs) - caller_roles
            if disallowed:
                raise HTTPException(
                    status_code=403,
                    detail=f"Cannot assign roles you don't hold: {', '.join(disallowed)}",
                )

    tenant_ctx = get_current_tenant()
    new_user, email_status, email_warning = await invite_staff(
        session, data,
        tenant_id=str(tenant_ctx.tenant.id),
        tenant_slug=tenant_ctx.tenant.slug,
    )

    if email_status == "not_configured":
        await notify(
            session, user.id, EMAIL_FAILED,
            "Invite email not sent",
            f"No email provider configured. Staff member {new_user.full_name} ({new_user.email}) "
            f"was created but the invite email could not be sent. "
            f"Configure SMTP in Settings → Email / SMTP.",
            {"staff_email": new_user.email, "staff_id": str(new_user.id)},
        )
    else:
        await notify(
            session, user.id, STAFF_INVITED,
            "Staff invited",
            f"Invite email queued for {new_user.full_name} ({new_user.email}).",
            {"staff_email": new_user.email, "staff_id": str(new_user.id)},
        )

    resp = StaffInviteResponse.model_validate(new_user)
    resp.email_status = email_status
    resp.email_warning = email_warning
    return resp


@router.post("/staff/{user_id}/deactivate", response_model=StaffUserResponse)
async def deactivate_staff(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("staff:*:manage")),
):
    deactivated = await deactivate_user(session, user_id)
    return StaffUserResponse.model_validate(deactivated)


@router.post("/staff/{user_id}/activate", response_model=StaffUserResponse)
async def activate_staff(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("staff:*:manage")),
):
    activated = await activate_user(session, user_id)
    return StaffUserResponse.model_validate(activated)


@router.get("/staff/{user_id}/deactivation-impact", response_model=DeactivationImpactResponse)
async def staff_deactivation_impact(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("staff:*:manage")),
):
    return await get_deactivation_impact(session, user_id)


@router.delete("/staff/{user_id}", status_code=204)
async def remove_staff(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("staff:*:manage")),
):
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    await delete_staff(session, user_id)


@router.post("/staff/{user_id}/reset-password", response_model=StaffUserResponse)
async def reset_staff_password_endpoint(
    user_id: uuid.UUID,
    data: ResetPasswordRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("staff:*:manage")),
):
    updated = await reset_staff_password(session, user_id, data.new_password)
    return StaffUserResponse.model_validate(updated)


# --- Customer endpoints ---

@router.get("/customers", response_model=list[CustomerResponse])
async def list_tenant_customers(
    search: str | None = None,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("customers:*:read")),
):
    scope = await resolve_data_scope(session, user)
    scope_owner_ids = scope.owner_ids if scope.is_scoped else None
    customers = await list_customers(session, search, scope_owner_ids=scope_owner_ids)
    return [CustomerResponse(**c) for c in customers]


@router.post("/customers", response_model=CustomerResponse, status_code=201)
async def create_tenant_customer(
    data: CustomerCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("customers:*:create")),
):
    customer = await create_customer(session, data)
    return CustomerResponse(**{**customer.model_dump(), "booking_count": 0})


@router.post("/customers/{customer_id}/deactivate", response_model=CustomerResponse)
async def deactivate_tenant_customer(
    customer_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("customers:*:deactivate")),
):
    customer = await deactivate_customer(session, customer_id)
    return CustomerResponse(**{**customer.model_dump(), "booking_count": 0})


@router.post("/customers/{customer_id}/activate", response_model=CustomerResponse)
async def activate_tenant_customer(
    customer_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("customers:*:manage")),
):
    customer = await activate_customer(session, customer_id)
    return CustomerResponse(**{**customer.model_dump(), "booking_count": 0})
