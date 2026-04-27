from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.auth.models import User
from app.core.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.core.auth.service import (
    authenticate_user,
    build_user_response,
    create_tokens,
    get_user_roles,
    refresh_tokens,
    register_user,
)
from app.core.auth.jwt import decode_token, revoke_refresh_token
from app.core.tenancy.context import get_current_tenant
from app.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    tenant_ctx = get_current_tenant()
    tenant_id = str(tenant_ctx.tenant.id)
    user = await register_user(session, data, tenant_id=tenant_id)
    roles = await get_user_roles(session, str(user.id))
    return await create_tokens(user, tenant_id, roles)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_db),
):
    tenant_ctx = get_current_tenant()
    tenant_id = str(tenant_ctx.tenant.id)
    user = await authenticate_user(session, data)
    roles = await get_user_roles(session, str(user.id))
    return await create_tokens(user, tenant_id, roles)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    session: AsyncSession = Depends(get_db),
):
    return await refresh_tokens(session, data)


@router.post("/logout")
async def logout(
    data: RefreshRequest,
    user: User = Depends(get_current_user),
):
    try:
        payload = decode_token(data.refresh_token)
        jti = payload.get("jti")
        if jti:
            await revoke_refresh_token(jti)
    except Exception:
        pass
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    roles = await get_user_roles(session, str(user.id))
    return build_user_response(user, roles)
