"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";

interface SubNavItem {
  href: string;
  label: string;
}

interface SubNavSection {
  title: string;
  items: SubNavItem[];
  action?: { label: string; href: string };
}

const SUB_NAV_CONFIG: Record<string, SubNavSection> = {
  "/resources": {
    title: "Resources",
    items: [],
    action: { label: "+ Add Type", href: "/resources/new-type" },
  },
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

export function SubNav() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const configKey = Object.keys(SUB_NAV_CONFIG).find((key) =>
    pathname.startsWith(key)
  );

  if (!configKey) return null;

  const config = SUB_NAV_CONFIG[configKey];
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
        <Link
          href={config.action.href}
          className="mt-4 text-sm text-primary hover:underline"
        >
          {config.action.label}
        </Link>
      )}
    </div>
  );
}
