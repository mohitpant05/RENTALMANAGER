# Admin Infrastructure Migration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move admin routes from `(admin)/` route group to `admin/` real path segment, update icon rail to 7 items, add new sub-nav sections, and add all new shared types + hooks needed by subsequent plans.

**Architecture:** Rename route group from `(admin)` (invisible in URL) to `admin` (real path segment `/admin/...`). Update all internal links to use `/admin/` prefix. Add Reviews + Notifications to icon rail and sub-nav. Add shared TypeScript types and React Query hooks for notifications, reviews, storage, and search.

**Tech Stack:** Next.js 15, TypeScript, Zustand, TanStack Query, Axios, Lucide icons

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Move | `app/(admin)/` → `app/admin/` | Route group to real segment |
| Modify | `components/shell/icon-rail.tsx` | Add Reviews + Notifications, prefix all hrefs with `/admin` |
| Modify | `components/shell/sub-nav.tsx` | Add reviews + notifications sections, prefix all hrefs |
| Modify | `components/shell/header.tsx` | No changes needed (breadcrumbs auto-derive from path) |
| Modify | `hooks/use-auth.ts` | Add `isAdmin()`, update redirects to `/admin/resources` |
| Modify | `lib/auth-store.ts` | Add `isAdmin` derived field |
| Modify | `app/(auth)/login/page.tsx` | Update redirect from `/resources` to role-based |
| Modify | `app/page.tsx` | Change redirect from `/resources` to `/` (public landing, for now just redirect to `/admin/resources`) |
| Modify | `types/api.ts` | Add all new types |
| Create | `hooks/use-notifications.ts` | Notification query hooks |
| Create | `hooks/use-reviews.ts` | Review query hooks |
| Create | `hooks/use-storage.ts` | File upload hook |
| Create | `hooks/use-search.ts` | Search hook |

---

### Task 1: Move Admin Route Group to Real Path Segment

**Files:**
- Move: `app/(admin)/` → `app/admin/`

- [ ] **Step 1: Move the directory**

```bash
cd frontend/src/app && mv '(admin)' admin
```

- [ ] **Step 2: Verify build compiles**

```bash
cd frontend && npm run build
```

Expected: Build succeeds. All admin pages now accessible at `/admin/resources`, `/admin/bookings`, etc.

- [ ] **Step 3: Commit**

```bash
git add -A frontend/src/app/
git commit -m "refactor(frontend): move admin routes to /admin/ path prefix"
```

---

### Task 2: Update Icon Rail for /admin/ Prefix + New Items

**Files:**
- Modify: `frontend/src/components/shell/icon-rail.tsx`

- [ ] **Step 1: Update NAV_ITEMS with /admin prefix and add Reviews + Notifications**

Replace the entire `icon-rail.tsx` content:

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bell,
  Box,
  CalendarDays,
  Palette,
  Settings,
  Star,
  Users,
  Sun,
  Moon,
  LogOut,
} from "lucide-react";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

const NAV_ITEMS = [
  { href: "/admin/resources", icon: Box, label: "Resources" },
  { href: "/admin/bookings", icon: CalendarDays, label: "Bookings" },
  { href: "/admin/reviews", icon: Star, label: "Reviews" },
  { href: "/admin/staff", icon: Users, label: "Staff" },
  { href: "/admin/notifications", icon: Bell, label: "Notifications" },
  { href: "/admin/theming", icon: Palette, label: "Theming" },
  { href: "/admin/settings", icon: Settings, label: "Settings" },
] as const;

