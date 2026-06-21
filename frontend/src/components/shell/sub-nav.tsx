"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import type { ResourceTypeResponse } from "@/types/api";
import { useCreateTypeSheetStore } from "@/lib/create-type-sheet-store";
import { usePermissions } from "@/hooks/use-permissions";

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
  "/admin/bookings": {
    title: "Bookings",
    items: [
      { href: "/admin/bookings", label: "All" },
      { href: "/admin/bookings?status=pending", label: "Pending" },
      { href: "/admin/bookings?status=confirmed", label: "Confirmed" },
      { href: "/admin/bookings?status=active", label: "Active" },
      { href: "/admin/bookings?status=completed", label: "Completed" },
      { href: "/admin/bookings?status=cancelled", label: "Cancelled" },
    ],
  },
  "/admin/reviews": {
    title: "Reviews",
    items: [
      { href: "/admin/reviews", label: "All" },
      { href: "/admin/reviews?status=pending", label: "Pending Moderation" },
      { href: "/admin/reviews?status=approved", label: "Approved" },
      { href: "/admin/reviews?status=rejected", label: "Rejected" },
    ],
  },
  "/admin/notifications": {
    title: "Notifications",
    items: [
      { href: "/admin/notifications", label: "All" },
      { href: "/admin/notifications?unread=true", label: "Unread" },
    ],
  },
  "/admin/theming": {
    title: "Theming",
    items: [
      { href: "/admin/theming#brand", label: "Brand" },
      { href: "/admin/theming#colors", label: "Colors" },
      { href: "/admin/theming#typography", label: "Typography" },
      { href: "/admin/theming#components", label: "Components" },
    ],
  },
  "/admin/payouts": {
    title: "Payouts",
    items: [
      { href: "/admin/payouts", label: "Balances" },
      { href: "/admin/payouts?tab=history", label: "History" },
    ],
  },
  "/admin/staff": {
    title: "Staff",
    items: [
      { href: "/admin/staff", label: "Members" },
      { href: "/admin/staff/roles", label: "Roles & Permissions" },
    ],
  },
  "/admin/settings": {
    title: "Settings",
    items: [
      { href: "/admin/settings", label: "General" },
      { href: "/admin/settings/commission", label: "Commission" },
      { href: "/admin/settings/email", label: "Email / SMTP" },
      { href: "/admin/settings/payments", label: "Payments" },
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
    items: types.map((t) => ({ href: `/admin/resources/${t.slug}`, label: t.name })),
    action: { label: "+ Add Type", onClick: () => setOpen(true) },
  };
}

export function SubNav() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const isResourcesSection = pathname.startsWith("/admin/resources");
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
            const isHashLink = item.href.includes("#") && item.href.startsWith(pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={isHashLink ? () => {
                  const hash = item.href.split("#")[1];
                  if (window.location.hash === `#${hash}`) {
                    window.dispatchEvent(new HashChangeEvent("hashchange"));
                  }
                } : undefined}
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
