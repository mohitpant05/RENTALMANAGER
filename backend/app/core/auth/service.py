from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.email.send import send_email
from app.core.auth.invite import claim_invite_token, get_invite_data
from app.core.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    is_refresh_token_valid,
    revoke_refresh_token,
    store_refresh_token,
)
from app.core.auth.models import Role, User, UserRole
from app.core.auth.password import hash_password, verify_password
from app.core.auth.schemas import (
    LoginRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.core.email.templates import welcome_email


async def register_user(
    session: AsyncSession,
    data: RegisterRequest,
    tenant_id: str,
    user_type: str = "customer",
) -> User:
    result = await session.exec(select(User).where(User.email == data.email))
    if result.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        user_type=user_type,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    try:
        body = welcome_email(user.full_name)
        send_email(user.email, "Welcome to RentManager", body)
    except Exception:
        pass

    return user


async def authenticate_user(session: AsyncSession, data: LoginRequest) -> User:
    result = await session.exec(select(User).where(User.email == data.email))
    user = result.first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if user.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account pending invite acceptance",
        )
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    user.last_login = datetime.now(UTC)
    session.add(user)
    await session.commit()
    return user


async def get_user_roles(session: AsyncSession, user_id: str) -> list[str]:
    result = await session.exec(
        select(Role.slug)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    return list(result.all())


async def create_tokens(user: User, tenant_id: str, roles: list[str]) -> TokenResponse:
    access_token = create_access_token(
        user_id=str(user.id),
        tenant_id=tenant_id,
        roles=roles,
    )
    refresh_token, jti = create_refresh_token(
        user_id=str(user.id),
        tenant_id=tenant_id,
    )
    await store_refresh_token(jti, str(user.id), tenant_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


async def refresh_tokens(session: AsyncSession, data: RefreshRequest) -> TokenResponse:
    try:
        payload = decode_token(data.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    jti = payload.get("jti")
    if not await is_refresh_token_valid(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked",
        )

    await revoke_refresh_token(jti)

    user_id = payload["sub"]
    tenant_id = payload["tenant_id"]

    result = await session.exec(select(User).where(User.id == user_id))
    user = result.first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    roles = await get_user_roles(session, str(user.id))
    return await create_tokens(user, tenant_id, roles)


async def update_profile(
    session: AsyncSession, user: User, data: ProfileUpdateRequest
) -> User:
    from datetime import datetime

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return user

    for key, value in update_data.items():
        setattr(user, key, value)

    user.updated_at = datetime.now(UTC)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def build_user_response(
    user: User, roles: list[str], permissions: list[str] | None = None
) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        is_active=user.is_active,
        is_verified=user.is_verified,
        user_type=user.user_type,
        avatar_url=user.avatar_url,
        preferred_currency=user.preferred_currency,
        created_at=user.created_at,
        roles=roles,
        permissions=permissions or [],
    )


async def verify_invite_token(token: str, tenant_id: str, session: AsyncSession) -> dict:
    data = await get_invite_data(token)
    if data is None or data["tenant_id"] != tenant_id:
        return {"valid": False}

    result = await session.exec(select(User).where(User.id == data["user_id"]))
    user = result.first()
    if user is None:
        return {"valid": False}

    return {"valid": True, "email": user.email, "full_name": user.full_name}


async def accept_invite(
    token: str, password: str, tenant_id: str, session: AsyncSession
) -> tuple[User, list[str]]:
    data = await claim_invite_token(token)
    if data is None or data["tenant_id"] != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invite",
        )

    result = await session.exec(select(User).where(User.id == data["user_id"]))
    user = result.first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invite",
        )

    user.password_hash = hash_password(password)
    user.is_active = True
    user.is_verified = True
    user.updated_at = datetime.now(UTC)
    session.add(user)
    await session.commit()

    try:
        body = welcome_email(user.full_name)
        send_email(user.email, "Welcome to RentManager", body)
    except Exception:
        pass

    roles = await get_user_roles(session, str(user.id))
    return user, roles


async def change_password(
    session: AsyncSession, user: User, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.now(UTC)
    session.add(user)
    await session.commit()


async def initiate_password_reset(
    session: AsyncSession, email: str, tenant_id: str, frontend_url: str
) -> None:
    import uuid as _uuid
    from app.core.auth.invite import store_reset_token
    from app.core.email.templates import password_reset_email

    result = await session.exec(select(User).where(User.email == email))
    user = result.first()
    if not user or not user.is_active:
        return

    token = str(_uuid.uuid4())
    await store_reset_token(token, str(user.id), tenant_id)
    reset_url = f"{frontend_url}/reset-password?token={token}"
    body = password_reset_email(user.full_name, reset_url)
    try:
        send_email(user.email, "Reset Your Password — RentManager", body)
    except Exception:
        pass


async def complete_password_reset(
    session: AsyncSession, token: str, new_password: str
) -> None:
    from app.core.auth.invite import claim_reset_token

    data = await claim_reset_token(token)
    if not data:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    result = await session.exec(select(User).where(User.id == data["user_id"]))
    user = result.first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.now(UTC)
    session.add(user)
    await session.commit()
