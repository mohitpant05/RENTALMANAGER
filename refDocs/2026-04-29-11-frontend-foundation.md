# Frontend Foundation + Shell + Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up the Next.js admin dashboard foundation with dependencies, shadcn/ui, dark/light theme, API client with auth, tenant middleware, and the icon rail + sub-nav shell layout.

**Architecture:** Next.js 15 App Router with route groups `(auth)` and `(admin)`. Zustand stores for auth and tenant state. Axios-based API client with automatic token refresh. Next.js middleware rewrites subdomain to path prefix in production, passes through path-based routing in development.

**Tech Stack:** Next.js 15, React 19, Tailwind CSS v4, shadcn/ui, Zustand, TanStack Query, Axios, next-themes, React Hook Form, Zod, Lucide icons

---

## File Structure

```
frontend/src/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx          # Login form page
│   │   └── register/page.tsx       # Registration form page
│   ├── (admin)/
│   │   ├── layout.tsx              # Admin shell (auth guard + sidebar)
│   │   ├── page.tsx                # Redirect to /resources
│   │   ├── resources/page.tsx      # Placeholder
│   │   ├── bookings/page.tsx       # Placeholder
│   │   ├── staff/page.tsx          # Placeholder
│   │   ├── theming/page.tsx        # Placeholder
│   │   └── settings/page.tsx       # Placeholder
│   ├── layout.tsx                  # Root layout (providers)
│   ├── page.tsx                    # Landing redirect
│   └── not-found.tsx               # 404 page
├── components/
│   ├── ui/                         # shadcn/ui (auto-generated)
│   ├── shell/
│   │   ├── icon-rail.tsx           # Left icon rail
│   │   ├── sub-nav.tsx             # Context-dependent sub-navigation
│   │   └── header.tsx              # Content area header with breadcrumb
│   └── providers.tsx               # All providers wrapped
├── lib/
│   ├── api.ts                      # Axios instance with interceptors
│   ├── auth-store.ts               # Zustand auth store
│   ├── tenant-store.ts             # Zustand tenant store
│   └── utils.ts                    # cn() helper
├── middleware.ts                   # Tenant resolution middleware
├── hooks/
│   └── use-auth.ts                 # Auth convenience hook
└── types/
    └── api.ts                      # Shared API response types
```

---

### Task 1: Install Dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install core dependencies**

```bash
cd frontend && npm install @tanstack/react-query @tanstack/react-table react-hook-form @hookform/resolvers zod zustand axios next-themes lucide-react sonner class-variance-authority clsx tailwind-merge
```

- [ ] **Step 2: Install shadcn/ui CLI and init**

```bash
cd frontend && npx shadcn@latest init -d
```

This creates `components.json` and sets up the shadcn/ui configuration. Accept defaults (New York style, Zinc base color, CSS variables).

- [ ] **Step 3: Add initial shadcn components**

```bash
cd frontend && npx shadcn@latest add button input label card separator avatar dropdown-menu sheet toast sonner
```

- [ ] **Step 4: Verify the build compiles**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): install dependencies and init shadcn/ui"
```

---

### Task 2: Utility Helpers and Types

**Files:**
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/src/types/api.ts`

- [ ] **Step 1: Create utils.ts with cn helper**

```typescript
// frontend/src/lib/utils.ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 2: Create shared API types matching backend schemas**

```typescript
// frontend/src/types/api.ts
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  is_active: boolean;
  is_verified: boolean;
  user_type: string;
  avatar_url: string | null;
  created_at: string;
  roles: string[];
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface TenantResponse {
  id: string;
  name: string;
  slug: string;
  schema_name: string;
  is_active: boolean;
  config: Record<string, unknown> | null;
  base_currency: string;
  timezone: string;
  created_at: string;
  updated_at: string;
}

export interface ThemeResponse {
  id: string;
  tenant_id: string;
  brand: Record<string, unknown>;
  colors: Record<string, unknown>;
  typography: Record<string, unknown>;
  components: Record<string, unknown>;
  features: Record<string, unknown>;
  updated_at: string;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/utils.ts frontend/src/types/api.ts
git commit -m "feat(frontend): add utility helpers and API types"
```

---

### Task 3: Auth Store (Zustand)

**Files:**
- Create: `frontend/src/lib/auth-store.ts`

- [ ] **Step 1: Create auth store**

```typescript
// frontend/src/lib/auth-store.ts
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
}

