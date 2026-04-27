from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.auth.models import Permission, Role, RolePermission

DEFAULT_PERMISSIONS = [
    ("resources:*:read", "Read all resources"),
    ("resources:*:manage", "Manage all resources"),
    ("resources:*:create", "Create resources"),
    ("resources:*:delete", "Delete resources"),
    ("bookings:*:read", "Read all bookings"),
    ("bookings:*:create", "Create bookings"),
    ("bookings:*:manage", "Manage all bookings"),
    ("bookings:*:cancel", "Cancel any booking"),
    ("reviews:*:read", "Read reviews"),
    ("reviews:*:create", "Create reviews"),
    ("reviews:*:moderate", "Moderate reviews"),
    ("staff:*:invite", "Invite staff members"),
    ("staff:*:manage", "Manage staff"),
    ("pricing:*:read", "Read pricing rules"),
    ("pricing:*:configure", "Configure pricing"),
    ("theme:*:read", "Read theme config"),
    ("theme:*:edit", "Edit theme"),
    ("analytics:*:read", "Read analytics"),
    ("settings:*:manage", "Manage tenant settings"),
]

DEFAULT_ROLES = {
    "admin": {
        "name": "Admin",
        "description": "Full tenant administration",
        "permissions": ["*:*:*"],
    },
    "staff": {
        "name": "Staff",
        "description": "Tenant staff with configurable permissions",
        "permissions": [
            "resources:*:read",
            "resources:*:manage",
            "bookings:*:read",
            "bookings:*:manage",
            "reviews:*:read",
            "reviews:*:moderate",
            "pricing:*:read",
            "analytics:*:read",
        ],
    },
    "customer": {
        "name": "Customer",
        "description": "Books resources and leaves reviews",
        "permissions": [
            "resources:*:read",
            "bookings:*:create",
            "bookings:*:read",
            "reviews:*:read",
            "reviews:*:create",
        ],
    },
    "lister": {
        "name": "Lister",
        "description": "Lists resources for rent",
        "permissions": [
            "resources:*:read",
            "resources:*:create",
            "resources:*:manage",
            "bookings:*:read",
            "bookings:*:manage",
            "reviews:*:read",
            "pricing:*:read",
        ],
    },
}


async def seed_default_roles(session: AsyncSession) -> None:
    perm_map: dict[str, Permission] = {}
    all_codenames = {code for code, _ in DEFAULT_PERMISSIONS}
    all_codenames.add("*:*:*")

    for codename, description in [*DEFAULT_PERMISSIONS, ("*:*:*", "Superuser — all permissions")]:
        result = await session.exec(
            select(Permission).where(Permission.codename == codename)
        )
        existing = result.first()
        if existing:
            perm_map[codename] = existing
        else:
            perm = Permission(codename=codename, description=description)
            session.add(perm)
            perm_map[codename] = perm

    await session.flush()

    for slug, config in DEFAULT_ROLES.items():
        result = await session.exec(select(Role).where(Role.slug == slug))
        existing_role = result.first()
        if existing_role:
            continue

        role = Role(
            name=config["name"],
            slug=slug,
            description=config["description"],
            is_system=True,
        )
        session.add(role)
        await session.flush()

        for perm_codename in config["permissions"]:
            perm = perm_map.get(perm_codename)
            if perm:
                rp = RolePermission(role_id=role.id, permission_id=perm.id)
                session.add(rp)

    await session.commit()
