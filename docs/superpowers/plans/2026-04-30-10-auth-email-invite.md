# Auth, Email Service & Invite Flow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Invite-only admin authentication with pluggable async email delivery (Gmail SMTP / Mandrill).

**Architecture:** Backend email module with strategy pattern, invite tokens stored in Redis (72h TTL), Celery task for non-blocking delivery. Frontend login polish + accept-invite page, remove public registration.

**Tech Stack:** FastAPI, Celery, Redis, smtplib (Gmail), httpx (Mandrill), Next.js 15, React 19, Zustand, shadcn/ui, react-hook-form + Zod.

**Spec:** `docs/superpowers/specs/2026-04-30-auth-email-invite-design.md`

---

## File Structure

### Backend — New Files

| File | Responsibility |
|------|---------------|
| `app/core/email/__init__.py` | Package init |
| `app/core/email/provider.py` | `EmailProvider` ABC — `send(to, subject, body) -> bool` |
| `app/core/email/gmail.py` | `GmailSMTPProvider` — sync smtplib over TLS |
| `app/core/email/mandrill.py` | `MandrillProvider` — sync httpx POST to Mandrill API |
| `app/core/email/factory.py` | `get_email_provider()` — returns provider or `None` if unconfigured |
| `app/core/auth/invite.py` | Redis helpers: `store_invite_token`, `get_invite_data`, `delete_invite_token` |
| `tests/test_email.py` | Email provider unit tests (mocked SMTP/HTTP) |
| `tests/test_invite_integration.py` | Invite flow integration tests |

### Backend — Modified Files

| File | Change |
|------|--------|
| `app/config.py` | Add email config fields + `frontend_url` + `invite_token_expire_hours` |
| `app/celery_app.py` | Add `task_send_email` on `email` queue |
| `app/core/auth/models.py:21` | `password_hash: str` → `str \| None = Field(default=None, ...)` |
| `app/core/auth/service.py:52-64` | Add `password_hash is None` check in `authenticate_user` |
| `app/core/auth/schemas.py` | Add `AcceptInviteRequest`, `VerifyInviteResponse` |
| `app/core/auth/router.py` | Add `POST /accept-invite`, `GET /verify-invite` endpoints |
| `app/core/admin/schemas.py:79-84` | Remove `password` from `StaffInvite` |
| `app/core/admin/service.py:132-154` | Rewrite `invite_staff` — create inactive user, generate token, send email |

### Frontend — New Files

| File | Responsibility |
|------|---------------|
| `src/components/tenant-initializer.tsx` | Extracts tenant slug from URL, sets Zustand store |
| `src/app/(auth)/layout.tsx` | Split-panel auth layout (branding + form) |
| `src/app/(auth)/accept-invite/page.tsx` | Token verification + password form |

### Frontend — Modified Files

| File | Change |
|------|--------|
| `next.config.ts` | Fix rewrite destination: add `/api` prefix |
| `src/middleware.ts` | Remove `PUBLIC_PATHS` early return, extract tenant for all routes |
| `src/lib/tenant-store.ts` | Add localStorage persistence for slug |
| `src/components/providers.tsx` | Add `TenantInitializer` |
| `src/types/api.ts` | Add `AcceptInviteRequest`, `VerifyInviteResponse` |
| `src/hooks/use-auth.ts` | Add `acceptInvite`, remove `register` |
| `src/app/(auth)/login/page.tsx` | Password toggle, auth redirect, better error display |

### Frontend — Deleted Files

| File | Reason |
|------|--------|
| `src/app/(auth)/register/page.tsx` | No public registration — invite-only |

---

## Task 1: Backend — Email Config

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add email and invite config fields to Settings**

```python
# In backend/app/config.py, add these fields to the Settings class after jwt_algorithm:

    frontend_url: str = "http://localhost:3000"
    invite_token_expire_hours: int = 72

    email_provider: str = ""
    email_from: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    mandrill_api_key: str = ""
```

- [ ] **Step 2: Verify config loads**

Run: `cd backend && python -c "from app.config import get_settings; s = get_settings(); print(s.email_provider, s.frontend_url)"`

Expected: ` http://localhost:3000` (empty string for email_provider, default frontend_url)

- [ ] **Step 3: Commit**

```bash
git add backend/app/config.py
git commit -m "feat(email): add email and invite config fields to Settings"
```

---

## Task 2: Backend — Email Provider Module

**Files:**
- Create: `backend/app/core/email/__init__.py`
- Create: `backend/app/core/email/provider.py`
- Create: `backend/app/core/email/gmail.py`
- Create: `backend/app/core/email/mandrill.py`
- Create: `backend/app/core/email/factory.py`
- Test: `backend/tests/test_email.py`

- [ ] **Step 1: Write failing tests for email providers**

