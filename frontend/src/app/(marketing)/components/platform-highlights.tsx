import {
  Shield,
  Globe,
  Smartphone,
  Bell,
  Search,
  HardDrive,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface Highlight {
  icon: LucideIcon;
  title: string;
  description: string;
}

const HIGHLIGHTS: Highlight[] = [
  {
    icon: Shield,
    title: "Multi-Tenant Architecture",
    description: "Each business gets isolated, secure workspace",
  },
  {
    icon: Globe,
    title: "Custom Domain Support",
    description: "Use your own domain — full white-label",
  },
  {
    icon: Smartphone,
    title: "Mobile Responsive",
    description: "Works on any device — desktop, tablet, phone",
  },
  {
    icon: Bell,
    title: "Real-Time Notifications",
    description: "Instant alerts for bookings, payments, reviews",
  },
  {
    icon: Search,
    title: "Instant Search",
    description: "Meilisearch-powered — typo-tolerant, fast, filterable",
  },
  {
    icon: HardDrive,
    title: "Secure File Storage",
    description: "S3-compatible storage with per-tenant isolation",
  },
];

export function PlatformHighlights() {
  return (
    <section className="border-t bg-muted/30 py-16 sm:py-24">
      <div className="mx-auto max-w-6xl px-4">
        <h2 className="text-center text-3xl font-bold tracking-tight sm:text-4xl">
          Why RentManager?
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-center text-muted-foreground">
          Built for scale, security, and speed from day one.
        </p>

        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {HIGHLIGHTS.map((h) => (
            <div
              key={h.title}
              className="flex items-start gap-4 rounded-lg border bg-card p-5"
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                <h.icon className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h3 className="text-sm font-semibold">{h.title}</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {h.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
