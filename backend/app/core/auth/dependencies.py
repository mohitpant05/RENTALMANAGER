import logging
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.jwt import decode_token
from app.core.auth.models import Permission, RolePermission, User, UserPermissionOverride, UserRole
from app.core.tenancy.context import get_current_tenant
from app.database import get_db

logger = logging.getLogger("app.auth.dependencies")

_security = HTTPBearer()

PERMISSION_SUPERSETS: dict[str, list[str]] = {
    "bookings:*:manage": [
        "bookings:*:confirm",
        "bookings:*:reject",
        "bookings:*:cancel",
        "bookings:*:no_show",
    ],
}


def matches_permission(required: str, granted: set[str]) -> bool:
    if required in granted:
        return True
    parts = required.split(":")
    if len(parts) != 3:
        return False
    domain, qualifier, action = parts
    candidates = [
        f"{domain}:*:{action}",
        f"{domain}:{qualifier}:*",
        f"{domain}:*:*",
        "*:*:*",
    ]
    if any(c in granted for c in candidates):
        return True
    for superset_perm, sub_perms in PERMISSION_SUPERSETS.items():
        if required in sub_perms and matches_permission(superset_perm, granted):
            return True
    return False


async def get_user_permissions(session: AsyncSession, user_id: uuid.UUID) -> set[str]:
    result = await session.exec(
        select(Permission.codename)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
    )
    perms = set(result.all())

    override_result = await session.exec(
        select(Permission.codename, UserPermissionOverride.granted)
        .join(UserPermissionOverride, UserPermissionOverride.permission_id == Permission.id)
        .where(UserPermissionOverride.user_id == user_id)
    )
    for codename, granted in override_result.all():
        if granted:
            perms.add(codename)
        else:
            perms.discard(codename)

    return perms


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    session: AsyncSession = Depends(get_db),
) -> User:
    logger.info("AUTH STEP 1/6: decode token")
    try:
        payload = decode_token(credentials.credentials)
        logger.info("AUTH STEP 1/6 OK — sub=%s tenant_id=%s type=%s exp=%s",
                     payload.get("sub"), payload.get("tenant_id"),
                     payload.get("type"), payload.get("exp"))
    except JWTError as e:
        logger.warning("AUTH STEP 1/6 FAILED — JWT decode error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    logger.info("AUTH STEP 2/6: check token type == 'access'")
    if payload.get("type") != "access":
        logger.warning("AUTH STEP 2/6 FAILED — token type is '%s'", payload.get("type"))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    logger.info("AUTH STEP 2/6 OK")

    logger.info("AUTH STEP 3/6: get tenant context")
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        logger.warning("AUTH STEP 3/6 FAILED — no tenant context (middleware didn't set it)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No tenant context",
        )
    logger.info("AUTH STEP 3/6 OK — tenant.id=%s tenant.slug=%s",
                 tenant_ctx.tenant.id, tenant_ctx.tenant.slug)

    logger.info("AUTH STEP 4/6: check tenant_id match (token=%s vs context=%s)",
                 payload.get("tenant_id"), str(tenant_ctx.tenant.id))
    if payload.get("tenant_id") != str(tenant_ctx.tenant.id):
        logger.warning("AUTH STEP 4/6 FAILED — token tenant_id=%s != context tenant.id=%s",
                        payload.get("tenant_id"), tenant_ctx.tenant.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token tenant mismatch",
        )
    logger.info("AUTH STEP 4/6 OK — tenant match")

    user_id = payload.get("sub")
    logger.info("AUTH STEP 5/6: load user id=%s from DB (search_path=%s)",
                 user_id, tenant_ctx.schema_name)
    result = await session.exec(select(User).where(User.id == user_id))
    user = result.first()
    if user is None:
        logger.warning("AUTH STEP 5/6 FAILED — user %s not found in schema %s",
                        user_id, tenant_ctx.schema_name)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    if not user.is_active:
        logger.warning("AUTH STEP 5/6 FAILED — user %s is inactive", user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    logger.info("AUTH STEP 5/6 OK — user=%s email=%s user_type=%s",
                 user.id, user.email, user.user_type)

    logger.info("AUTH STEP 6/6 — authentication successful, returning user")
    return user


def require_permission(permission: str):
    async def _checker(
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db),
    ) -> User:
        if user.user_type == "admin":
            return user

        user_perms = await get_user_permissions(session, user.id)
        if not matches_permission(permission, user_perms):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _checker


async def get_current_user_with_perms(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    session: AsyncSession = Depends(get_db),
) -> tuple[User, set[str]]:
    user = await get_current_user(credentials, session)
    if user.user_type == "admin":
        return user, {"*:*:*"}
    perms = await get_user_permissions(session, user.id)
    return user, perms


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        HTTPBearer(auto_error=False)
    ),
    session: AsyncSession = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, session)
    except HTTPException:
        return None
