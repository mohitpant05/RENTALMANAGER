export const NAV_PERMISSION_MAP: Record<string, string[]> = {
  "/admin": [],
  "/admin/resources": ["resources:*:read", "resources:*:manage"],
  "/admin/bookings": ["bookings:*:read", "bookings:*:manage"],
  "/admin/customers": ["customers:*:read", "customers:*:manage"],
  "/admin/booking-slots": ["bookings:*:read", "bookings:*:manage"],
  "/admin/payouts": ["settings:*:manage"],
  "/admin/refunds": ["settings:*:manage"],
  "/admin/reviews": ["reviews:*:read", "reviews:*:moderate"],
  "/admin/staff": ["staff:*:manage", "staff:*:invite"],
  "/admin/notifications": [],
  "/admin/theming": ["theme:*:read", "theme:*:edit"],
  "/admin/settings": ["settings:*:manage"],
};

export const PERMISSION_DOMAIN_LABELS: Record<string, string> = {
  resources: "Resources",
  bookings: "Bookings",
  reviews: "Reviews",
  staff: "Staff",
  pricing: "Pricing",
  theme: "Theming",
  analytics: "Analytics",
  settings: "Settings",
  resource_types: "Resource Types",
  customers: "Customers",
  listers: "Listers",
};

export function matchesPermission(
  required: string,
  granted: string[]
): boolean {
  const grantedSet = new Set(granted);
  if (grantedSet.has("*:*:*")) return true;
  if (grantedSet.has(required)) return true;

  const parts = required.split(":");
  if (parts.length !== 3) return false;
  const [domain, qualifier, action] = parts;
  const candidates = [
    `${domain}:*:${action}`,
    `${domain}:${qualifier}:*`,
    `${domain}:*:*`,
    "*:*:*",
  ];
  return candidates.some((c) => grantedSet.has(c));
}

export function canAccessRoute(
  route: string,
  permissions: string[]
): boolean {
  const requiredPerms = NAV_PERMISSION_MAP[route];
  if (!requiredPerms || requiredPerms.length === 0) return true;
  return requiredPerms.some((p) => matchesPermission(p, permissions));
}
