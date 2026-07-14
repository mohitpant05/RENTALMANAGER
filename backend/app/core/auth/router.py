import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings
from app.core.auth.dependencies import get_current_user, require_permission
from app.core.auth.jwt import decode_token, revoke_refresh_token
from app.core.auth.models import User
from app.core.auth.schemas import (
    AcceptInviteRequest,
    ChangePasswordRequest,
    CustomerLookupResponse,
    ForgotPasswordRequest,
    LoginRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    RequestEmailChangeRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailChangeRequest,
    VerifyInviteResponse,
)
from app.core.auth.service import (
    accept_invite,
    authenticate_user,
    build_user_response,
    change_password,
    complete_password_reset,
    create_tokens,
    get_user_roles,
    initiate_password_reset,
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
    from app.core.auth.dependencies import get_user_permissions

    roles = await get_user_roles(session, str(user.id))
    if user.user_type == "admin":
        perms = ["*:*:*"]
    else:
        perms = list(await get_user_permissions(session, user.id))
    return build_user_response(user, roles, perms)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    from app.core.auth.dependencies import get_user_permissions

    updated = await update_profile(session, user, data)
    roles = await get_user_roles(session, str(updated.id))
    if updated.user_type == "admin":
        perms = ["*:*:*"]
    else:
        perms = list(await get_user_permissions(session, updated.id))
    return build_user_response(updated, roles, perms)


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


@router.post("/change-password")
async def change_password_endpoint(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await change_password(session, user, data.current_password, data.new_password)
    return {"detail": "Password changed"}


@router.post("/request-email-change")
@limiter.limit("5/minute")
async def request_email_change(
    request: Request,
    data: RequestEmailChangeRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    import secrets

    from app.core.auth.password import verify_password
    from app.core.email.send import send_email
    from app.core.email.templates import email_change_otp_email
    from app.redis_client import get_redis

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect password")

    existing = await session.exec(
        select(User).where(User.email == data.new_email, User.id != user.id)
    )
    if existing.first():
        raise HTTPException(status_code=400, detail="Email already in use")

    otp = "".join(secrets.choice("0123456789") for _ in range(6))
    r = get_redis()
    key = f"email_change:{user.id}"
    await r.setex(key, 600, f"{data.new_email}:{otp}")

    send_email(
        data.new_email,
        "Verify your new email address",
        email_change_otp_email(user.full_name, otp),
    )
    return {"detail": "Verification code sent to new email"}


@router.post("/verify-email-change", response_model=UserResponse)
async def verify_email_change(
    data: VerifyEmailChangeRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    from app.core.auth.dependencies import get_user_permissions

    from app.redis_client import get_redis

    r = get_redis()
    key = f"email_change:{user.id}"
    stored = await r.get(key)
    if not stored:
        raise HTTPException(status_code=400, detail="No pending email change or code expired")

    new_email, stored_otp = stored.rsplit(":", 1)
    if data.otp != stored_otp:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    existing = await session.exec(
        select(User).where(User.email == new_email, User.id != user.id)
    )
    if existing.first():
        raise HTTPException(status_code=400, detail="Email already in use")

    user.email = new_email
    session.add(user)
    await session.commit()
    await session.refresh(user)
    await r.delete(key)

    roles = await get_user_roles(session, str(user.id))
    if user.user_type == "admin":
        perms = ["*:*:*"]
    else:
        perms = list(await get_user_permissions(session, user.id))
    return build_user_response(user, roles, perms)


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_db),
):
    tenant_ctx = get_current_tenant()
    tenant_id = str(tenant_ctx.tenant.id)
    await initiate_password_reset(session, data.email, tenant_id, settings.frontend_url)
    return {"detail": "If that email exists, a reset link has been sent"}


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    session: AsyncSession = Depends(get_db),
):
    await complete_password_reset(session, data.token, data.new_password)
    return {"detail": "Password has been reset"}


@router.get("/users/lookup", response_model=CustomerLookupResponse)
async def lookup_customer(
    email: str,
    user: User = Depends(require_permission("bookings:*:create_on_behalf")),
    session: AsyncSession = Depends(get_db),
):
    result = await session.exec(select(User).where(User.email == email))
    found = result.first()
    if not found:
        raise HTTPException(status_code=404, detail="Customer not found")
    return CustomerLookupResponse(
        id=found.id,
        email=found.email,
        full_name=found.full_name,
        phone=found.phone,
    )
