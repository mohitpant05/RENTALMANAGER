# Auth, Email Service & Invite Flow — Design Spec

## Overview

Invite-only admin panel authentication with pluggable async email delivery. No public registration — staff are invited by admins, accept via email link, set their own password.

## 1. Email Service

### Module: `backend/app/core/email/`

**Provider interface:**

```python
class EmailProvider(ABC):
    @abstractmethod
    async def send(self, to: str, subject: str, body: str) -> bool: ...
```

**Implementations:**

| Provider | Transport | Config |
|----------|-----------|--------|
| `GmailSMTPProvider` | `aiosmtplib` over TLS | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` |
| `MandrillProvider` | `httpx` HTTP API | `MANDRILL_API_KEY` |

**Configuration (env vars):**

```env
EMAIL_PROVIDER=gmail|mandrill
EMAIL_FROM=noreply@example.com
FRONTEND_URL=http://localhost:3000    # used in invite email links

# Gmail SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# Mandrill
MANDRILL_API_KEY=
```

**Factory:** `get_email_provider()` returns provider instance or `None` if creds not configured.

**Celery task:** `send_email_task(to, subject, body)` on dedicated `email` queue.
- If provider is `None` (creds missing) → log warning, return clean (no error).
- Retry 3x on transient failures with exponential backoff (30s, 60s, 120s).
- Permanent failure → task fails, logged.

### Future Evolution

- Per-tenant email provider config (stored in tenant config JSONB instead of env).
- HTML email templates with tenant branding (logo, colors from TenantTheme).
- Shared email queue monitoring/dashboard.

## 2. Invite Token Flow

### Backend Changes

**Modified endpoint:** `POST /api/admin/staff/invite` (replaces `POST /api/admin/staff`)

- Input: `{ email, full_name, user_type, role_slugs }`
- Creates user with `is_active=False`, no password hash.
- Generates invite token (UUID4).
- Stores in Redis: key `invite:{token}` → `{ user_id, tenant_id }`, TTL 72 hours.
- Enqueues `send_email_task` with invite link: `{FRONTEND_URL}/accept-invite?token={token}`.
- Returns `StaffUserResponse`.

**New endpoint:** `POST /api/auth/accept-invite`

- Public (no auth required).
- Input: `{ token, password }`
- Looks up `invite:{token}` in Redis.
- If missing/expired → 400 "Invalid or expired invite".
- Sets password hash on user, sets `is_active=True`, `is_verified=True`.
- Deletes Redis key (single-use token).
- Returns `TokenResponse` (auto-login on accept).

**New endpoint:** `GET /api/auth/verify-invite?token=...`

- Public.
- Returns `{ valid: true, email, full_name }` or `{ valid: false }`.
- Frontend uses this to pre-fill accept page or redirect if token is bad.

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| Re-invite pending user (`is_active=False`) | Delete old Redis token, generate new, re-send email |
| Re-invite active user (`is_active=True`) | 409 "User already active" |
| Token used twice | Redis key deleted on first accept; second attempt gets 400 |
| Token expired | 400 "Invalid or expired invite"; admin re-invites |
| Login with pending invite (`is_active=False`) | 403 "Account pending invite acceptance" |

### Schema Change Required

`password_hash` on `User` model is currently `str` (non-nullable). Change to `str | None = None` to allow creating users without a password (pending invite). Login must check for `None` password hash and return 403.

## 3. Frontend Auth Pages

### Bug Fixes

1. **Proxy rewrite:** Change `next.config.ts` destination to `http://localhost:8000/api/:path*` (currently strips `/api` prefix).
2. **Tenant middleware:** Extract tenant slug for auth pages too (currently skips `/login`, `/register`).
3. **Tenant store init:** Read slug from URL (`/t/{slug}/` on localhost) or subdomain, set in Zustand store on client mount.

### Login Page (`/login`)

- Keep current structure (Zod + react-hook-form + useAuth hook).
- Add password visibility toggle (eye icon button).
- Add "Forgot password?" link (disabled placeholder for now).
- Redirect to `/resources` if already authenticated.
- Distinct error messages: 403 (deactivated/pending) vs 401 (bad credentials).

### Accept Invite Page (`/accept-invite?token=...`)

- On mount: `GET /api/auth/verify-invite?token=...`.
- Invalid token → error message + "Contact your administrator" guidance.
- Valid token → show pre-filled name/email (read-only) + password + confirm password fields.
- Password visibility toggle.
- Min 8 chars validation, passwords must match.
- On submit: `POST /api/auth/accept-invite` → auto-login → redirect to `/resources`.

### Remove Public Register Page

Delete `src/app/(auth)/register/page.tsx`. No open registration for admin panel.

### Auth Layout (`/(auth)/layout.tsx`)

- Shared wrapper for login + accept-invite.
- Split layout: left = branding panel (app name, tagline), right = form card.
- Responsive: branding panel hidden on mobile, form card full-width.

## 4. Error Handling Summary

**Email failures:** Invite still created even if email fails. Admin can re-send invite or share link manually. Celery retries handle transient issues.

**Auth failures:** Clear error messages distinguish between bad credentials, deactivated accounts, and pending invites.

**Token safety:** Single-use (Redis key deleted on accept). TTL-based expiry (72h). No enumeration risk (UUID4 tokens).

## 5. Future Evolution (Later Phases)

- Per-tenant email provider config (move from env to tenant config JSONB).
- HTML email templates with tenant branding.
- Password reset flow (reuse same token pattern — Redis + email link).
- Invite expiry notification email.
- Bulk invite (CSV upload).
- Invite status tracking in admin panel (pending/accepted/expired).