export const useAuthStore = create<AuthState>((set) => ({
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
}));
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/auth-store.ts
git commit -m "feat(frontend): add Zustand auth store with token management"
```

---

### Task 4: Tenant Store (Zustand)

**Files:**
- Create: `frontend/src/lib/tenant-store.ts`

- [ ] **Step 1: Create tenant store**

```typescript
// frontend/src/lib/tenant-store.ts
import { create } from "zustand";

interface TenantState {
  slug: string | null;
  setSlug: (slug: string) => void;
}

export const useTenantStore = create<TenantState>((set) => ({
  slug: null,
  setSlug: (slug) => set({ slug }),
}));
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/tenant-store.ts
git commit -m "feat(frontend): add Zustand tenant store"
```

---

### Task 5: API Client with Token Refresh

**Files:**
- Create: `frontend/src/lib/api.ts`

- [ ] **Step 1: Create axios instance with interceptors**

```typescript
// frontend/src/lib/api.ts
import axios from "axios";
import { useAuthStore } from "./auth-store";
import { useTenantStore } from "./tenant-store";
import type { TokenResponse } from "@/types/api";

const api = axios.create({
  baseURL: "/api",
});

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach((promise) => {
    if (token) {
      promise.resolve(token);
    } else {
      promise.reject(error);
    }
  });
  failedQueue = [];
}