```python
# backend/tests/test_email.py
import pytest
from unittest.mock import patch, MagicMock


def test_factory_returns_none_when_no_config():
    from app.core.email.factory import get_email_provider

    with patch("app.core.email.factory.get_settings") as mock:
        mock.return_value = MagicMock(email_provider="", email_from="")
        provider = get_email_provider()
        assert provider is None


def test_factory_returns_gmail_provider():
    from app.core.email.factory import get_email_provider
    from app.core.email.gmail import GmailSMTPProvider

    with patch("app.core.email.factory.get_settings") as mock:
        mock.return_value = MagicMock(
            email_provider="gmail",
            email_from="test@gmail.com",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="user",
            smtp_password="pass",
        )
        provider = get_email_provider()
        assert isinstance(provider, GmailSMTPProvider)


def test_factory_returns_mandrill_provider():
    from app.core.email.factory import get_email_provider
    from app.core.email.mandrill import MandrillProvider

    with patch("app.core.email.factory.get_settings") as mock:
        mock.return_value = MagicMock(
            email_provider="mandrill",
            email_from="test@example.com",
            mandrill_api_key="test-key",
        )
        provider = get_email_provider()
        assert isinstance(provider, MandrillProvider)


def test_gmail_provider_sends_email():
    from app.core.email.gmail import GmailSMTPProvider

    provider = GmailSMTPProvider(
        host="smtp.gmail.com",
        port=587,
        user="user@gmail.com",
        password="pass",
        from_addr="noreply@example.com",
    )
    with patch("app.core.email.gmail.smtplib.SMTP") as mock_smtp:
        instance = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=instance)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        result = provider.send("to@test.com", "Subject", "Body")
        assert result is True
        instance.starttls.assert_called_once()
        instance.login.assert_called_once_with("user@gmail.com", "pass")
        instance.sendmail.assert_called_once()


def test_mandrill_provider_sends_email():
    from app.core.email.mandrill import MandrillProvider

    provider = MandrillProvider(
        api_key="test-key",
        from_addr="noreply@example.com",
    )
    with patch("app.core.email.mandrill.httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        result = provider.send("to@test.com", "Subject", "Body")
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["message"]["to"][0]["email"] == "to@test.com"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_email.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'app.core.email'`

- [ ] **Step 3: Create provider ABC**

```python
# backend/app/core/email/__init__.py
```

```python
# backend/app/core/email/provider.py
from abc import ABC, abstractmethod


class EmailProvider(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> bool:
        ...
```

- [ ] **Step 4: Create Gmail SMTP provider**

```python
# backend/app/core/email/gmail.py
import smtplib
from email.mime.text import MIMEText

from app.core.email.provider import EmailProvider


class GmailSMTPProvider(EmailProvider):
    def __init__(self, host: str, port: int, user: str, password: str, from_addr: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_addr = from_addr

    def send(self, to: str, subject: str, body: str) -> bool:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = to

        with smtplib.SMTP(self.host, self.port) as server:
            server.starttls()
            server.login(self.user, self.password)
            server.sendmail(self.from_addr, [to], msg.as_string())
        return True
```

- [ ] **Step 5: Create Mandrill provider**

```python
# backend/app/core/email/mandrill.py
import httpx

from app.core.email.provider import EmailProvider

MANDRILL_SEND_URL = "https://mandrillapp.com/api/1.0/messages/send"


class MandrillProvider(EmailProvider):
    def __init__(self, api_key: str, from_addr: str):
        self.api_key = api_key
        self.from_addr = from_addr

    def send(self, to: str, subject: str, body: str) -> bool:
        payload = {
            "key": self.api_key,
            "message": {
                "from_email": self.from_addr,
                "subject": subject,
                "text": body,
                "to": [{"email": to, "type": "to"}],
            },
        }
        resp = httpx.post(MANDRILL_SEND_URL, json=payload, timeout=30)
        resp.raise_for_status()
        return True
```

- [ ] **Step 6: Create factory**

```python
# backend/app/core/email/factory.py
from app.config import get_settings
from app.core.email.provider import EmailProvider


def get_email_provider() -> EmailProvider | None:
    settings = get_settings()

    if not settings.email_provider or not settings.email_from:
        return None

    if settings.email_provider == "gmail":
        from app.core.email.gmail import GmailSMTPProvider

        if not settings.smtp_user or not settings.smtp_password:
            return None
        return GmailSMTPProvider(
            host=settings.smtp_host,
            port=settings.smtp_port,
            user=settings.smtp_user,
            password=settings.smtp_password,
            from_addr=settings.email_from,
        )

    if settings.email_provider == "mandrill":
        from app.core.email.mandrill import MandrillProvider

        if not settings.mandrill_api_key:
            return None
        return MandrillProvider(
            api_key=settings.mandrill_api_key,
            from_addr=settings.email_from,
        )

    return None
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_email.py -v`