export function IconRail() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const { logout, user } = useAuth();

  const initials = user?.full_name
    ?.split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase() || "?";

  return (
    <div className="flex h-full w-[60px] flex-col items-center border-r bg-background py-4">
      <div className="mb-8">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground text-sm font-bold">
          RM
        </div>
      </div>

      <nav className="flex flex-1 flex-col items-center gap-2">
        {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
          const isActive = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              title={label}
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-lg transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground"
              )}
            >
              <Icon className="h-5 w-5" />
            </Link>
          );
        })}
      </nav>

      <div className="flex flex-col items-center gap-2">
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="relative flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground transition-colors"
          title="Toggle theme"
        >
          <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </button>
        <button
          onClick={logout}
          className="flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
          title="Logout"
        >
          <LogOut className="h-5 w-5" />
        </button>
        <Avatar className="h-8 w-8">
          <AvatarFallback className="text-xs">{initials}</AvatarFallback>
        </Avatar>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/shell/icon-rail.tsx
git commit -m "feat(frontend): update icon rail with /admin prefix + reviews and notifications"
```

---

### Task 3: Update Sub-Nav for /admin/ Prefix + New Sections

**Files:**
- Modify: `frontend/src/components/shell/sub-nav.tsx`

- [ ] **Step 1: Update all hrefs and add reviews + notifications sections**

Replace the entire `sub-nav.tsx` content:

```tsx
"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import type { ResourceTypeResponse } from "@/types/api";
import { useCreateTypeSheetStore } from "@/lib/create-type-sheet-store";

interface SubNavItem {
  href: string;
  label: string;
}

interface SubNavSection {
  title: string;
  items: SubNavItem[];
  action?: { label: string; href?: string; onClick?: () => void };
}

const STATIC_NAV_CONFIG: Record<string, SubNavSection> = {
  "/admin/bookings": {
    title: "Bookings",
    items: [
      { href: "/admin/bookings", label: "All" },
      { href: "/admin/bookings?status=pending", label: "Pending" },
      { href: "/admin/bookings?status=confirmed", label: "Confirmed" },
      { href: "/admin/bookings?status=active", label: "Active" },
      { href: "/admin/bookings?status=completed", label: "Completed" },
      { href: "/admin/bookings?status=cancelled", label: "Cancelled" },
    ],
  },
  "/admin/reviews": {
    title: "Reviews",
    items: [
      { href: "/admin/reviews", label: "All" },
      { href: "/admin/reviews?status=pending", label: "Pending Moderation" },
      { href: "/admin/reviews?status=approved", label: "Approved" },
      { href: "/admin/reviews?status=rejected", label: "Rejected" },
    ],
  },
  "/admin/notifications": {
    title: "Notifications",
    items: [
      { href: "/admin/notifications", label: "All" },
      { href: "/admin/notifications?unread=true", label: "Unread" },
    ],
  },
  "/admin/theming": {
    title: "Theming",
    items: [
      { href: "/admin/theming#brand", label: "Brand" },
      { href: "/admin/theming#colors", label: "Colors" },
      { href: "/admin/theming#typography", label: "Typography" },
      { href: "/admin/theming#components", label: "Components" },
    ],
  },
  "/admin/settings": {
    title: "Settings",
    items: [
      { href: "/admin/settings#general", label: "General" },
      { href: "/admin/settings#domains", label: "Domains" },
    ],
  },
};

function useResourceTypesNav(): SubNavSection | null {
  const setOpen = useCreateTypeSheetStore((s) => s.setOpen);
  const { data: types } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types");
      return data;
    },
    staleTime: 30_000,
  });

  if (!types) return { title: "Resources", items: [], action: { label: "+ Add Type", onClick: () => setOpen(true) } };

  return {
    title: "Resources",
    items: types.map((t) => ({ href: `/admin/resources/${t.slug}`, label: t.name })),
    action: { label: "+ Add Type", onClick: () => setOpen(true) },
  };
}

