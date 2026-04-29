import { create } from "zustand";

const TENANT_SLUG_KEY = "rm_tenant_slug";

interface TenantState {
  slug: string | null;
  setSlug: (slug: string) => void;
}

export const useTenantStore = create<TenantState>((set) => ({
  slug:
    typeof window !== "undefined"
      ? localStorage.getItem(TENANT_SLUG_KEY)
      : null,

  setSlug: (slug) => {
    if (typeof window !== "undefined") {
      localStorage.setItem(TENANT_SLUG_KEY, slug);
    }
    set({ slug });
  },
}));