Expected: All 5 tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/core/email/ backend/tests/test_email.py
git commit -m "feat(email): add pluggable email provider module (Gmail SMTP, Mandrill)"
```

---

## Task 3: Backend — Email Celery Task

**Files:**
- Modify: `backend/app/celery_app.py`
- Test: `backend/tests/test_email.py` (append)

- [ ] **Step 1: Add send_email task test**

Append to `backend/tests/test_email.py`:

```python
def test_send_email_task_skips_when_no_provider():
    from app.celery_app import task_send_email

    with patch("app.celery_app.get_email_provider", return_value=None):
        result = task_send_email("to@test.com", "Subject", "Body")
        assert result is None


def test_send_email_task_calls_provider():
    from app.celery_app import task_send_email

    mock_provider = MagicMock()
    mock_provider.send.return_value = True

    with patch("app.celery_app.get_email_provider", return_value=mock_provider):
        task_send_email("to@test.com", "Subject", "Body")
        mock_provider.send.assert_called_once_with("to@test.com", "Subject", "Body")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_email.py::test_send_email_task_skips_when_no_provider tests/test_email.py::test_send_email_task_calls_provider -v`

Expected: FAIL — `ImportError: cannot import name 'task_send_email'`

- [ ] **Step 3: Add task_send_email to celery_app.py**

Add at the top of `backend/app/celery_app.py`, after the existing imports:

```python
import logging

logger = logging.getLogger(__name__)
```

Add before the `celery.conf.beat_schedule` block:

```python
@celery.task(name="email.send", bind=True, max_retries=3)
def task_send_email(self, to: str, subject: str, body: str):
    from app.core.email.factory import get_email_provider

    provider = get_email_provider()
    if provider is None:
        logger.warning("No email provider configured, skipping email to %s", to)
        return None
    try:
        return provider.send(to, subject, body)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_email.py -v`

Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/celery_app.py backend/tests/test_email.py
git commit -m "feat(email): add send_email Celery task with retry and graceful degradation"
```

---

## Task 4: Backend — Make password_hash Nullable

**Files:**
- Modify: `backend/app/core/auth/models.py:21`

- [ ] **Step 1: Make password_hash nullable on User model**

In `backend/app/core/auth/models.py`, change line 21:

```python
# Before:
    password_hash: str = Field(max_length=255)
# After:
    password_hash: str | None = Field(default=None, max_length=255)
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `cd backend && python -m pytest tests/test_auth_integration.py -v`

Expected: All existing auth tests PASS (they all provide password_hash values)

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/auth/models.py
git commit -m "feat(auth): make password_hash nullable for invite-only registration"
```

---

## Task 5: Backend — Invite Token Helpers

**Files:**
- Create: `backend/app/core/auth/invite.py`

- [ ] **Step 1: Create invite token Redis helpers**

```python
# backend/app/core/auth/invite.py
import json

from app.config import get_settings
from app.redis_client import get_redis


async def store_invite_token(token: str, user_id: str, tenant_id: str) -> None:
    settings = get_settings()
    r = get_redis()
    ttl = settings.invite_token_expire_hours * 3600
    data = json.dumps({"user_id": user_id, "tenant_id": tenant_id})
    await r.setex(f"invite:{token}", ttl, data)


async def get_invite_data(token: str) -> dict | None:
    r = get_redis()
    data = await r.get(f"invite:{token}")
    if data is None:
        return None
    return json.loads(data)


async def delete_invite_token(token: str) -> None:
    r = get_redis()
    await r.delete(f"invite:{token}")
```

- [ ] **Step 2: Verify it imports cleanly**

Run: `cd backend && python -c "from app.core.auth.invite import store_invite_token, get_invite_data, delete_invite_token; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/auth/invite.py
git commit -m "feat(auth): add invite token Redis helpers"
```

---

## Task 6: Backend — Modify Staff Invite Endpoint

**Files:**
- Modify: `backend/app/core/admin/schemas.py:79-84`
- Modify: `backend/app/core/admin/service.py:132-154`

- [ ] **Step 1: Remove password from StaffInvite schema**

In `backend/app/core/admin/schemas.py`, change `StaffInvite`:

```python
# Before:
class StaffInvite(BaseModel):
    email: str
    full_name: str
    password: str
    user_type: str = "staff"
    role_slugs: list[str] = []

# After:
class StaffInvite(BaseModel):
    email: str
    full_name: str
    user_type: str = "staff"
    role_slugs: list[str] = []
```

- [ ] **Step 2: Rewrite invite_staff service function**

In `backend/app/core/admin/service.py`, replace the `invite_staff` function:

