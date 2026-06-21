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
from app.core.auth.models import Permission, Role, RolePermission, UserRole

DOMAIN_LABELS = {
    "resources": "Resources",
    "bookings": "Bookings",
    "reviews": "Reviews",
    "staff": "Staff",
    "pricing": "Pricing",
    "theme": "Theming",
    "analytics": "Analytics",
    "settings": "Settings",
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


async def update_staff_roles(
    session: AsyncSession, user_id: uuid.UUID, role_ids: list[uuid.UUID]
) -> None:
    from app.core.auth.models import User

    user_result = await session.exec(select(User).where(User.id == user_id))
    user = user_result.first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    existing = await session.exec(
        select(UserRole).where(UserRole.user_id == user_id)
    )
    for ur in existing.all():
        await session.delete(ur)
    await session.flush()

    for rid in role_ids:
        session.add(UserRole(user_id=user_id, role_id=rid))
    await session.commit()
