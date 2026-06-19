import { Settings, Rocket, LayoutDashboard } from "lucide-react";
import type { LucideIcon } from "lucide-react";

interface Step {
  number: number;
  icon: LucideIcon;
  title: string;
  description: string;
}

const STEPS: Step[] = [
  {
    number: 1,
    icon: Settings,
    title: "Set Up",
    description:
      "Create your account, add resources, configure pricing and payment gateways.",
  },
  {
    number: 2,
    icon: Rocket,
    title: "Go Live",
    description:
      "Your public storefront is auto-generated. Customers discover and book instantly.",
  },
  {
    number: 3,
    icon: LayoutDashboard,
    title: "Manage",
    description:
      "Admin panel handles bookings, payouts, staff, reviews — everything in one place.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="border-t py-16 sm:py-24">
      <div className="mx-auto max-w-6xl px-4">
        <h2 className="text-center text-3xl font-bold tracking-tight sm:text-4xl">
          How It Works
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-center text-muted-foreground">
          Three steps from sign-up to running your rental business.
        </p>

        <div className="relative mt-16 grid gap-8 sm:grid-cols-3">
          <div className="absolute left-0 right-0 top-8 hidden h-px bg-border sm:block" />

          {STEPS.map((step) => (
            <div key={step.number} className="relative text-center">
              <div className="relative mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-primary text-primary-foreground">
                <span className="absolute -right-1 -top-1 flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs font-bold text-foreground ring-2 ring-background">
                  {step.number}
                </span>
                <step.icon className="h-7 w-7" />
              </div>
              <h3 className="text-lg font-semibold">{step.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