```python
# Before:
async def invite_staff(session: AsyncSession, data: StaffInvite) -> User:
    result = await session.exec(select(User).where(User.email == data.email))
    if result.first() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        user_type=data.user_type,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    for slug in data.role_slugs:
        role_result = await session.exec(select(Role).where(Role.slug == slug))
        role = role_result.first()
        if role is not None:
            user_role = UserRole(user_id=user.id, role_id=role.id)
            session.add(user_role)
    await session.commit()
    return user

# After:
async def invite_staff(
    session: AsyncSession, data: StaffInvite, tenant_id: str, tenant_slug: str
) -> User:
    result = await session.exec(select(User).where(User.email == data.email))
    existing = result.first()

    if existing is not None:
        if existing.is_active:
            raise HTTPException(status_code=409, detail="User already active")
        user = existing
    else:
        user = User(
            email=data.email,
            password_hash=None,
            full_name=data.full_name,
            user_type=data.user_type,
            is_active=False,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        for slug in data.role_slugs:
            role_result = await session.exec(select(Role).where(Role.slug == slug))
            role = role_result.first()
            if role is not None:
                user_role = UserRole(user_id=user.id, role_id=role.id)
                session.add(user_role)
        await session.commit()

    import uuid as _uuid

    from app.celery_app import task_send_email
    from app.config import get_settings
    from app.core.auth.invite import store_invite_token

    token = str(_uuid.uuid4())
    await store_invite_token(token, str(user.id), tenant_id)

    settings = get_settings()
    invite_link = f"{settings.frontend_url}/t/{tenant_slug}/accept-invite?token={token}"
    subject = "You've been invited to RentManager"
    body = (
        f"Hi {user.full_name},\n\n"
        f"You've been invited to join as {user.user_type}.\n\n"
        f"Click the link below to set your password and activate your account:\n"
        f"{invite_link}\n\n"
        f"This link expires in {settings.invite_token_expire_hours} hours."
    )
    task_send_email.delay(user.email, subject, body)

    return user
```

Add `from app.core.auth.models import Role, UserRole` to the imports at the top of the file if not already present (it uses `Role` and `UserRole` — verify they are imported). Remove the `from app.core.auth.password import hash_password` import if it becomes unused after this change.

- [ ] **Step 3: Update the router to pass tenant context**

In `backend/app/core/admin/router.py`, update the `invite_tenant_staff` function:

```python
# Before:
@router.post("/staff", response_model=StaffUserResponse, status_code=201)
async def invite_tenant_staff(
    data: StaffInvite,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(_require_admin()),
):
    new_user = await invite_staff(session, data)
    return StaffUserResponse.model_validate(new_user)

# After:
@router.post("/staff", response_model=StaffUserResponse, status_code=201)
async def invite_tenant_staff(
    data: StaffInvite,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(_require_admin()),
):
    tenant_ctx = get_current_tenant()
    new_user = await invite_staff(
        session, data,
        tenant_id=str(tenant_ctx.tenant.id),
        tenant_slug=tenant_ctx.tenant.slug,
    )
    return StaffUserResponse.model_validate(new_user)
```

Make sure `get_current_tenant` is imported at the top of the router file. Add if not present:

```python
from app.core.tenancy.context import get_current_tenant
```

- [ ] **Step 4: Verify it compiles**

Run: `cd backend && python -c "from app.core.admin.router import router; print('OK')"`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/admin/schemas.py backend/app/core/admin/service.py backend/app/core/admin/router.py
git commit -m "feat(admin): rewrite staff invite to create inactive user with email notification"
```

---

## Task 7: Backend — Accept/Verify Invite Endpoints + Login Guard

**Files:**
- Modify: `backend/app/core/auth/schemas.py`
- Modify: `backend/app/core/auth/service.py`
- Modify: `backend/app/core/auth/router.py`

- [ ] **Step 1: Add invite schemas**

Append to `backend/app/core/auth/schemas.py`:

```python
class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)


class VerifyInviteResponse(BaseModel):
    valid: bool
    email: str | None = None
    full_name: str | None = None
```

- [ ] **Step 2: Add accept_invite and verify_invite service functions**

Append to `backend/app/core/auth/service.py`:

```python
from app.core.auth.invite import delete_invite_token, get_invite_data


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
    data = await get_invite_data(token)
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
    user.updated_at = datetime.now(timezone.utc)
    session.add(user)
    await session.commit()

    await delete_invite_token(token)

    roles = await get_user_roles(session, str(user.id))
    return user, roles
```

- [ ] **Step 3: Update authenticate_user with pending invite guard**

In `backend/app/core/auth/service.py`, replace `authenticate_user`:

```python
# Before:
async def authenticate_user(session: AsyncSession, data: LoginRequest) -> User:
    result = await session.exec(select(User).where(User.email == data.email))
    user = result.first()
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    user.last_login = datetime.now(timezone.utc)
    session.add(user)
    await session.commit()
    return user

