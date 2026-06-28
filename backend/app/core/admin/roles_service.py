import uuid
from collections import defaultdict

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.admin.roles_schemas import (
    PermissionGroup,
    PermissionResponse,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
)
from app.core.auth.models import Permission, Role, RolePermission, UserPermissionOverride, UserRole

DOMAIN_LABELS = {
    "resources": "Resources",
    "bookings": "Bookings",
    "reviews": "Reviews",
    "staff": "Staff",
    "pricing": "Pricing",
    "theme": "Theming",
    "analytics": "Analytics",
    "settings": "Settings",
    "resource_types": "Resource Types",
}


async def _build_role_response(session: AsyncSession, role: Role) -> RoleResponse:
    result = await session.exec(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role.id)
    )
    perms = [PermissionResponse.from_permission(p) for p in result.all()]
    resp = RoleResponse.model_validate(role)
    resp.permissions = perms
    return resp


async def list_roles(session: AsyncSession) -> list[RoleResponse]:
    result = await session.exec(select(Role).order_by(Role.name))
    roles = list(result.all())
    return [await _build_role_response(session, r) for r in roles]


async def get_role(session: AsyncSession, role_id: uuid.UUID) -> RoleResponse:
    result = await session.exec(select(Role).where(Role.id == role_id))
    role = result.first()
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return await _build_role_response(session, role)


async def create_role(session: AsyncSession, data: RoleCreate) -> RoleResponse:
    result = await session.exec(select(Role).where(Role.slug == data.slug))
    if result.first() is not None:
        raise HTTPException(status_code=409, detail="Role slug already exists")
    role = Role(
        name=data.name,
        slug=data.slug,
        description=data.description,
        is_system=False,
    )
    session.add(role)
    await session.commit()
    await session.refresh(role)
    return await _build_role_response(session, role)


async def update_role(
    session: AsyncSession, role_id: uuid.UUID, data: RoleUpdate
) -> RoleResponse:
    result = await session.exec(select(Role).where(Role.id == role_id))
    role = result.first()
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    if data.name is not None:
        role.name = data.name
    if data.description is not None:
        role.description = data.description
    session.add(role)
    await session.commit()
    await session.refresh(role)
    return await _build_role_response(session, role)


async def delete_role(session: AsyncSession, role_id: uuid.UUID) -> None:
    result = await session.exec(select(Role).where(Role.id == role_id))
    role = result.first()
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    if role.is_system:
        raise HTTPException(status_code=409, detail="Cannot delete system role")

    rp_result = await session.exec(
        select(RolePermission).where(RolePermission.role_id == role_id)
    )
    for rp in rp_result.all():
        await session.delete(rp)

    ur_result = await session.exec(
        select(UserRole).where(UserRole.role_id == role_id)
    )
    for ur in ur_result.all():
        await session.delete(ur)

    await session.delete(role)
    await session.commit()


async def set_role_permissions(
    session: AsyncSession, role_id: uuid.UUID, permission_ids: list[uuid.UUID]
) -> RoleResponse:
    result = await session.exec(select(Role).where(Role.id == role_id))
    role = result.first()
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")

    existing = await session.exec(
        select(RolePermission).where(RolePermission.role_id == role_id)
    )
    for rp in existing.all():
        await session.delete(rp)
    await session.flush()

    for pid in permission_ids:
        session.add(RolePermission(role_id=role_id, permission_id=pid))
    await session.commit()

    return await _build_role_response(session, role)


async def list_permissions_grouped(session: AsyncSession) -> list[PermissionGroup]:
    result = await session.exec(
        select(Permission).where(Permission.codename != "*:*:*").order_by(Permission.codename)
    )
    perms = result.all()

    groups: dict[str, list[PermissionResponse]] = defaultdict(list)
    for p in perms:
        resp = PermissionResponse.from_permission(p)
        groups[resp.domain].append(resp)

    return [
        PermissionGroup(
            domain=domain,
            label=DOMAIN_LABELS.get(domain, domain.capitalize()),
            permissions=perm_list,
        )
        for domain, perm_list in groups.items()
    ]


async def get_user_role_ids(session: AsyncSession, user_id: uuid.UUID) -> set[uuid.UUID]:
    result = await session.exec(
        select(UserRole.role_id).where(UserRole.user_id == user_id)
    )
    return set(result.all())


async def get_user_role_slugs(session: AsyncSession, user_id: uuid.UUID) -> set[str]:
    result = await session.exec(
        select(Role.slug)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    return set(result.all())


async def update_staff_roles(
    session: AsyncSession,
    user_id: uuid.UUID,
    role_ids: list[uuid.UUID],
    acting_user: "User | None" = None,
) -> None:
    from app.core.auth.models import User

    user_result = await session.exec(select(User).where(User.id == user_id))
    user = user_result.first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if acting_user and acting_user.user_type != "admin":
        allowed_role_ids = await get_user_role_ids(session, acting_user.id)
        requested = set(role_ids)
        disallowed = requested - allowed_role_ids
        if disallowed:
            slugs_result = await session.exec(
                select(Role.slug).where(Role.id.in_(disallowed))
            )
            bad_slugs = list(slugs_result.all())
            raise HTTPException(
                status_code=403,
                detail=f"Cannot assign roles you don't hold: {', '.join(bad_slugs)}",
            )

    existing = await session.exec(
        select(UserRole).where(UserRole.user_id == user_id)
    )
    for ur in existing.all():
        await session.delete(ur)
    await session.flush()

    for rid in role_ids:
        session.add(UserRole(user_id=user_id, role_id=rid))
    await session.commit()


async def get_staff_effective_permissions(
    session: AsyncSession, user_id: uuid.UUID
) -> dict:
    from app.core.admin.roles_schemas import PermissionOverrideResponse, PermissionResponse

    rp_result = await session.exec(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
    )
    role_perms = [PermissionResponse.from_permission(p) for p in rp_result.all()]

    override_result = await session.exec(
        select(UserPermissionOverride, Permission)
        .join(Permission, Permission.id == UserPermissionOverride.permission_id)
        .where(UserPermissionOverride.user_id == user_id)
    )
    overrides = []
    for ov, perm in override_result.all():
        overrides.append(PermissionOverrideResponse(
            permission_id=perm.id,
            codename=perm.codename,
            description=perm.description,
            granted=ov.granted,
        ))

    from app.core.auth.dependencies import get_user_permissions
    effective = await get_user_permissions(session, user_id)

    return {
        "role_permissions": role_perms,
        "overrides": overrides,
        "effective": sorted(effective),
    }


async def set_staff_permission_overrides(
    session: AsyncSession, user_id: uuid.UUID, overrides: list
) -> None:
    perm_ids = [entry.permission_id for entry in overrides]
    if perm_ids:
        result = await session.exec(
            select(Permission.id).where(Permission.id.in_(perm_ids))
        )
        valid_ids = set(result.all())
        for pid in perm_ids:
            if pid not in valid_ids:
                raise HTTPException(status_code=404, detail=f"Permission {pid} not found")

    existing = await session.exec(
        select(UserPermissionOverride).where(UserPermissionOverride.user_id == user_id)
    )
    for ov in existing.all():
        await session.delete(ov)
    await session.flush()

    for entry in overrides:
        session.add(UserPermissionOverride(
            user_id=user_id,
            permission_id=entry.permission_id,
            granted=entry.granted,
        ))
    await session.commit()