api.interceptors.request.use((config) => {
  const { accessToken } = useAuthStore.getState();
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }

  const { slug } = useTenantStore.getState();
  if (slug) {
    config.headers["X-Tenant-ID"] = slug;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({
          resolve: (token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(api(originalRequest));
          },
          reject,
        });
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    const refreshToken = useAuthStore.getState().getRefreshToken();
    if (!refreshToken) {
      useAuthStore.getState().clearAuth();
      isRefreshing = false;
      return Promise.reject(error);
    }

    try {
      const { data } = await axios.post<TokenResponse>("/api/auth/refresh", {
        refresh_token: refreshToken,
      });
      useAuthStore.getState().setAuth(data.access_token, data.refresh_token, useAuthStore.getState().user!);
      processQueue(null, data.access_token);
      originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      useAuthStore.getState().clearAuth();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default api;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/api.ts
git commit -m "feat(frontend): add API client with automatic token refresh"
```

---

### Task 6: Auth Hook

**Files:**
- Create: `frontend/src/hooks/use-auth.ts`

- [ ] **Step 1: Create auth hook with login/register/logout**

```typescript
// frontend/src/hooks/use-auth.ts
"use client";

import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/auth-store";
import { useTenantStore } from "@/lib/tenant-store";
import api from "@/lib/api";
import type { LoginRequest, RegisterRequest, TokenResponse, UserResponse } from "@/types/api";

export function useAuth() {
  const router = useRouter();
  const { setAuth, clearAuth, isAuthenticated, user, isLoading, getRefreshToken, setAccessToken } = useAuthStore();
  const { slug } = useTenantStore();

  async function login(data: LoginRequest) {
    const res = await api.post<TokenResponse>("/auth/login", data);
    const meRes = await api.get<UserResponse>("/auth/me", {
      headers: { Authorization: `Bearer ${res.data.access_token}` },
    });
    setAuth(res.data.access_token, res.data.refresh_token, meRes.data);
    router.push("/resources");
  }

  async function register(data: RegisterRequest) {
    const res = await api.post<TokenResponse>("/auth/register", data);
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

  return { login, register, logout, initAuth, isAuthenticated, user, isLoading };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/use-auth.ts
git commit -m "feat(frontend): add useAuth hook with login/register/logout/init"
```

---

### Task 7: Providers Wrapper

**Files:**
- Create: `frontend/src/components/providers.tsx`

- [ ] **Step 1: Create providers component**

```typescript
// frontend/src/components/providers.tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { Toaster } from "sonner";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30 * 1000,
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
        {children}
        <Toaster richColors position="top-right" />
      </ThemeProvider>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/providers.tsx
git commit -m "feat(frontend): add providers wrapper (react-query, theme, toaster)"
```

---

### Task 8: Root Layout and Tenant Middleware

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Create: `frontend/src/middleware.ts`

- [ ] **Step 1: Update root layout with providers**

```typescript
// frontend/src/app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "@/components/providers";
import "@/styles/globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "RentManager",
  description: "Multi-tenant rental management platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

- [ ] **Step 2: Create tenant resolution middleware**

```typescript
// frontend/src/middleware.ts
import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/login", "/register", "/_next", "/favicon.ico"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip public assets and auth pages
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // In development (localhost), expect path-based routing: /t/[slug]/...
  // In production (subdomain), rewrite subdomain to X-Tenant-Slug header
  const host = request.headers.get("host") || "";
  const isLocalhost = host.startsWith("localhost") || host.startsWith("127.0.0.1");

  let tenantSlug: string | null = null;

  if (isLocalhost) {
    // Dev: extract from path /t/[slug]/...
    const match = pathname.match(/^\/t\/([^/]+)(\/.*)?$/);
    if (match) {
      tenantSlug = match[1];
      // Rewrite to strip /t/[slug] prefix
      const rewrittenPath = match[2] || "/";
      const url = request.nextUrl.clone();
      url.pathname = rewrittenPath;
      const response = NextResponse.rewrite(url);
      response.headers.set("x-tenant-slug", tenantSlug);
      return response;
    }
  } else {
    // Production: extract subdomain
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

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/layout.tsx frontend/src/middleware.ts
git commit -m "feat(frontend): add root layout with providers and tenant middleware"
```

---

### Task 9: Admin Shell — Icon Rail

**Files:**
- Create: `frontend/src/components/shell/icon-rail.tsx`

- [ ] **Step 1: Create icon rail component**

```typescript
// frontend/src/components/shell/icon-rail.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Box,
  CalendarDays,
  Palette,
  Settings,
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
  { href: "/resources", icon: Box, label: "Resources" },
  { href: "/bookings", icon: CalendarDays, label: "Bookings" },
  { href: "/staff", icon: Users, label: "Staff" },
  { href: "/theming", icon: Palette, label: "Theming" },
  { href: "/settings", icon: Settings, label: "Settings" },
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
          className="flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground transition-colors"
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
git commit -m "feat(frontend): add icon rail navigation component"
```

---

### Task 10: Admin Shell — Sub-Nav

**Files:**
- Create: `frontend/src/components/shell/sub-nav.tsx`

- [ ] **Step 1: Create sub-nav component**

```typescript
// frontend/src/components/shell/sub-nav.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface SubNavItem {
  href: string;
  label: string;
}

interface SubNavSection {
  title: string;
  items: SubNavItem[];
  action?: { label: string; href: string };
}

const SUB_NAV_CONFIG: Record<string, SubNavSection> = {
  "/resources": {
    title: "Resources",
    items: [],
    action: { label: "+ Add Type", href: "/resources/new-type" },
  },
  "/bookings": {
    title: "Bookings",
    items: [
      { href: "/bookings", label: "All" },
      { href: "/bookings?status=pending", label: "Pending" },
      { href: "/bookings?status=confirmed", label: "Confirmed" },
      { href: "/bookings?status=active", label: "Active" },
      { href: "/bookings?status=completed", label: "Completed" },
      { href: "/bookings?status=cancelled", label: "Cancelled" },
    ],
  },
  "/theming": {
    title: "Theming",
    items: [
      { href: "/theming#brand", label: "Brand" },
      { href: "/theming#colors", label: "Colors" },
      { href: "/theming#typography", label: "Typography" },
      { href: "/theming#components", label: "Components" },
    ],
  },
  "/settings": {
    title: "Settings",
    items: [
      { href: "/settings#general", label: "General" },
      { href: "/settings#domains", label: "Domains" },
    ],
  },
};

export function SubNav() {
  const pathname = usePathname();

  // Find matching config based on pathname prefix
  const configKey = Object.keys(SUB_NAV_CONFIG).find((key) =>
    pathname.startsWith(key)
  );

  if (!configKey) return null;

  const config = SUB_NAV_CONFIG[configKey];

  return (
    <div className="flex h-full w-[220px] flex-col border-r bg-muted/30 p-4">
      <h2 className="mb-4 text-sm font-semibold">{config.title}</h2>

      {config.items.length > 0 && (
        <nav className="flex flex-col gap-1">
          {config.items.map((item) => {
            const isActive = pathname === item.href || (pathname + window?.location?.search) === item.href;
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
        <Link
          href={config.action.href}
          className="mt-4 text-sm text-primary hover:underline"
        >
          {config.action.label}
        </Link>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/shell/sub-nav.tsx
git commit -m "feat(frontend): add context-dependent sub-nav component"
```

---

### Task 11: Admin Shell — Header

**Files:**
- Create: `frontend/src/components/shell/header.tsx`

- [ ] **Step 1: Create header component with breadcrumb**

```typescript
// frontend/src/components/shell/header.tsx
"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { ChevronRight } from "lucide-react";

export function Header() {
  const pathname = usePathname();

  const segments = pathname.split("/").filter(Boolean);
  const breadcrumbs = segments.map((segment, index) => {
    const href = "/" + segments.slice(0, index + 1).join("/");
    const label = segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, " ");
    return { href, label };
  });

  return (
    <header className="flex h-14 items-center border-b px-6">
      <nav className="flex items-center gap-1 text-sm text-muted-foreground">
        {breadcrumbs.map((crumb, index) => (
          <span key={crumb.href} className="flex items-center gap-1">
            {index > 0 && <ChevronRight className="h-3 w-3" />}
            {index === breadcrumbs.length - 1 ? (
              <span className="font-medium text-foreground">{crumb.label}</span>
            ) : (
              <Link href={crumb.href} className="hover:text-foreground transition-colors">
                {crumb.label}
              </Link>
            )}
          </span>
        ))}
      </nav>
    </header>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/shell/header.tsx
git commit -m "feat(frontend): add header component with breadcrumb"
```

---

### Task 12: Admin Layout (Auth Guard + Shell Assembly)

**Files:**
- Create: `frontend/src/app/(admin)/layout.tsx`
- Create: `frontend/src/app/(admin)/page.tsx`

- [ ] **Step 1: Create admin layout with auth guard and shell**

```typescript
// frontend/src/app/(admin)/layout.tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { IconRail } from "@/components/shell/icon-rail";
import { SubNav } from "@/components/shell/sub-nav";
import { Header } from "@/components/shell/header";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading, initAuth } = useAuth();

  useEffect(() => {
    initAuth();
  }, []);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <IconRail />
      <SubNav />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create admin index page (redirects to resources)**

```typescript
// frontend/src/app/(admin)/page.tsx
import { redirect } from "next/navigation";

export default function AdminIndex() {
  redirect("/resources");
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(admin\)/layout.tsx frontend/src/app/\(admin\)/page.tsx
git commit -m "feat(frontend): add admin layout with auth guard and shell assembly"
```

---

### Task 13: Auth Pages — Login

**Files:**
- Create: `frontend/src/app/(auth)/login/page.tsx`

- [ ] **Step 1: Create login page**

```typescript
// frontend/src/app/(auth)/login/page.tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

const loginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { login } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);

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
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Login failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Sign in</CardTitle>
          <CardDescription>Enter your credentials to access the admin panel</CardDescription>
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
                <p className="text-sm text-destructive">{errors.email.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                {...register("password")}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "Signing in..." : "Sign in"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-primary hover:underline">
              Register
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/\(auth\)/login/page.tsx
git commit -m "feat(frontend): add login page with RHF + Zod validation"
```

---

### Task 14: Auth Pages — Register

**Files:**
- Create: `frontend/src/app/(auth)/register/page.tsx`

- [ ] **Step 1: Create register page**

```typescript
// frontend/src/app/(auth)/register/page.tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

const registerSchema = z.object({
  email: z.string().email("Invalid email address"),
  full_name: z.string().min(2, "Name must be at least 2 characters"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  phone: z.string().optional(),
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const { register: registerUser } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  async function onSubmit(data: RegisterForm) {
    setIsSubmitting(true);
    try {
      await registerUser(data);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Registration failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Create account</CardTitle>
          <CardDescription>Register to manage your rental business</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="full_name">Full Name</Label>
              <Input
                id="full_name"
                placeholder="John Doe"
                {...register("full_name")}
              />
              {errors.full_name && (
                <p className="text-sm text-destructive">{errors.full_name.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                {...register("email")}
              />
              {errors.email && (
                <p className="text-sm text-destructive">{errors.email.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">Phone (optional)</Label>
              <Input
                id="phone"
                placeholder="+1234567890"
                {...register("phone")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                {...register("password")}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "Creating account..." : "Create account"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="text-primary hover:underline">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/\(auth\)/register/page.tsx
git commit -m "feat(frontend): add register page with RHF + Zod validation"
```

---

### Task 15: Placeholder Module Pages

**Files:**
- Create: `frontend/src/app/(admin)/resources/page.tsx`
- Create: `frontend/src/app/(admin)/bookings/page.tsx`
- Create: `frontend/src/app/(admin)/staff/page.tsx`
- Create: `frontend/src/app/(admin)/theming/page.tsx`
- Create: `frontend/src/app/(admin)/settings/page.tsx`

- [ ] **Step 1: Create placeholder pages for all modules**

```typescript
// frontend/src/app/(admin)/resources/page.tsx
export default function ResourcesPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Resource Types</h1>
      <p className="mt-2 text-muted-foreground">Manage your resource types and resources.</p>
    </div>
  );
}
```

```typescript
// frontend/src/app/(admin)/bookings/page.tsx
export default function BookingsPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Bookings</h1>
      <p className="mt-2 text-muted-foreground">View and manage bookings.</p>
    </div>
  );
}
```

```typescript
// frontend/src/app/(admin)/staff/page.tsx
export default function StaffPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Staff</h1>
      <p className="mt-2 text-muted-foreground">Manage staff members and roles.</p>
    </div>
  );
}
```

```typescript
// frontend/src/app/(admin)/theming/page.tsx
export default function ThemingPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Theming</h1>
      <p className="mt-2 text-muted-foreground">Customize your brand appearance.</p>
    </div>
  );
}
```

```typescript
// frontend/src/app/(admin)/settings/page.tsx
export default function SettingsPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold">Settings</h1>
      <p className="mt-2 text-muted-foreground">Configure tenant settings.</p>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/\(admin\)/resources/ frontend/src/app/\(admin\)/bookings/ frontend/src/app/\(admin\)/staff/ frontend/src/app/\(admin\)/theming/ frontend/src/app/\(admin\)/settings/
git commit -m "feat(frontend): add placeholder pages for all admin modules"
```

---

### Task 16: Update Global CSS for shadcn/ui Theming

**Files:**
- Modify: `frontend/src/styles/globals.css`

- [ ] **Step 1: Update globals.css with CSS variables for dark/light mode**

```css
/* frontend/src/styles/globals.css */
@import "tailwindcss";

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    --primary: 210 40% 98%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 212.7 26.8% 83.9%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/styles/globals.css
git commit -m "feat(frontend): add shadcn/ui CSS variables for dark/light theme"
```

---

### Task 17: Landing Page Redirect and 404

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/app/not-found.tsx`

- [ ] **Step 1: Update landing page to redirect to admin**

```typescript
// frontend/src/app/page.tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/resources");
}
```

- [ ] **Step 2: Create 404 page**

```typescript
// frontend/src/app/not-found.tsx
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-4xl font-bold">404</h1>
      <p className="text-muted-foreground">Page not found</p>
      <Button asChild>
        <Link href="/resources">Go to Dashboard</Link>
      </Button>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/page.tsx frontend/src/app/not-found.tsx
git commit -m "feat(frontend): add landing redirect and 404 page"
```

---

### Task 18: Verify Full Build

- [ ] **Step 1: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No type errors.

- [ ] **Step 2: Run Next.js build**

```bash
cd frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 3: Manual smoke test**

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000` — should redirect to `/resources` (or to `/login` if auth guard triggers).
Open `http://localhost:3000/login` — should show login form.
Verify icon rail shows on `/resources` with all 5 module icons.
Verify theme toggle switches between dark/light.

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A frontend/
git commit -m "fix(frontend): resolve build issues from integration"
```