# After:
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

    user.last_login = datetime.now(timezone.utc)
    session.add(user)
    await session.commit()
    return user
```

- [ ] **Step 4: Add router endpoints**

In `backend/app/core/auth/router.py`, add these imports to the existing import block:

```python
from app.core.auth.schemas import (
    AcceptInviteRequest,
    LoginRequest,
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
    verify_invite_token,
)
```

Then add these endpoints after the `/register` endpoint:

```python
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
```

- [ ] **Step 5: Verify it compiles**

Run: `cd backend && python -c "from app.core.auth.router import router; print(len(router.routes), 'routes')"`

Expected: `7 routes` (register, login, refresh, logout, me, verify-invite, accept-invite)

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/auth/schemas.py backend/app/core/auth/service.py backend/app/core/auth/router.py
git commit -m "feat(auth): add accept-invite, verify-invite endpoints and pending invite login guard"
```

---

## Task 8: Backend — Invite Integration Tests

**Files:**
- Create: `backend/tests/test_invite_integration.py`

- [ ] **Step 1: Write invite flow integration tests**

```python
# backend/tests/test_invite_integration.py
import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.core.auth.invite import get_invite_data, store_invite_token
from app.core.auth.models import User
from app.core.tenancy.models import Tenant


@pytest.mark.asyncio
async def test_invite_staff_creates_inactive_user(
    client: AsyncClient, admin_headers: dict, test_tenant: Tenant
):
    resp = await client.post(
        "/api/admin/staff",
        json={
            "email": "newstaff@test.com",
            "full_name": "New Staff",
            "role_slugs": ["staff"],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "newstaff@test.com"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_verify_invite_valid_token(
    client: AsyncClient, admin_headers: dict, test_tenant: Tenant, db_session
):
    resp = await client.post(
        "/api/admin/staff",
        json={"email": "verify@test.com", "full_name": "Verify User"},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    from app.redis_client import get_redis

    r = get_redis()
    keys = []
    async for key in r.scan_iter(match="invite:*"):
        keys.append(key)
    assert len(keys) >= 1
    token = keys[-1].replace("invite:", "")

    resp = await client.get(
        f"/api/auth/verify-invite?token={token}",
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["email"] == "verify@test.com"
    assert data["full_name"] == "Verify User"


@pytest.mark.asyncio
async def test_verify_invite_invalid_token(
    client: AsyncClient, test_tenant: Tenant
):
    resp = await client.get(
        "/api/auth/verify-invite?token=nonexistent-token",
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


@pytest.mark.asyncio
async def test_accept_invite_activates_user_and_returns_tokens(
    client: AsyncClient, admin_headers: dict, test_tenant: Tenant
):
    resp = await client.post(
        "/api/admin/staff",
        json={"email": "accept@test.com", "full_name": "Accept User"},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    from app.redis_client import get_redis

    r = get_redis()
    keys = []
    async for key in r.scan_iter(match="invite:*"):
        keys.append(key)
    token = keys[-1].replace("invite:", "")

    resp = await client.post(
        "/api/auth/accept-invite",
        json={"token": token, "password": "newpassword123"},
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data

    login_resp = await client.post(
        "/api/auth/login",
        json={"email": "accept@test.com", "password": "newpassword123"},
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert login_resp.status_code == 200


@pytest.mark.asyncio
async def test_accept_invite_token_single_use(
    client: AsyncClient, admin_headers: dict, test_tenant: Tenant
):
    resp = await client.post(
        "/api/admin/staff",
        json={"email": "singleuse@test.com", "full_name": "Single Use"},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    from app.redis_client import get_redis

    r = get_redis()
    keys = []
    async for key in r.scan_iter(match="invite:*"):
        keys.append(key)
    token = keys[-1].replace("invite:", "")

    resp = await client.post(
        "/api/auth/accept-invite",
        json={"token": token, "password": "password123"},
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert resp.status_code == 200

    resp2 = await client.post(
        "/api/auth/accept-invite",
        json={"token": token, "password": "password123"},
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_reinvite_active_user_fails(
    client: AsyncClient, admin_headers: dict, test_tenant: Tenant
):
    resp = await client.post(
        "/api/admin/staff",
        json={"email": "reinvite@test.com", "full_name": "Reinvite User"},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    from app.redis_client import get_redis

    r = get_redis()
    keys = []
    async for key in r.scan_iter(match="invite:*"):
        keys.append(key)
    token = keys[-1].replace("invite:", "")

    await client.post(
        "/api/auth/accept-invite",
        json={"token": token, "password": "password123"},
        headers={"X-Tenant-ID": test_tenant.slug},
    )

    resp2 = await client.post(
        "/api/admin/staff",
        json={"email": "reinvite@test.com", "full_name": "Reinvite User"},
        headers=admin_headers,
    )
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_login_pending_invite_returns_403(
    client: AsyncClient, admin_headers: dict, test_tenant: Tenant
):
    resp = await client.post(
        "/api/admin/staff",
        json={"email": "pending@test.com", "full_name": "Pending User"},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    login_resp = await client.post(
        "/api/auth/login",
        json={"email": "pending@test.com", "password": "anything"},
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert login_resp.status_code == 403
    assert "pending invite" in login_resp.json()["detail"].lower()
```

