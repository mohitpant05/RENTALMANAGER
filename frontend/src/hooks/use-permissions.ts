"use client";

import { useAuthStore } from "@/lib/auth-store";
import { matchesPermission, canAccessRoute } from "@/lib/permissions";

export function usePermissions() {
  const { user, isAdmin } = useAuthStore();
  const permissions = user?.permissions ?? [];

  function hasPermission(codename: string): boolean {
    if (isAdmin()) return true;
    return matchesPermission(codename, permissions);
  }

  function hasAnyPermission(...codenames: string[]): boolean {
    if (isAdmin()) return true;
    return codenames.some((c) => matchesPermission(c, permissions));
  }

  function canAccessNav(route: string): boolean {
    if (isAdmin()) return true;
    return canAccessRoute(route, permissions);
  }

  return { hasPermission, hasAnyPermission, canAccessNav, isAdmin: isAdmin() };
}
