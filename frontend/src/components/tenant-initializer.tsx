"use client";

import { useEffect } from "react";
import { useTenantStore } from "@/lib/tenant-store";

async function resolveTenantByDomain(domain: string) {
  const res = await fetch(`/api/tenancy/resolve?domain=${encodeURIComponent(domain)}`);
  if (!res.ok) return null;
  const data = await res.json();
  return data;
}

export function TenantInitializer() {
  const setSlug = useTenantStore((s) => s.setSlug);
  const setResolved = useTenantStore((s) => s.setResolved);

  useEffect(() => {
    const host = window.location.hostname;

    async function init() {
      const resolved = await resolveTenantByDomain(host);
      if (resolved?.slug) {
        setSlug(resolved.slug);
        return;
      }

      const isLocalhost = host === "localhost" || host === "127.0.0.1";
      if (isLocalhost) {
        const match = window.location.pathname.match(/^\/t\/([^/]+)/);
        if (match) {
          setSlug(match[1]);
          return;
        }
      }

      setResolved();
    }

    init();
  }, [setSlug, setResolved]);

  return null;
}