export function SubNav() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const isResourcesSection = pathname.startsWith("/admin/resources");
  const resourcesNav = useResourceTypesNav();

  const staticKey = Object.keys(STATIC_NAV_CONFIG).find((key) =>
    pathname.startsWith(key)
  );

  const config = isResourcesSection ? resourcesNav : staticKey ? STATIC_NAV_CONFIG[staticKey] : null;

  if (!config) return null;

  const currentUrl = searchParams.toString()
    ? `${pathname}?${searchParams.toString()}`
    : pathname;

  return (
    <div className="flex h-full w-[220px] flex-col border-r bg-muted/30 p-4">
      <h2 className="mb-4 text-sm font-semibold">{config.title}</h2>

      {config.items.length > 0 && (
        <nav className="flex flex-col gap-1">
          {config.items.map((item) => {
            const isActive = currentUrl === item.href || pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-md px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      )}

      {config.action && (
        config.action.onClick ? (
          <button
            onClick={config.action.onClick}
            className="mt-4 text-sm text-primary hover:underline text-left"
          >
            {config.action.label}
          </button>
        ) : config.action.href ? (
          <Link
            href={config.action.href}
            className="mt-4 text-sm text-primary hover:underline"
          >
            {config.action.label}
          </Link>
        ) : null
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/shell/sub-nav.tsx
git commit -m "feat(frontend): update sub-nav with /admin prefix + reviews and notifications sections"
```

---

### Task 4: Update Auth — Role-Based Redirects + isAdmin Helper

**Files:**
- Modify: `frontend/src/lib/auth-store.ts`
- Modify: `frontend/src/hooks/use-auth.ts`
- Modify: `frontend/src/app/(auth)/login/page.tsx`
- Modify: `frontend/src/app/admin/layout.tsx`
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Add isAdmin to auth store**

In `frontend/src/lib/auth-store.ts`, add an `isAdmin` derived getter:

```typescript
import { create } from "zustand";
import type { UserResponse } from "@/types/api";

const REFRESH_TOKEN_KEY = "rm_refresh_token";

interface AuthState {
  accessToken: string | null;
  user: UserResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setAuth: (accessToken: string, refreshToken: string, user: UserResponse) => void;
  setAccessToken: (token: string) => void;
  clearAuth: () => void;
  getRefreshToken: () => string | null;
  isAdmin: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  user: null,
  isAuthenticated: false,
  isLoading: true,

  setAuth: (accessToken, refreshToken, user) => {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    set({ accessToken, user, isAuthenticated: true, isLoading: false });
  },

  setAccessToken: (token) => {
    set({ accessToken: token });
  },

  clearAuth: () => {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    set({ accessToken: null, user: null, isAuthenticated: false, isLoading: false });
  },

  getRefreshToken: () => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  isAdmin: () => {
    const user = get().user;
    return user?.user_type === "admin" || user?.user_type === "staff";
  },
}));
```

- [ ] **Step 2: Update useAuth hook with role-based redirect**

Replace `frontend/src/hooks/use-auth.ts`:

```typescript
"use client";

import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/auth-store";
import api from "@/lib/api";
import type {
  AcceptInviteRequest,
  LoginRequest,
  RegisterRequest,
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
    isAdmin,
  } = useAuthStore();

  function getRedirectPath(userType: string): string {
    return userType === "admin" || userType === "staff"
      ? "/admin/resources"
      : "/";
  }

  async function login(data: LoginRequest) {
    const res = await api.post<TokenResponse>("/auth/login", data);
    const meRes = await api.get<UserResponse>("/auth/me", {
      headers: { Authorization: `Bearer ${res.data.access_token}` },
    });
    setAuth(res.data.access_token, res.data.refresh_token, meRes.data);
    router.push(getRedirectPath(meRes.data.user_type));
  }

  async function register(data: RegisterRequest) {
    const res = await api.post<TokenResponse>("/auth/register", data);
    const meRes = await api.get<UserResponse>("/auth/me", {
      headers: { Authorization: `Bearer ${res.data.access_token}` },
    });
    setAuth(res.data.access_token, res.data.refresh_token, meRes.data);
    router.push("/");
  }

  async function acceptInvite(data: AcceptInviteRequest) {
    const res = await api.post<TokenResponse>("/auth/accept-invite", data);
    const meRes = await api.get<UserResponse>("/auth/me", {
      headers: { Authorization: `Bearer ${res.data.access_token}` },
    });
    setAuth(res.data.access_token, res.data.refresh_token, meRes.data);
    router.push("/admin/resources");
  }

  async function logout() {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      try {
        await api.post("/auth/logout", { refresh_token: refreshToken });
      } catch {
        // best-effort
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
    register,
    acceptInvite,
    logout,
    initAuth,
    isAuthenticated,
    user,
    isLoading,
    isAdmin,
  };
}
```

- [ ] **Step 3: Update login page redirect**

In `frontend/src/app/(auth)/login/page.tsx`, change the authenticated redirect:

Replace:
```tsx
router.push("/resources");
```

With:
```tsx
const userType = user?.user_type;
router.push(userType === "admin" || userType === "staff" ? "/admin/resources" : "/");
```

Update the `useEffect` import to include `user`:

```tsx
const { login, isAuthenticated, isLoading, user } = useAuth();
```

- [ ] **Step 4: Update admin layout redirect**

In `frontend/src/app/admin/layout.tsx`, update the unauthenticated redirect:

Replace:
```tsx
router.push("/login");
```

With:
```tsx
router.push("/login");
```

(No change needed — login path stays the same.)

- [ ] **Step 5: Update root page.tsx**

Replace `frontend/src/app/page.tsx`:

```tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/admin/resources");
}
```

Note: This temporarily redirects to admin. When Phase B (public marketplace) is implemented, this becomes the public landing page and this redirect is removed.

- [ ] **Step 6: Update internal links in resource pages**

In all resource page files (`app/admin/resources/page.tsx`, `app/admin/resources/[typeSlug]/page.tsx`, `app/admin/resources/[typeSlug]/[resourceId]/page.tsx`) and booking pages (`app/admin/bookings/page.tsx`, `app/admin/bookings/[id]/page.tsx`), search for any hardcoded paths like `/resources/` or `/bookings/` in Link hrefs or router.push calls and prefix with `/admin`.

Key patterns to find-and-replace within these files:
- `href="/resources` → `href="/admin/resources`
- `href="/bookings` → `href="/admin/bookings`
- `router.push("/resources` → `router.push("/admin/resources`
- `router.push("/bookings` → `router.push("/admin/bookings`

- [ ] **Step 7: Verify build + manual test**

```bash
cd frontend && npm run build
```

Then `npm run dev` and verify:
- `http://localhost:3000` redirects to `/admin/resources`
- Icon rail shows 7 items with correct active states
- Sub-nav works for all sections
- Login redirects to `/admin/resources`

- [ ] **Step 8: Commit**

```bash
git add -A frontend/src/
git commit -m "feat(frontend): role-based redirects and /admin prefix across all pages"
```

---

### Task 5: Add All New Types to api.ts

**Files:**
- Modify: `frontend/src/types/api.ts`

- [ ] **Step 1: Append new types**

Add to the end of `frontend/src/types/api.ts`:

```typescript
// ─── Staff ─────────────────────────────────────────────

export interface StaffInviteRequest {
  email: string;
  full_name: string;
  user_type: "staff" | "admin";
  role_slugs?: string[];
}

// ─── Notifications ─────────────────────────────────────

export interface NotificationResponse {
  id: string;
  user_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface UnreadCountResponse {
  count: number;
}

// ─── Reviews ───────────────────────────────────────────

export interface ReviewResponse {
  id: string;
  resource_id: string | null;
  lister_id: string | null;
  reviewer_id: string;
  direction: string;
  rating: number;
  comment: string | null;
  category_ratings: Record<string, number> | null;
  status: string;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewCreate {
  resource_id: string;
  rating: number;
  comment?: string;
  category_ratings?: Record<string, number>;
  direction?: string;
}

export interface ReviewModerateRequest {
  status: "approved" | "rejected";
  rejection_reason?: string;
}

export interface RatingSummaryResponse {
  average: number;
  count: number;
  distribution: Record<string, number>;
}

// ─── Storage ───────────────────────────────────────────

export interface UploadUrlRequest {
  filename: string;
  content_type: string;
  entity_type: string;
  entity_id: string;
}

export interface UploadUrlResponse {
  upload_url: string;
  attachment_id: string;
}

export interface AttachmentResponse {
  id: string;
  entity_type: string;
  entity_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  url: string;
  created_at: string;
}

// ─── Search ────────────────────────────────────────────

export interface SearchRequest {
  query: string;
  type_slug?: string;
  min_price?: number;
  max_price?: number;
  location?: string;
  sort?: "relevance" | "price_asc" | "price_desc" | "rating";
  offset?: number;
  limit?: number;
}

export interface SearchResponse {
  hits: ResourceResponse[];
  total: number;
  processing_time_ms: number;
}

// ─── Domains ───────────────────────────────────────────

export interface DomainResponse {
  id: string;
  domain: string;
  tenant_id: string;
  created_at: string;
}

export interface DomainCreate {
  domain: string;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/api.ts
git commit -m "feat(frontend): add types for staff, notifications, reviews, storage, search, domains"
```

---

### Task 6: Create Shared Hooks

**Files:**
- Create: `frontend/src/hooks/use-notifications.ts`
- Create: `frontend/src/hooks/use-reviews.ts`
- Create: `frontend/src/hooks/use-storage.ts`
- Create: `frontend/src/hooks/use-search.ts`

- [ ] **Step 1: Create use-notifications.ts**

```typescript
// frontend/src/hooks/use-notifications.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { NotificationResponse, UnreadCountResponse } from "@/types/api";

export function useUnreadCount() {
  return useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: async () => {
      const { data } = await api.get<UnreadCountResponse>("/notifications/unread-count");
      return data;
    },
    refetchInterval: 30_000,
  });
}

export function useNotifications(params?: { unread_only?: boolean; offset?: number; limit?: number }) {
  return useQuery({
    queryKey: ["notifications", params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.unread_only) searchParams.set("unread_only", "true");
      if (params?.offset) searchParams.set("offset", String(params.offset));
      if (params?.limit) searchParams.set("limit", String(params.limit));
      const { data } = await api.get<NotificationResponse[]>(`/notifications?${searchParams.toString()}`);
      return data;
    },
  });
}

export function useMarkRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (notificationId: string) => {
      await api.post(`/notifications/${notificationId}/read`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useMarkAllRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.post("/notifications/read-all");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}
```

- [ ] **Step 2: Create use-reviews.ts**

```typescript
// frontend/src/hooks/use-reviews.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  ReviewResponse,
  ReviewCreate,
  ReviewModerateRequest,
  RatingSummaryResponse,
} from "@/types/api";

export function useReviews(params?: {
  resource_id?: string;
  direction?: string;
  status?: string;
  offset?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["reviews", params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.resource_id) searchParams.set("resource_id", params.resource_id);
      if (params?.direction) searchParams.set("direction", params.direction);
      if (params?.status) searchParams.set("status", params.status);
      if (params?.offset) searchParams.set("offset", String(params.offset));
      searchParams.set("limit", String(params?.limit ?? 20));
      const { data } = await api.get<ReviewResponse[]>(`/reviews?${searchParams.toString()}`);
      return data;
    },
  });
}

export function useMyReviews(params?: { offset?: number; limit?: number }) {
  return useQuery({
    queryKey: ["reviews", "my", params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.offset) searchParams.set("offset", String(params.offset));
      searchParams.set("limit", String(params?.limit ?? 20));
      const { data } = await api.get<ReviewResponse[]>(`/reviews/my?${searchParams.toString()}`);
      return data;
    },
  });
}

export function useRatingSummary(resourceId: string) {
  return useQuery({
    queryKey: ["reviews", "summary", resourceId],
    queryFn: async () => {
      const { data } = await api.get<RatingSummaryResponse>(`/reviews/resource/${resourceId}/summary`);
      return data;
    },
    enabled: !!resourceId,
  });
}

export function useCreateReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (review: ReviewCreate) => {
      const { data } = await api.post<ReviewResponse>("/reviews", review);
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["reviews"] });
      if (data.resource_id) {
        queryClient.invalidateQueries({ queryKey: ["reviews", "summary", data.resource_id] });
      }
    },
  });
}

export function useModerateReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ reviewId, body }: { reviewId: string; body: ReviewModerateRequest }) => {
      const { data } = await api.post<ReviewResponse>(`/reviews/${reviewId}/moderate`, body);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews"] });
    },
  });
}
```

- [ ] **Step 3: Create use-storage.ts**

```typescript
// frontend/src/hooks/use-storage.ts
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import api from "@/lib/api";
import type { AttachmentResponse, UploadUrlRequest, UploadUrlResponse } from "@/types/api";

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"];
const MAX_SIZE = 10 * 1024 * 1024; // 10MB

export function useAttachments(entityType: string, entityId: string) {
  return useQuery({
    queryKey: ["attachments", entityType, entityId],
    queryFn: async () => {
      const { data } = await api.get<AttachmentResponse[]>(
        `/storage/attachments?entity_type=${entityType}&entity_id=${entityId}`
      );
      return data;
    },
    enabled: !!entityId,
  });
}

export function useUpload(entityType: string, entityId: string) {
  const queryClient = useQueryClient();
  const [isUploading, setIsUploading] = useState(false);

  async function upload(file: File): Promise<AttachmentResponse | null> {
    if (!ALLOWED_TYPES.includes(file.type)) {
      throw new Error("File type not supported. Use JPG, PNG, WebP, or GIF.");
    }
    if (file.size > MAX_SIZE) {
      throw new Error("File too large. Maximum 10MB.");
    }

    setIsUploading(true);
    try {
      const { data: urlData } = await api.post<UploadUrlResponse>("/storage/upload-url", {
        filename: file.name,
        content_type: file.type,
        entity_type: entityType,
        entity_id: entityId,
      } as UploadUrlRequest);

      await axios.put(urlData.upload_url, file, {
        headers: { "Content-Type": file.type },
      });

      const { data: attachment } = await api.post<AttachmentResponse>("/storage/confirm", {
        attachment_id: urlData.attachment_id,
      });

      queryClient.invalidateQueries({ queryKey: ["attachments", entityType, entityId] });
      return attachment;
    } finally {
      setIsUploading(false);
    }
  }

  const deleteMutation = useMutation({
    mutationFn: async (attachmentId: string) => {
      await api.delete(`/storage/attachments/${attachmentId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["attachments", entityType, entityId] });
    },
  });

  return { upload, isUploading, deleteAttachment: deleteMutation.mutate, isDeleting: deleteMutation.isPending };
}
```

- [ ] **Step 4: Create use-search.ts**

```typescript
// frontend/src/hooks/use-search.ts
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { SearchRequest, SearchResponse } from "@/types/api";

export function useSearch(params: SearchRequest, enabled = true) {
  return useQuery({
    queryKey: ["search", params],
    queryFn: async () => {
      const { data } = await api.post<SearchResponse>("/search", params);
      return data;
    },
    enabled: enabled && !!params.query,
  });
}
```

- [ ] **Step 5: Verify build**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/use-notifications.ts frontend/src/hooks/use-reviews.ts frontend/src/hooks/use-storage.ts frontend/src/hooks/use-search.ts
git commit -m "feat(frontend): add shared hooks for notifications, reviews, storage, and search"
```

---

## Verification Checklist

- [ ] All admin pages accessible at `/admin/` prefix
- [ ] Icon rail shows 7 items: Resources, Bookings, Reviews, Staff, Notifications, Theming, Settings
- [ ] Sub-nav works for all sections including new Reviews + Notifications
- [ ] Login redirects admin/staff to `/admin/resources`
- [ ] Root page redirects to `/admin/resources`
- [ ] TypeScript compiles with no errors
- [ ] All new types and hooks importable
