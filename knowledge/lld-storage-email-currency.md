# LLD: File Storage, Email, and Currency

## File Storage (MinIO)

Source: `backend/app/core/storage/`

### Bucket Naming
```
Bucket: rm-{tenant_slug}
```
Per-tenant bucket isolation. Created on first upload via `ensure_bucket()`.

### Upload Flow (Backend-Proxied)
```
Client                    Backend                    MinIO
  │ POST /storage/upload    │                         │
  │ (multipart: file,       │                         │
  │  entity_type, entity_id)│                         │
  │─────────────────────────►                         │
  │                         │ Validate type + size    │
  │                         │ Generate path:          │
  │                         │ {type}/{id}/{uuid}_{name}│
  │                         │ put_object ─────────────►│
  │                         │ INSERT Attachment       │
  │                         │ presigned_get_object ───►│
  │◄────────────────────────│                         │
  │ {attachment + download_url}                       │
```

Uploads go through the backend (no direct browser-to-MinIO access).
Downloads use presigned URLs (rewritten via `MINIO_PUBLIC_ENDPOINT`).

### URL Expiry
- Upload URL: 15 minutes
- Download URL: 60 minutes

### Attachment Model
```sql
attachments (
  id            UUID PK,
  entity_type   VARCHAR,      -- 'resource', 'booking', 'user', etc.
  entity_id     UUID,         -- polymorphic FK
  file_path     VARCHAR,      -- path within MinIO bucket
  file_name     VARCHAR,
  mime_type     VARCHAR,
  file_size     INT,
  purpose       VARCHAR,      -- 'photo', 'document', 'avatar'
  uploaded_by   UUID FK → users.id,
  created_at    TIMESTAMPTZ
)
```

### Delete
Owner or admin can delete. Removes MinIO object + DB record.

---

## Email System

Source: `backend/app/core/email/`

### Provider Pattern
```python
class EmailProvider(ABC):
    def send(self, to: str, subject: str, body: str) -> bool
```

### Factory (`email/factory.py`)
```
EMAIL_PROVIDER env var → provider:
  "console"  → ConsoleEmailProvider (prints to stdout, dev only)
  "gmail"    → GmailSMTPProvider (requires SMTP_USER, SMTP_PASSWORD)
  "mandrill" → MandrillProvider (requires MANDRILL_API_KEY)
  null/empty → None (emails silently skipped)
```

### Email Delivery
All emails sent via Celery task `email.send`:
- Queue: `email` (separate from default)
- Max retries: 3
- Backoff: 30s × 2^retry (30s, 60s, 120s)

### Email Templates (`email/templates.py`)
- `welcome_email(name)` — on registration or invite acceptance
- `booking_confirmation_email(name, resource, start, end, price)` — on booking confirmation
- `booking_status_change_email(name, resource, status)` — on cancel/reject
- `staff_invite_email(name, invite_url)` — staff invitation

---

## Currency System

Source: `backend/app/core/currency/`

### Exchange Rate Source
External API: `https://api.exchangerate.host/latest`

### 32 Supported Currencies
USD, EUR, GBP, INR, AUD, CAD, JPY, CNY, CHF, SGD, AED, SAR, BRL, MXN, ZAR, THB, KRW, TRY, RUB, NZD, SEK, NOK, DKK, HKD, MYR, PHP, IDR, VND, EGP, NGN, KES, PKR

### Caching Strategy
```
Redis key: currency:rates:{base}
TTL: 3600 seconds (1 hour)
```
1. Check Redis cache
2. If miss → fetch from API, cache result
3. Apply admin overrides (Redis key: `currency:overrides`)

### Admin Rate Overrides
```python
set_rate_override(currency, rate_to_usd)    # stores in Redis, invalidates USD cache
remove_rate_override(currency)               # removes override
```
Overrides only apply to USD-base rates. Override cache has no TTL (persistent until removed).

### Conversion Formula
```python
converted = amount / from_rate * to_rate
```
All rates relative to base currency.

### Celery Refresh
Task `currency.refresh_rates` runs every 12 hours:
- Clears USD cache
- Fetches fresh rates (re-populates cache)

### Endpoints (no auth, no tenant required)
```
GET /api/currency/rates → all exchange rates
GET /api/currency/convert?from=USD&to=INR&amount=100 → converted amount
```
