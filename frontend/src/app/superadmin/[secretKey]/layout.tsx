"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter, usePathname } from "next/navigation";
import { usePlatformStore } from "@/lib/platform-store";
import { useValidateKey } from "@/hooks/use-platform";

export default function SuperadminLayout({ children }: { children: React.ReactNode }) {
  const params = useParams<{ secretKey: string }>();
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, loadToken } = usePlatformStore();
  const validateKey = useValidateKey();
  const [keyValid, setKeyValid] = useState<boolean | null>(null);

  useEffect(() => {
    loadToken();
  }, [loadToken]);

  useEffect(() => {
    if (!params.secretKey) return;
    validateKey.mutate(decodeURIComponent(params.secretKey), {
      onSuccess: () => setKeyValid(true),
      onError: () => setKeyValid(false),
    });
  }, [params.secretKey]);

  useEffect(() => {
    if (keyValid === false) {
      router.replace("/not-found");
    }
  }, [keyValid, router]);

  useEffect(() => {
    if (keyValid && !isAuthenticated && !pathname.endsWith("/login")) {
      router.replace(`/superadmin/${params.secretKey}/login`);
    }
  }, [keyValid, isAuthenticated, pathname, params.secretKey, router]);

  if (keyValid === null) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (keyValid === false) return null;

  return (
    <div className="min-h-screen bg-background">
      {isAuthenticated && !pathname.endsWith("/login") ? (
        <div className="flex h-screen">
          <SuperadminSidebar secretKey={params.secretKey} />
          <main className="flex-1 overflow-y-auto p-6">{children}</main>
        </div>
      ) : (
        children
      )}
    </div>
  );
}

function SuperadminSidebar({ secretKey }: { secretKey: string }) {
  const pathname = usePathname();
  const { clearToken } = usePlatformStore();
  const router = useRouter();
  const base = `/superadmin/${secretKey}`;

  const links = [
    { href: `${base}/dashboard`, label: "Dashboard" },
    { href: `${base}/tenants`, label: "Tenants" },
    { href: `${base}/settings`, label: "Settings" },
  ];

  return (
    <nav className="flex w-56 flex-col border-r bg-card p-4">
      <h2 className="mb-6 text-lg font-semibold">Platform Admin</h2>
      <div className="flex flex-1 flex-col gap-1">
        {links.map((link) => (
          <a
            key={link.href}
            href={link.href}
            className={`rounded-md px-3 py-2 text-sm transition-colors ${
              pathname.startsWith(link.href)
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent/50"
            }`}
          >
            {link.label}
          </a>
        ))}
      </div>
      <button
        onClick={() => {
          clearToken();
          router.replace(`/superadmin/${secretKey}/login`);
        }}
        className="mt-auto rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-destructive/10"
      >
        Logout
      </button>
    </nav>
  );
}
