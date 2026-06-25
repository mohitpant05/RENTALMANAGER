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
  isStaff: () => boolean;
  isLister: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  user: null,
  isAuthenticated: false,
  isLoading: true,

  setAuth: (accessToken, refreshToken, user) => {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    document.cookie = `rm_auth=${user.user_type};path=/;max-age=604800;samesite=lax`;
    if (user.preferred_currency) {
      localStorage.setItem("rm_display_currency", user.preferred_currency);
    }
    set({ accessToken, user, isAuthenticated: true, isLoading: false });
  },

  setAccessToken: (token) => {
    set({ accessToken: token });
  },

  clearAuth: () => {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    document.cookie = "rm_auth=;path=/;max-age=0";
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

  isStaff: () => {
    const user = get().user;
    return user?.user_type === "staff";
  },

  isLister: () => {
    const user = get().user;
    return user?.user_type === "lister";
  },
}));
