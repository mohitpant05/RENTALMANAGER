"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useTenantStore } from "@/lib/tenant-store";
import { Hero } from "./components/hero";
import { Verticals } from "./components/verticals";
import { Features } from "./components/features";
import { HowItWorks } from "./components/how-it-works";
import { PlatformHighlights } from "./components/platform-highlights";
import { CtaBanner } from "./components/cta-banner";
import { Footer } from "./components/footer";

export default function MarketingPage() {
  const router = useRouter();
  const resolved = useTenantStore((s) => s.resolved);
  const slug = useTenantStore((s) => s.slug);
  const landingPage = useTenantStore((s) => s.landingPage);

  const shouldRedirect = resolved && !!slug && landingPage === "browse";

  useEffect(() => {
    if (shouldRedirect) {
      router.replace("/browse");
    }
  }, [shouldRedirect, router]);

  if (!resolved || shouldRedirect) return null;

  return (
    <main>
      <Hero />
      <Verticals />
      <Features />
      <HowItWorks />
      <PlatformHighlights />
      <CtaBanner />
      <Footer />
    </main>
  );
}
