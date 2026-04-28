import { create } from "zustand";

interface TenantState {
  slug: string | null;
  setSlug: (slug: string) => void;
}

export const useTenantStore = create<TenantState>((set) => ({
  slug: null,
  setSlug: (slug) => set({ slug }),
}));
