# Tenant Admin Dashboard — Frontend Design Spec

## Overview

Tenant admin dashboard for RentManager. The interface tenant owners/admins use to manage their rental business: resources, bookings, staff, theming, and settings.

## Tech Stack

| Layer | Choice |
|-------|--------|
| Framework | Next.js 15 (App Router, Server Components) |
| UI | shadcn/ui + Tailwind CSS v4 |
| State | Zustand (auth/client state) + TanStack Query (server state) |
| Tables | TanStack Table (lean v1: pagination, sort, search) |
| Forms | React Hook Form + Zod |
| Auth | Memory access token + localStorage refresh token |
| Color Mode | System toggle (dark/light) via next-themes |
| Tenant Resolution | Path-based dev (`/t/[slug]/...`), subdomain prod — middleware rewrites |

## Architecture

```
frontend/src/
├── app/
│   ├── (auth)/                    # Login/register (no admin shell)
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── (admin)/                   # Admin shell layout (icon rail + sub-nav)
│   │   ├── layout.tsx             # Shell with sidebar, auth guard
│   │   ├── resources/
│   │   │   ├── page.tsx           # Resource types list
│   │   │   └── [typeSlug]/
│   │   │       ├── page.tsx       # Resources of this type
│   │   │       └── [id]/page.tsx  # Single resource edit
│   │   ├── bookings/
│   │   │   ├── page.tsx           # Bookings list
│   │   │   └── [id]/page.tsx      # Booking detail
│   │   ├── staff/page.tsx         # Staff list + invite
│   │   ├── theming/page.tsx       # Theme editor
│   │   └── settings/page.tsx      # Tenant config
│   ├── middleware.ts              # Tenant resolution (subdomain↔path)
│   └── layout.tsx                 # Root: providers, fonts, theme
├── components/
│   ├── ui/                        # shadcn/ui components
│   ├── data-table/                # Reusable DataTable wrapper
│   ├── shell/                     # Icon rail, sub-nav, header
│   └── forms/                     # Shared form components
├── lib/
│   ├── api/                       # API client, interceptors, refresh logic
│   ├── auth/                      # Auth store (Zustand), guards
│   ├── tenant/                    # Tenant context, resolution helpers
│   └── utils.ts                   # cn(), formatters
├── hooks/                         # TanStack Query hooks per domain
│   ├── use-resources.ts
│   ├── use-bookings.ts
│   ├── use-staff.ts
│   └── use-tenant.ts
└── types/                         # Shared TypeScript types (mirror backend schemas)
```

## Shell & Navigation

### Layout: Icon Rail + Sub-Nav + Content

Three-column layout:

1. **Icon rail** (~60px, fixed left):
   - Module icons: Resources, Bookings, Staff, Theming, Settings
   - Bottom-pinned: user avatar, theme toggle (sun/moon), logout
   - Active module highlighted with accent background

2. **Sub-nav panel** (~220px, collapsible):
   - Context changes per active module:
     - Resources → resource types list + "Add Type" action
     - Bookings → status filter tabs (All, Pending, Active, Completed, Cancelled)
     - Staff → none (single page)
     - Theming → section links (Brand, Colors, Typography, Components)
     - Settings → section links (General, Domains)

3. **Content area** (fills remainder):
   - Breadcrumb trail at top
   - Page title + action buttons (top-right)
   - Main content below

### Responsive Behavior

- Desktop (≥1024px): Full three-column layout
- Tablet (768-1023px): Icon rail collapses to hamburger, sub-nav becomes drawer
- Mobile (<768px): Full-screen content, bottom nav or hamburger

## Auth Flow

1. User hits any `(admin)` route → `layout.tsx` checks Zustand auth store
2. No token in memory → check localStorage for refresh token
3. No refresh token → redirect to `/login`
4. Has refresh token → attempt silent refresh via `POST /api/auth/refresh`
5. Refresh succeeds → store new access token in Zustand, continue
6. Refresh fails → clear all, redirect to `/login`
7. Login page → `POST /api/auth/login` → store access token (Zustand), refresh token (localStorage)
8. All API calls: axios interceptor attaches `Authorization: Bearer <access_token>`
9. 401 response → interceptor queues request, attempts refresh, retries on success
10. Tenant slug: extracted from URL path (dev) or subdomain (prod) by middleware, passed as `X-Tenant-Slug` header to backend

### Auth Store (Zustand)

```typescript
interface AuthState {
  accessToken: string | null
  user: User | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refresh: () => Promise<boolean>
}
```

## Module: Resources

Most complex module. Three route levels.

### Resource Types List (`/resources`)

- Grid of cards showing each resource type: icon, name, slug, resource count, availability model badge
- "Create Resource Type" button → full-page form or large modal
- Resource type form fields: name, slug (auto-generated from name), icon picker, availability_model (select: date_range/time_slot/hourly), pricing_model (select: fixed_per_day/fixed_per_slot/per_hour/tiered/custom), attribute schema builder

### Attribute Schema Builder

Dynamic form for defining resource type attributes:
- List of attribute rows, each with: name (text), type (select: text/number/enum/tags/boolean/date), required (toggle), filterable (toggle)
- If type=enum: additional "options" field (tag input)
- Add/remove/reorder attributes
- This schema is saved as JSONB and drives the resource create/edit form

### Resources List (`/resources/[typeSlug]`)

- DataTable: name, status (active/draft/inactive), base_price, rating, created_at
- Pagination, sort by any column, search by name
- Row click → navigate to detail
- "Add Resource" button
- Filter: status dropdown

### Resource Detail (`/resources/[typeSlug]/[id]`)

