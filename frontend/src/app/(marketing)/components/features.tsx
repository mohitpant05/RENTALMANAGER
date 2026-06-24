import {
  Users,
  Layers,
  DollarSign,
  CreditCard,
  PieChart,
  CalendarCheck,
  Palette,
  BarChart3,
  FolderOpen,
  Clock,
  Star,
  Search,
  MapPin,
  Globe,
  PlusCircle,
  Zap,
  MessageSquare,
  FileText,
  Bot,
  Phone,
  BrainCircuit,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface Feature {
  icon: LucideIcon;
  title: string;
  description: string;
}

interface FeatureCategory {
  label: string;
  badge?: string;
  features: Feature[];
}

const CATEGORIES: FeatureCategory[] = [
  {
    label: "Admin Capabilities",
    features: [
      {
        icon: Users,
        title: "Staff & Role Management",
        description:
          "Add staff, assign roles (admin, staff, owner). Granular permissions.",
      },
      {
        icon: Layers,
        title: "Dynamic Resource Types",
        description:
          "Create custom resource types with flexible attribute schemas",
      },
      {
        icon: DollarSign,
        title: "Dynamic Pricing",
        description:
          "Configure pricing strategies — daily, hourly, seasonal, custom rules",
      },
      {
        icon: CreditCard,
        title: "Payment Gateways",
        description:
          "Multiple gateway support — Stripe, Razorpay, and more",
      },
      {
        icon: PieChart,
        title: "Commission & Payouts",
        description:
          "Set commission rates, track owner payouts, automated splits",
      },
      {
        icon: CalendarCheck,
        title: "Booking Management",
        description:
          "Full booking lifecycle — pending, confirmed, active, completed, cancelled",
      },
      {
        icon: Palette,
        title: "Theming & Branding",
        description:
          "Custom colors, logo, domain — each business gets own identity",
      },
      {
        icon: BarChart3,
        title: "Analytics Dashboard",
        description:
          "Track bookings, revenue, occupancy, performance metrics",
      },
    ],
  },
  {
    label: "Staff Capabilities",
    features: [
      {
        icon: FolderOpen,
        title: "Resource Management",
        description: "Manage assigned private and public resources",
      },
      {
        icon: Clock,
        title: "Booking & Availability",
        description: "Handle reservations, set availability windows",
      },
      {
        icon: Star,
        title: "Reviews & Ratings",
        description: "Monitor and respond to customer reviews",
      },
    ],
  },
  {
    label: "Public / Customer Features",
    features: [
      {
        icon: Search,
        title: "Resource Discovery",
        description:
          "Search & filter with Meilisearch-powered instant results",
      },
      {
        icon: MapPin,
        title: "Geofencing",
        description:
          "Location-based resource discovery with map integration",
      },
      {
        icon: Globe,
        title: "Dynamic Pricing Display",
        description:
          "Real-time pricing with multi-currency conversion",
      },
      {
        icon: PlusCircle,
        title: "Add-on Bookings",
        description: "Book extras alongside primary resource",
      },
      {
        icon: Zap,
        title: "Instant Booking",
        description: "Seamless booking flow — select, pay, confirm",
      },
      {
        icon: MessageSquare,
        title: "Reviews & Ratings",
        description: "Two-way review system (guest and owner)",
      },
      {
        icon: FileText,
        title: "Public Pages",
        description:
          "Auto-generated public storefront for each business",
      },
    ],
  },
  {
    label: "AI-Powered",
    badge: "Coming Soon",
    features: [
      {
        icon: Sparkles,
        title: "Personalized Recommendations",
        description:
          "AI suggests resources based on user history & preferences",
      },
      {
        icon: Bot,
        title: "Smart Chatbot",
        description:
          "24/7 customer support, booking assistance, FAQ handling",
      },
      {
        icon: Phone,
        title: "AI Dialer",
        description:
          "Automated phone bookings, confirmation calls, reminders",
      },
      {
        icon: BrainCircuit,
        title: "Intelligent Pricing",
        description: "AI-driven dynamic pricing optimization",
      },
    ],
  },
];

export function Features() {
  return (
    <section id="features" className="border-t bg-muted/30 py-16 sm:py-24">
      <div className="mx-auto max-w-6xl px-4">
        <h2 className="text-center text-3xl font-bold tracking-tight sm:text-4xl">
          Everything You Need
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-center text-muted-foreground">
          From admin controls to customer-facing pages — every feature your
          rental business needs, built in.
        </p>

        <div className="mt-16 space-y-16">
          {CATEGORIES.map((category) => (
            <div key={category.label}>
              <div className="mb-6 flex items-center gap-3">
                <h3 className="text-xl font-semibold">{category.label}</h3>
                {category.badge && (
                  <Badge variant="secondary">{category.badge}</Badge>
                )}
              </div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {category.features.map((feature) => (
                  <Card key={feature.title} size="sm">
                    <CardContent className="flex flex-col gap-2">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <feature.icon className="h-5 w-5 text-primary" />
                      </div>
                      <h4 className="text-sm font-semibold">{feature.title}</h4>
                      <p className="text-xs text-muted-foreground">
                        {feature.description}
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
