"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import type { ResourceTypeResponse } from "@/types/api";
import { useCreateTypeSheetStore } from "@/lib/create-type-sheet-store";

interface SubNavItem {
  href: string;
  label: string;
}

interface SubNavSection {
  title: string;
  items: SubNavItem[];
  action?: { label: string; href?: string; onClick?: () => void };
}

const STATIC_NAV_CONFIG: Record<string, SubNavSection> = {
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

function useResourceTypesNav(): SubNavSection | null {
  const setOpen = useCreateTypeSheetStore((s) => s.setOpen);
  const { data: types } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types");
      return data;
    },
    staleTime: 30_000,
  });

  if (!types) return { title: "Resources", items: [], action: { label: "+ Add Type", onClick: () => setOpen(true) } };

  return {
    title: "Resources",
    items: types.map((t) => ({ href: `/resources/${t.slug}`, label: t.name })),
    action: { label: "+ Add Type", onClick: () => setOpen(true) },
  };
}

export function SubNav() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const isResourcesSection = pathname.startsWith("/resources");
  const resourcesNav = useResourceTypesNav();

  const staticKey = Object.keys(STATIC_NAV_CONFIG).find((key) =>
    pathname.startsWith(key)
  );

  const config = isResourcesSection ? resourcesNav : staticKey ? STATIC_NAV_CONFIG[staticKey] : null;

  if (!config) return null;

  const currentUrl = searchParams.toString()
    ? `${pathname}?${searchParams.toString()}`
    : pathname;

  return (
    <div className="flex h-full w-[220px] flex-col border-r bg-muted/30 p-4">
      <h2 className="mb-4 text-sm font-semibold">{config.title}</h2>

      {config.items.length > 0 && (
        <nav className="flex flex-col gap-1">
          {config.items.map((item) => {
            const isActive = currentUrl === item.href || pathname === item.href;
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
        config.action.onClick ? (
          <button
            onClick={config.action.onClick}
            className="mt-4 text-sm text-primary hover:underline text-left"
          >
            {config.action.label}
          </button>
        ) : config.action.href ? (
          <Link
            href={config.action.href}
            className="mt-4 text-sm text-primary hover:underline"
          >
            {config.action.label}
          </Link>
        ) : null
      )}
    </div>
  );
}
