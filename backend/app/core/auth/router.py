import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings
from app.core.auth.dependencies import get_current_user
from app.core.auth.jwt import decode_token, revoke_refresh_token
from app.core.auth.models import User
from app.core.auth.schemas import (
    AcceptInviteRequest,
    LoginRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    VerifyInviteResponse,
)
from app.core.auth.service import (
    accept_invite,
    authenticate_user,
    build_user_response,
    create_tokens,
    get_user_roles,
    refresh_tokens,
    register_user,
    update_profile,
    verify_invite_token,
)
from app.core.tenancy.context import get_current_tenant
from app.database import get_db
from app.rate_limiter import limiter

settings = get_settings()

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/verify-invite", response_model=VerifyInviteResponse)
async def verify_invite(
    token: str,
    session: AsyncSession = Depends(get_db),
):
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        return VerifyInviteResponse(valid=False)
    tenant_id = str(tenant_ctx.tenant.id)
    result = await verify_invite_token(token, tenant_id, session)
    return VerifyInviteResponse(**result)


@router.post("/accept-invite", response_model=TokenResponse)
async def accept_invite_endpoint(
    data: AcceptInviteRequest,
    session: AsyncSession = Depends(get_db),
):
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        raise HTTPException(status_code=400, detail="Invalid or expired invite")
    tenant_id = str(tenant_ctx.tenant.id)
    user, roles = await accept_invite(data.token, data.password, tenant_id, session)
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


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit(settings.register_rate_limit)
async def register(
    request: Request,
    data: RegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    tenant_ctx = get_current_tenant()
    tenant_id = str(tenant_ctx.tenant.id)
    user = await register_user(session, data, tenant_id, user_type="customer")
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


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    updated = await update_profile(session, user, data)
    roles = await get_user_roles(session, str(updated.id))
    return build_user_response(updated, roles)


@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    result = await session.exec(select(User).where(User.id == user_id))
    user = result.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    roles = await get_user_roles(session, str(user.id))
    return build_user_response(user, roles)
