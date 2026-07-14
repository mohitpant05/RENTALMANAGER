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

  useEffect(() => {
    if (resolved && slug) {
      router.replace("/browse");
    }
  }, [resolved, slug, router]);

  if (resolved && slug) return null;

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
