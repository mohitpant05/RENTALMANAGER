import { create } from "zustand";

interface TenantTheme {
  brand: Record<string, string>;
  colors: Record<string, string>;
  typography: Record<string, string | number>;
  components: Record<string, string | boolean>;
}

interface ThemeState {
  theme: TenantTheme | null;
  loaded: boolean;
  setTheme: (theme: TenantTheme) => void;
}

export const useThemeStore = create<ThemeState>((set) => ({
  theme: null,
  loaded: false,
  setTheme: (theme) => set({ theme, loaded: true }),
}));
