"use client";

import { useAuthStore } from "@/lib/auth-store";
import { matchesPermission, canAccessRoute } from "@/lib/permissions";

const PERMISSION_SUPERSETS: Record<string, string[]> = {
  "bookings:*:manage": [
    "bookings:*:confirm",
    "bookings:*:reject",
    "bookings:*:cancel",
    "bookings:*:no_show",
  ],
};

function matchesPermissionWithSupersets(
  required: string,
  grantedSet: Set<string>
): boolean {
  if (matchesPermission(required, [...grantedSet])) return true;

  for (const [superset, subs] of Object.entries(PERMISSION_SUPERSETS)) {
    if (
      subs.includes(required) &&
      matchesPermission(superset, [...grantedSet])
    ) {
      return true;
    }
  }

  return false;
}

export function usePermissions() {
  const user = useAuthStore((s) => s.user);
  const isLoading = useAuthStore((s) => s.isLoading);
  const isAdmin = useAuthStore((s) => s.isAdmin);

  const permissions = user?.permissions ?? [];
  const permSet = new Set(permissions);

  function hasPermission(codename: string): boolean {
    if (isAdmin()) return true;
    return matchesPermissionWithSupersets(codename, permSet);
  }

  function hasAnyPermission(...codenames: string[]): boolean {
    if (isAdmin()) return true;
    return codenames.some((c) => matchesPermissionWithSupersets(c, permSet));
  }

  function canAccessNav(route: string): boolean {
    if (isAdmin()) return true;
    return canAccessRoute(route, permissions);
  }

  return { permissions, hasPermission, hasAnyPermission, canAccessNav, isLoading };
}
