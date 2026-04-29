"use client";

import { useEffect } from "react";
import { useTenantStore } from "@/lib/tenant-store";

export function TenantInitializer() {
  const setSlug = useTenantStore((s) => s.setSlug);

  useEffect(() => {
    const host = window.location.hostname;
    const isLocalhost = host === "localhost" || host === "127.0.0.1";

    if (isLocalhost) {
      const match = window.location.pathname.match(/^\/t\/([^/]+)/);
      if (match) {
        setSlug(match[1]);
      }
    } else {
      const parts = host.split(".");
      if (parts.length >= 3) {
        setSlug(parts[0]);
      }
    }
  }, [setSlug]);

  return null;
}
