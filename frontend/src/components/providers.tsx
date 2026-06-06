"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { Toaster } from "sonner";
import { useEffect, useState } from "react";
import { TenantInitializer } from "@/components/tenant-initializer";
import { useAuthStore } from "@/lib/auth-store";
import api from "@/lib/api";
import type { TokenResponse, UserResponse } from "@/types/api";

function AuthInitializer() {
  useEffect(() => {
    const refreshToken = localStorage.getItem("rm_refresh_token");
    if (!refreshToken) {
      useAuthStore.getState().clearAuth();
      return;
    }

    useAuthStore.setState({ isLoading: true });

    api
      .post<TokenResponse>("/auth/refresh", { refresh_token: refreshToken })
      .then((res) =>
        api.get<UserResponse>("/auth/me", {
          headers: { Authorization: `Bearer ${res.data.access_token}` },
        }).then((meRes) => {
          useAuthStore.getState().setAuth(
            res.data.access_token,
            res.data.refresh_token,
            meRes.data
          );
        })
      )
      .catch(() => {
        useAuthStore.getState().clearAuth();
      });
  }, []);

  return null;
}

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
        <AuthInitializer />
        <TenantInitializer />
      </ThemeProvider>
    </QueryClientProvider>
  );
}
