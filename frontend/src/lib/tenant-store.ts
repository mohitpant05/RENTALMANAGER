import { create } from "zustand";

const TENANT_SLUG_KEY = "rm_tenant_slug";

interface TenantState {
  slug: string | null;
  resolved: boolean;
  landingPage: "browse" | "marketing";
  setSlug: (slug: string, landingPage?: "browse" | "marketing") => void;
  setResolved: () => void;
}

export const useTenantStore = create<TenantState>((set) => ({
  slug:
    typeof window !== "undefined"
      ? localStorage.getItem(TENANT_SLUG_KEY)
      : null,
  resolved: false,
  landingPage: "browse",

  setSlug: (slug, landingPage = "browse") => {
    if (typeof window !== "undefined") {
      localStorage.setItem(TENANT_SLUG_KEY, slug);
    }
    set({ slug, resolved: true, landingPage });
  },

  setResolved: () => {
    set({ resolved: true });
  },
}));
