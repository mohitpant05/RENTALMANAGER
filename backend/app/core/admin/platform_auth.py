from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings
from app.core.auth.models import PlatformUser
from app.core.auth.password import verify_password
from app.database import get_session

_security = HTTPBearer()


def create_platform_token(user_id: str) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "type": "platform",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


async def authenticate_platform_user(
    session: AsyncSession, email: str, password: str
) -> PlatformUser:
    result = await session.exec(
        select(PlatformUser).where(PlatformUser.email == email)
    )
    user = result.first()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated",
        )
    return user


async def get_current_platform_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    session: AsyncSession = Depends(get_session),
) -> PlatformUser:
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    if payload.get("type") != "platform":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not a platform token",
        )
    user_id = payload.get("sub")
    result = await session.exec(
        select(PlatformUser).where(PlatformUser.id == user_id)
    )
    user = result.first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user
