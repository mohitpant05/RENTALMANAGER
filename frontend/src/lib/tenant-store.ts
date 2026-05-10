import { create } from "zustand";

const TENANT_SLUG_KEY = "rm_tenant_slug";

interface TenantState {
  slug: string | null;
  resolved: boolean;
  setSlug: (slug: string) => void;
  setResolved: () => void;
}

export const useTenantStore = create<TenantState>((set) => ({
  slug:
    typeof window !== "undefined"
      ? localStorage.getItem(TENANT_SLUG_KEY)
      : null,
  resolved: false,

  setSlug: (slug) => {
    if (typeof window !== "undefined") {
      localStorage.setItem(TENANT_SLUG_KEY, slug);
    }
    set({ slug, resolved: true });
  },

  setResolved: () => {
    set({ resolved: true });
  },
}));
