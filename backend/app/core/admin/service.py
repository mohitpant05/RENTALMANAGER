import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.admin.models import TenantTheme
from app.core.admin.schemas import (
    DeactivationImpactResponse,
    DomainCreate,
    StaffInvite,
    ThemeUpdate,
)
from app.core.auth.models import Role, User, UserRole
from app.core.tenancy.models import Tenant, TenantDomain


async def get_theme(session: AsyncSession, tenant_id: uuid.UUID) -> TenantTheme:
    result = await session.exec(
        select(TenantTheme).where(TenantTheme.tenant_id == tenant_id)
    )
    theme = result.first()
    if theme is None:
        theme = TenantTheme(tenant_id=tenant_id)
        session.add(theme)
        await session.commit()
        await session.refresh(theme)
    return theme


async def update_theme(
    session: AsyncSession, tenant_id: uuid.UUID, data: ThemeUpdate
) -> TenantTheme:
    theme = await get_theme(session, tenant_id)
    if data.brand is not None:
        theme.brand = data.brand
    if data.colors is not None:
        theme.colors = data.colors
    if data.typography is not None:
        theme.typography = data.typography
    if data.components is not None:
        theme.components = data.components
    if data.features is not None:
        theme.features = data.features
    theme.updated_at = datetime.now(UTC)
    session.add(theme)
    await session.commit()
    await session.refresh(theme)
    return theme


async def update_tenant_config(
    session: AsyncSession,
    tenant: Tenant,
    name: str | None = None,
    base_currency: str | None = None,
    tz: str | None = None,
    config: dict | None = None,
) -> Tenant:
    if name is not None:
        tenant.name = name
    if base_currency is not None:
        tenant.base_currency = base_currency
    if tz is not None:
        tenant.timezone = tz
    if config is not None:
        from app.core.admin.schemas import SENSITIVE_CONFIG_KEYS
        existing = tenant.config or {}
        for k, v in config.items():
            if k in SENSITIVE_CONFIG_KEYS and isinstance(v, str) and v.startswith("••••"):
                continue
            existing[k] = v
        tenant.config = existing
    tenant.updated_at = datetime.now(UTC)
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def list_domains(
    session: AsyncSession, tenant_id: uuid.UUID
) -> list[TenantDomain]:
    result = await session.exec(
        select(TenantDomain).where(TenantDomain.tenant_id == tenant_id)
    )
    return list(result.all())


async def add_domain(
    session: AsyncSession, tenant_id: uuid.UUID, data: DomainCreate
) -> TenantDomain:
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
    return domain


async def remove_domain(
    session: AsyncSession, tenant_id: uuid.UUID, domain_id: uuid.UUID
) -> None:
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


async def list_staff(session: AsyncSession) -> list[dict]:
    result = await session.exec(
        select(User).where(User.user_type.in_(["admin", "staff"]))
    )
    users = list(result.all())
    staff_list = []
    for u in users:
        roles_result = await session.exec(
            select(Role.slug)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == u.id)
        )
        roles = list(roles_result.all())
        staff_list.append({**u.model_dump(), "roles": roles})
    return staff_list


async def invite_staff(
    session: AsyncSession, data: StaffInvite, tenant_id: str, tenant_slug: str
) -> User:
    result = await session.exec(select(User).where(User.email == data.email))
    existing = result.first()

    if existing is not None:
        if existing.is_active:
            raise HTTPException(status_code=409, detail="User already active")
        user = existing
        from app.core.auth.invite import delete_user_invite_tokens
        await delete_user_invite_tokens(str(user.id))
    else:
        user = User(
            email=data.email,
            password_hash=None,
            full_name=data.full_name,
            user_type=data.user_type,
            is_active=False,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        for slug in data.role_slugs:
            role_result = await session.exec(select(Role).where(Role.slug == slug))
            role = role_result.first()
            if role is not None:
                user_role = UserRole(user_id=user.id, role_id=role.id)
                session.add(user_role)
        await session.commit()

    import uuid as _uuid

    from app.config import get_settings
    from app.core.auth.invite import store_invite_token
    from app.core.email.send import send_email

    token = str(_uuid.uuid4())
    await store_invite_token(token, str(user.id), tenant_id)

    settings = get_settings()
    invite_link = f"{settings.frontend_url}/t/{tenant_slug}/accept-invite?token={token}"
    subject = "You've been invited to RentManager"
    body = (
        f"Hi {user.full_name},\n\n"
        f"You've been invited to join as {user.user_type}.\n\n"
        f"Click the link below to set your password and activate your account:\n"
        f"{invite_link}\n\n"
        f"This link expires in {settings.invite_token_expire_hours} hours."
    )
    send_email(user.email, subject, body)

    return user


async def deactivate_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    result = await session.exec(select(User).where(User.id == user_id))
    user = result.first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    user.updated_at = datetime.now(UTC)
    session.add(user)

    from app.domains.bookings.models import Booking
    from app.domains.resources.models import Resource

    resource_result = await session.exec(
        select(Resource).where(
            Resource.owner_id == user_id, Resource.status == "active"
        )
    )
    resources = list(resource_result.all())
    resource_ids = []
    for r in resources:
        r.status = "suspended"
        r.suspension_reason = "owner_deactivated"
        session.add(r)
        resource_ids.append(r.id)

    if resource_ids:
        booking_result = await session.exec(
            select(Booking).where(
                Booking.resource_id.in_(resource_ids),
                Booking.status == "pending",
            )
        )
        for booking in booking_result.all():
            booking.status = "rejected"
            booking.cancellation_reason = "Resource owner deactivated"
            booking.updated_at = datetime.now(UTC)
            booking.version += 1
            session.add(booking)

    await session.commit()
    await session.refresh(user)
    return user


async def activate_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    result = await session.exec(select(User).where(User.id == user_id))
    user = result.first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    user.updated_at = datetime.now(UTC)
    session.add(user)

    from app.domains.resources.models import Resource

    resource_result = await session.exec(
        select(Resource).where(
            Resource.owner_id == user_id,
            Resource.suspension_reason == "owner_deactivated",
        )
    )
    for r in resource_result.all():
        r.status = "active"
        r.suspension_reason = None
        session.add(r)

    await session.commit()
    await session.refresh(user)
    return user


async def get_deactivation_impact(
    session: AsyncSession, user_id: uuid.UUID
) -> DeactivationImpactResponse:
    from app.domains.bookings.models import Booking
    from app.domains.resources.models import Resource

    resource_result = await session.exec(
        select(Resource).where(
            Resource.owner_id == user_id, Resource.status == "active"
        )
    )
    resources = list(resource_result.all())
    resource_ids = [r.id for r in resources]

    pending_count = 0
    if resource_ids:
        from sqlmodel import func
        count_result = await session.exec(
            select(func.count(Booking.id)).where(
                Booking.resource_id.in_(resource_ids),
                Booking.status == "pending",
            )
        )
        pending_count = count_result.one()

    return DeactivationImpactResponse(
        resources_count=len(resources),
        pending_bookings_count=pending_count,
    )
