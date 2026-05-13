import { create } from "zustand";

const PLATFORM_TOKEN_KEY = "rm_platform_token";

interface PlatformAuthState {
  token: string | null;
  isAuthenticated: boolean;
  setToken: (token: string) => void;
  clearToken: () => void;
  loadToken: () => void;
}

export const usePlatformStore = create<PlatformAuthState>((set) => ({
  token: null,
  isAuthenticated: false,

  setToken: (token) => {
    localStorage.setItem(PLATFORM_TOKEN_KEY, token);
    set({ token, isAuthenticated: true });
  },

  clearToken: () => {
    localStorage.removeItem(PLATFORM_TOKEN_KEY);
    set({ token: null, isAuthenticated: false });
  },

  loadToken: () => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem(PLATFORM_TOKEN_KEY);
    if (token) {
      set({ token, isAuthenticated: true });
    }
  },
}));
