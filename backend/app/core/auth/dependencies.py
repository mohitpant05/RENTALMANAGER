import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.core.auth.jwt import decode_token
from app.core.auth.models import Permission, RolePermission, User, UserRole
from app.core.tenancy.context import get_current_tenant
from app.database import get_db

_security = HTTPBearer()


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
        f"*:*:*",
    ]
    return any(c in granted for c in candidates)


async def get_user_permissions(session: AsyncSession, user_id: uuid.UUID) -> set[str]:
    result = await session.exec(
        select(Permission.codename)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
    )
    return set(result.all())


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    session: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No tenant context",
        )

    if payload.get("tenant_id") != str(tenant_ctx.tenant.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token tenant mismatch",
        )

    user_id = payload.get("sub")
    result = await session.exec(select(User).where(User.id == user_id))
    user = result.first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
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
