import {
  Building2,
  Car,
  Wrench,
  LayoutGrid,
  ChefHat,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

const VERTICALS = [
  {
    icon: Building2,
    title: "Vacation & Property Rentals",
    tagline: "Manage listings, availability, and guest bookings",
  },
  {
    icon: Car,
    title: "Vehicle Rental",
    tagline: "Fleet management, dynamic pricing, instant booking",
  },
  {
    icon: Wrench,
    title: "Equipment Rental",
    tagline: "Inventory tracking, add-ons, maintenance scheduling",
  },
  {
    icon: LayoutGrid,
    title: "Space & Venue Rental",
    tagline: "Room booking, time slots, capacity management",
  },
  {
    icon: ChefHat,
    title: "Service Providers",
    tagline: "Staff scheduling, service packages, customer matching",
  },
];

export function Verticals() {
  return (
    <section className="border-t py-16 sm:py-24">
      <div className="mx-auto max-w-6xl px-4">
        <h2 className="text-center text-3xl font-bold tracking-tight sm:text-4xl">
          Built For Your Industry
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-center text-muted-foreground">
          One platform, five industries. Configure it for your specific rental
          business.
        </p>
        <div className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {VERTICALS.map((v) => (
            <Card key={v.title} className="text-center">
              <CardContent className="flex flex-col items-center gap-3 pt-6">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                  <v.icon className="h-6 w-6 text-primary" />
                </div>
                <h3 className="text-sm font-semibold">{v.title}</h3>
                <p className="text-xs text-muted-foreground">{v.tagline}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