- [ ] **Step 2: Run the tests**

Run: `cd backend && python -m pytest tests/test_invite_integration.py -v`

Expected: All 7 tests PASS

- [ ] **Step 3: Run full test suite to verify no regressions**

Run: `cd backend && python -m pytest -v`

Expected: All tests PASS (existing + new)

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_invite_integration.py
git commit -m "test(invite): add invite flow integration tests"
```

---

## Task 9: Frontend — Bug Fixes

**Files:**
- Modify: `frontend/next.config.ts`
- Modify: `frontend/src/middleware.ts`
- Modify: `frontend/src/lib/tenant-store.ts`
- Create: `frontend/src/components/tenant-initializer.tsx`
- Modify: `frontend/src/components/providers.tsx`

- [ ] **Step 1: Fix proxy rewrite in next.config.ts**

In `frontend/next.config.ts`, change the rewrite destination:

```typescript
// Before:
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/:path*`,

// After:
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
```

- [ ] **Step 2: Fix middleware to extract tenant for all routes**

Replace the entire `frontend/src/middleware.ts`:

```typescript
import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const host = request.headers.get("host") || "";
  const isLocalhost = host.startsWith("localhost") || host.startsWith("127.0.0.1");

  let tenantSlug: string | null = null;

  if (isLocalhost) {
    const match = pathname.match(/^\/t\/([^/]+)(\/.*)?$/);
    if (match) {
      tenantSlug = match[1];
      const rewrittenPath = match[2] || "/";
      const url = request.nextUrl.clone();
      url.pathname = rewrittenPath;
      const response = NextResponse.rewrite(url);
      response.headers.set("x-tenant-slug", tenantSlug);
      return response;
    }
  } else {
    const parts = host.split(".");
    if (parts.length >= 3) {
      tenantSlug = parts[0];
    }
  }

  if (tenantSlug) {
    const response = NextResponse.next();
    response.headers.set("x-tenant-slug", tenantSlug);
    return response;
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
```

- [ ] **Step 3: Add localStorage persistence to tenant store**

Replace `frontend/src/lib/tenant-store.ts`:

```typescript
import { create } from "zustand";

const TENANT_SLUG_KEY = "rm_tenant_slug";

interface TenantState {
  slug: string | null;
  setSlug: (slug: string) => void;
}

export const useTenantStore = create<TenantState>((set) => ({
  slug:
    typeof window !== "undefined"
      ? localStorage.getItem(TENANT_SLUG_KEY)
      : null,

  setSlug: (slug) => {
    if (typeof window !== "undefined") {
      localStorage.setItem(TENANT_SLUG_KEY, slug);
    }
    set({ slug });
  },
}));
```

- [ ] **Step 4: Create TenantInitializer component**

```typescript
// frontend/src/components/tenant-initializer.tsx
"use client";

import { useEffect } from "react";
import { useTenantStore } from "@/lib/tenant-store";

export function TenantInitializer() {
  const setSlug = useTenantStore((s) => s.setSlug);

  useEffect(() => {
    const host = window.location.hostname;
    const isLocalhost = host === "localhost" || host === "127.0.0.1";

    if (isLocalhost) {
      const match = window.location.pathname.match(/^\/t\/([^/]+)/);
      if (match) {
        setSlug(match[1]);
      }
    } else {
      const parts = host.split(".");
      if (parts.length >= 3) {
        setSlug(parts[0]);
      }
    }
  }, [setSlug]);

  return null;
}
```

- [ ] **Step 5: Add TenantInitializer to Providers**

In `frontend/src/components/providers.tsx`, add the import and component:

```typescript
// Add import:
import { TenantInitializer } from "@/components/tenant-initializer";

// In the JSX, add TenantInitializer after Toaster:
        <Toaster richColors position="top-right" />
        <TenantInitializer />
```

- [ ] **Step 6: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add frontend/next.config.ts frontend/src/middleware.ts frontend/src/lib/tenant-store.ts frontend/src/components/tenant-initializer.tsx frontend/src/components/providers.tsx
git commit -m "fix(frontend): fix proxy rewrite, tenant middleware, and tenant store persistence"
```

---

## Task 10: Frontend — Types + Auth Hook Updates

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/hooks/use-auth.ts`

