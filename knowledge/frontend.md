# Frontend — Next.js Application

## Structure

```
frontend/
├── src/
│   ├── app/                  # Next.js App Router
│   │   ├── layout.tsx        # Root layout with providers
│   │   ├── page.tsx          # Landing page
│   │   └── not-found.tsx     # 404 page
│   │
│   ├── components/
│   │   ├── tenant-initializer.tsx   # Resolves tenant on page load
│   │   └── providers.tsx            # App-wide context providers
│   │
│   ├── hooks/
│   │   ├── use-auth.ts         # Auth state + actions
│   │   ├── use-notifications.ts
│   │   ├── use-currency.ts
│   │   ├── use-platform.ts
│   │   ├── use-reviews.ts
│   │   ├── use-addons.ts
│   │   ├── use-booking-flow.ts
│   │   ├── use-search.ts
│   │   └── use-storage.ts
│   │
│   ├── lib/
│   │   ├── api.ts              # Axios instance with auth + tenant interceptors
│   │   ├── auth-store.ts       # Zustand auth store (tokens, user)
│   │   ├── tenant-store.ts     # Zustand tenant store (slug, resolved)
│   │   ├── platform-store.ts   # Platform-level state
│   │   └── utils.ts
│   │
│   ├── types/
│   │   ├── api.ts
│   │   ├── payment.ts
│   │   ├── payout.ts
│   │   └── commission.ts
│   │
│   ├── styles/globals.css
│   └── middleware.ts           # Next.js edge middleware (tenant + auth routing)
│
├── Dockerfile                  # Multi-stage (dev/prod)
├── package.json
└── tsconfig.json
```

## Tenant Resolution (Frontend Side)

### 1. Next.js Middleware (`src/middleware.ts`)
Runs on every request at edge:
- **Localhost**: extracts tenant from `/t/<slug>/...` URL pattern, rewrites to `/...` with `x-tenant-slug` header
- **Production**: extracts subdomain from host (e.g., `acme.rentmanager.com` → `acme`)
- Superadmin routes (`/superadmin/*`) skip tenant check
- Admin routes require `rm_auth` cookie

### 2. TenantInitializer Component (`components/tenant-initializer.tsx`)
Client-side, runs on mount:
- Calls `GET /api/tenancy/resolve?domain=<hostname>` to resolve by custom domain
- Falls back to `/t/<slug>` URL extraction on localhost
- Stores slug in Zustand `tenant-store` + localStorage

### 3. API Interceptor (`lib/api.ts`)
Every API call:
- Injects `Authorization: Bearer <token>` from auth store
- Injects `X-Tenant-ID: <slug>` from tenant store
- Handles 401 → automatic token refresh with queue

## State Management

Zustand stores (persist to localStorage):
- `auth-store` — accessToken, refreshToken, user object
- `tenant-store` — slug, resolved flag
- `platform-store` — platform-level config

## Tech Stack
- Next.js 15 (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui component library
- Zustand for state
- Axios for HTTP