- Form with sections:
  - **Basic Info** — name, description (rich text or textarea), location (text + optional geo picker later), base_price, currency, status
  - **Dynamic Attributes** — rendered from type's attribute_schema. Each attribute becomes a form field of appropriate type (text input, number input, select, tag input, checkbox, date picker)
  - **Images** — Upload via presigned URL (storage API), display uploaded attachments, delete
- Save → PUT to update resource

## Module: Bookings

### Bookings List (`/bookings`)

- DataTable: guest_name (from user), resource_name, start/end dates, status (color-coded badge), total_price, created_at
- Sub-nav tabs filter by status
- Sort by date (default: newest first)
- Search by guest name or resource name
- Row click → detail

### Booking Detail (`/bookings/[id]`)

- Read-heavy layout:
  - Guest info card (name, email, phone)
  - Resource info card (name, type, link)
  - Date range with duration
  - Pricing breakdown (base × days/hours, any adjustments)
  - Status timeline (visual progression through states)
- Action buttons (contextual based on current status):
  - Pending → Confirm / Reject
  - Confirmed → Cancel / Mark Active
  - Active → Complete / Mark No-Show
  - Each action calls appropriate backend endpoint with state transition

## Module: Staff

### Staff List (`/staff`)

Single page with:
- DataTable: full_name, email, user_type (badge: admin/staff), roles (badge list), status (active/deactivated)
- "Invite Staff" button → slide-out sheet or modal
- Row actions: deactivate user

### Invite Staff Form

- Fields: email, full_name, password, user_type (select: staff/admin), role_slugs (multi-select from available roles)
- Submit → `POST /api/admin/staff`
- Success → refetch staff list, close form

## Module: Theming

### Theme Editor (`/theming`)

Single page with sub-nav section links. Two-panel layout on desktop: form on left, live preview on right.

**Sections:**

1. **Brand** — Logo upload (drag-drop → storage API), favicon upload, business name (read from tenant config)

2. **Colors** — Color picker inputs for: primary, secondary, accent, background, surface, text_primary, text_secondary, error, success. Each renders as input + swatch.

3. **Typography** — Font family select (curated Google Fonts list), heading font select, base_size input (px), border_radius slider (px)

4. **Components** — Button style radio (rounded/square/pill), card_shadow toggle, navbar_position select (top/side), footer_layout select (standard/minimal/expanded)

**Live Preview Panel:**
- Mini mock showing: nav bar, a card with button, text sample, color swatches
- Updates in real-time as values change (local state, not saved yet)
- Uses CSS variables that update dynamically

**Save:** Single "Save Theme" button → `PUT /api/admin/theme` with full theme object. Partial updates supported by backend.

## Module: Settings

### Settings Page (`/settings`)

Sub-nav section links. Single page with sections:

**General:**
- Tenant name (text input)
- Base currency (select from common currencies)
- Timezone (select, searchable — major timezones)
- Config (JSON editor for advanced config — collapsible, optional)
- Save → `PATCH /api/admin/tenant`

**Domains:**
- Table of current custom domains (domain, added_at)
- "Add Domain" form: domain input + add button → `POST /api/admin/domains`
- Delete action on each row → `DELETE /api/admin/domains/{id}`
- Info box with DNS setup instructions (CNAME to platform domain)

## Tenant Resolution (Middleware)

```typescript
// middleware.ts
// Production: client.rentmanager.com → extract "client" → rewrite to /t/client/...
// Development: /t/client/resources → pass through as-is
// API calls: attach X-Tenant-Slug header derived from resolved slug
```

- Middleware reads hostname, extracts subdomain if not localhost
- In dev (localhost): expects `/t/[slug]/` prefix — no rewrite needed
- In prod: rewrites subdomain to path prefix transparently
- Stores resolved slug in request header for downstream use
- Auth pages (`/login`, `/register`) still need tenant context (user registers under a tenant)

## API Client

```typescript
// lib/api/client.ts
// Axios instance with:
// - baseURL from env (NEXT_PUBLIC_API_URL)
// - Request interceptor: attach Bearer token from auth store
// - Request interceptor: attach X-Tenant-Slug from tenant context
// - Response interceptor: on 401, attempt refresh, retry original request
// - Response interceptor: on 403, show permission denied toast
```

## Data Fetching Pattern

TanStack Query hooks per domain:

```typescript
// hooks/use-resources.ts
export function useResourceTypes() { ... }
export function useResources(typeSlug: string, params: ListParams) { ... }
export function useResource(typeSlug: string, id: string) { ... }
export function useCreateResource(typeSlug: string) { ... }  // mutation
export function useUpdateResource(typeSlug: string, id: string) { ... }  // mutation
```

Queries use staleTime of 30s for lists, 60s for detail views. Mutations invalidate related queries on success.

## Dependencies (additions to package.json)

```json
{
  "@tanstack/react-query": "^5",
  "@tanstack/react-table": "^8",
  "react-hook-form": "^7",
  "@hookform/resolvers": "^3",
  "zod": "^3",
  "zustand": "^5",
  "axios": "^1",
  "next-themes": "^0.4",
  "lucide-react": "^0.400",
  "sonner": "^1",
  "class-variance-authority": "^0.7",
  "clsx": "^2",
  "tailwind-merge": "^2"
}
```

## Out of Scope (v1)

- Calendar view for bookings
- Role CRUD (just role assignment)
- Bulk actions on tables
- Column visibility/resize
- Rich text editor for resource descriptions
- Geo picker for resource location
- Notification management
- Analytics/metrics dashboard
- i18n/multi-language
- Mobile-optimized views (responsive but not mobile-first)