- [ ] **Step 1: Add invite-related types**

Append to `frontend/src/types/api.ts`:

```typescript
export interface AcceptInviteRequest {
  token: string;
  password: string;
}

export interface VerifyInviteResponse {
  valid: boolean;
  email?: string;
  full_name?: string;
}
```

- [ ] **Step 2: Update useAuth hook — add acceptInvite, remove register**

Replace `frontend/src/hooks/use-auth.ts`:

```typescript
"use client";

import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/auth-store";
import api from "@/lib/api";
import type {
  AcceptInviteRequest,
  LoginRequest,
  TokenResponse,
  UserResponse,
} from "@/types/api";

export function useAuth() {
  const router = useRouter();
  const {
    setAuth,
    clearAuth,
    setAccessToken,
    isAuthenticated,
    user,
    isLoading,
    getRefreshToken,
  } = useAuthStore();

  async function login(data: LoginRequest) {
    const res = await api.post<TokenResponse>("/auth/login", data);
    const meRes = await api.get<UserResponse>("/auth/me", {
      headers: { Authorization: `Bearer ${res.data.access_token}` },
    });
    setAuth(res.data.access_token, res.data.refresh_token, meRes.data);
    router.push("/resources");
  }

  async function acceptInvite(data: AcceptInviteRequest) {
    const res = await api.post<TokenResponse>("/auth/accept-invite", data);
    const meRes = await api.get<UserResponse>("/auth/me", {
      headers: { Authorization: `Bearer ${res.data.access_token}` },
    });
    setAuth(res.data.access_token, res.data.refresh_token, meRes.data);
    router.push("/resources");
  }

  async function logout() {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await api.post("/auth/logout", { refresh_token: refreshToken });
      } catch {
        // Logout best-effort
      }
    }
    clearAuth();
    router.push("/login");
  }

  async function initAuth() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      clearAuth();
      return;
    }
    try {
      const res = await api.post<TokenResponse>("/auth/refresh", {
        refresh_token: refreshToken,
      });
      setAccessToken(res.data.access_token);
      const meRes = await api.get<UserResponse>("/auth/me", {
        headers: { Authorization: `Bearer ${res.data.access_token}` },
      });
      setAuth(res.data.access_token, res.data.refresh_token, meRes.data);
    } catch {
      clearAuth();
    }
  }

  return {
    login,
    acceptInvite,
    logout,
    initAuth,
    isAuthenticated,
    user,
    isLoading,
  };
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

Expected: No errors (register page will error since it still uses `register` — that's expected and fixed in Task 12)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/hooks/use-auth.ts
git commit -m "feat(frontend): add invite types and acceptInvite auth hook"
```

---

## Task 11: Frontend — Auth Layout + Login Polish

**Files:**
- Create: `frontend/src/app/(auth)/layout.tsx`
- Modify: `frontend/src/app/(auth)/login/page.tsx`

- [ ] **Step 1: Create shared auth layout**

```typescript
// frontend/src/app/(auth)/layout.tsx
export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      <div className="hidden lg:flex lg:w-1/2 items-center justify-center bg-primary/5 p-12">
        <div className="max-w-md text-center">
          <div className="mb-6 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary text-primary-foreground text-2xl font-bold">
              RM
            </div>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">RentManager</h1>
          <p className="mt-3 text-muted-foreground text-lg">
            Multi-tenant rental management platform
          </p>
        </div>
      </div>
      <div className="flex w-full lg:w-1/2 items-center justify-center p-4">
        {children}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Polish login page**

Replace `frontend/src/app/(auth)/login/page.tsx`:

```typescript
"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toast } from "sonner";

const loginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push("/resources");
    }
  }, [isLoading, isAuthenticated, router]);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  async function onSubmit(data: LoginForm) {
    setIsSubmitting(true);
    try {
      await login(data);
    } catch (error: unknown) {
      const axiosError = error as {
        response?: { status?: number; data?: { detail?: string } };
      };
      const status = axiosError.response?.status;
      const detail = axiosError.response?.data?.detail;

      if (status === 403) {
        toast.error(detail || "Account access denied");
      } else {
        toast.error(detail || "Invalid email or password");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center">
        <CardTitle className="text-2xl">Sign in</CardTitle>
        <CardDescription>
          Enter your credentials to access the admin panel
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="admin@example.com"
              {...register("email")}
            />
            {errors.email && (
              <p className="text-sm text-destructive">
                {errors.email.message}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                className="pr-10"
                {...register("password")}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                tabIndex={-1}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {errors.password && (
              <p className="text-sm text-destructive">
                {errors.password.message}
              </p>
            )}
          </div>
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Signing in..." : "Sign in"}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-muted-foreground">
          <span className="cursor-not-allowed opacity-50">
            Forgot password?
          </span>
        </p>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

Expected: May show error for register page (fixed in next task). Login page should compile clean.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/\(auth\)/layout.tsx frontend/src/app/\(auth\)/login/page.tsx
git commit -m "feat(frontend): add split-panel auth layout and polish login page"
```

---

## Task 12: Frontend — Accept-Invite Page + Remove Register

**Files:**
- Create: `frontend/src/app/(auth)/accept-invite/page.tsx`
- Delete: `frontend/src/app/(auth)/register/page.tsx`

- [ ] **Step 1: Create accept-invite page**

```typescript
// frontend/src/app/(auth)/accept-invite/page.tsx
"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toast } from "sonner";
import type { VerifyInviteResponse } from "@/types/api";

const acceptSchema = z
  .object({
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type AcceptForm = z.infer<typeof acceptSchema>;

export default function AcceptInvitePage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const { acceptInvite } = useAuth();

  const [verifying, setVerifying] = useState(true);
  const [inviteData, setInviteData] = useState<VerifyInviteResponse | null>(
    null,
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AcceptForm>({
    resolver: zodResolver(acceptSchema),
  });

  useEffect(() => {
    if (!token) {
      setVerifying(false);
      return;
    }
    api
      .get<VerifyInviteResponse>(`/auth/verify-invite?token=${token}`)
      .then((res) => setInviteData(res.data))
      .catch(() => setInviteData({ valid: false }))
      .finally(() => setVerifying(false));
  }, [token]);

  async function onSubmit(data: AcceptForm) {
    if (!token) return;
    setIsSubmitting(true);
    try {
      await acceptInvite({ token, password: data.password });
    } catch (error: unknown) {
      const axiosError = error as {
        response?: { data?: { detail?: string } };
      };
      toast.error(
        axiosError.response?.data?.detail || "Failed to accept invite",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (verifying) {
    return (
      <Card className="w-full max-w-md">
        <CardContent className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </CardContent>
      </Card>
    );
  }

  if (!token || !inviteData?.valid) {
    return (
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Invalid Invite</CardTitle>
          <CardDescription>
            This invite link is invalid or has expired. Please contact your
            administrator for a new invite.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center">
        <CardTitle className="text-2xl">Set your password</CardTitle>
        <CardDescription>
          Complete your account setup to get started
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="mb-6 space-y-2">
          <div>
            <Label className="text-muted-foreground text-xs">Name</Label>
            <p className="font-medium">{inviteData.full_name}</p>
          </div>
          <div>
            <Label className="text-muted-foreground text-xs">Email</Label>
            <p className="font-medium">{inviteData.email}</p>
          </div>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                className="pr-10"
                {...register("password")}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                tabIndex={-1}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {errors.password && (
              <p className="text-sm text-destructive">
                {errors.password.message}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirmPassword">Confirm Password</Label>
            <Input
              id="confirmPassword"
              type={showPassword ? "text" : "password"}
              {...register("confirmPassword")}
            />
            {errors.confirmPassword && (
              <p className="text-sm text-destructive">
                {errors.confirmPassword.message}
              </p>
            )}
          </div>
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Activating account..." : "Activate account"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Delete register page**

```bash
rm frontend/src/app/\(auth\)/register/page.tsx
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`

Expected: No errors

- [ ] **Step 4: Start dev server and verify pages load**

Run: `cd frontend && npm run dev`

Check in browser:
- `http://localhost:3000/login` → shows login form with password toggle, branding panel on left
- `http://localhost:3000/accept-invite` → shows "Invalid Invite" (no token)
- `http://localhost:3000/accept-invite?token=test` → shows "Invalid Invite" (invalid token)
- `http://localhost:3000/register` → 404

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/\(auth\)/accept-invite/page.tsx
git rm frontend/src/app/\(auth\)/register/page.tsx
git commit -m "feat(frontend): add accept-invite page, remove public registration"
```

---

## Summary

| Task | Description | Files Changed |
|------|------------|---------------|
| 1 | Email config fields | 1 modified |
| 2 | Email provider module + tests | 5 created, 1 test |
| 3 | Email Celery task + tests | 1 modified, 1 test updated |
| 4 | Nullable password_hash | 1 modified |
| 5 | Invite token Redis helpers | 1 created |
| 6 | Staff invite endpoint rewrite | 3 modified |
| 7 | Accept/verify invite + login guard | 3 modified |
| 8 | Invite integration tests | 1 created |
| 9 | Frontend bug fixes | 3 modified, 2 created |
| 10 | Frontend types + auth hook | 2 modified |
| 11 | Auth layout + login polish | 1 created, 1 modified |
| 12 | Accept-invite page + remove register | 1 created, 1 deleted |
