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
      ? "/admin"
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
    router.push("/admin");
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
