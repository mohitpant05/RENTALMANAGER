"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { CalendarDays, ChevronDown, Package } from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { BookingResponse, ResourceResponse, AttachmentResponse } from "@/types/api";
import { BookingCardPublic } from "@/components/public/booking-card-public";
import { useFormatPrice } from "@/hooks/use-currency";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type Tab = "all" | "upcoming" | "active" | "past" | "cancelled";

const TABS: { value: Tab; label: string }[] = [
  { value: "all", label: "All" },
  { value: "upcoming", label: "Upcoming" },
  { value: "active", label: "Active" },
  { value: "past", label: "Past" },
  { value: "cancelled", label: "Cancelled" },
];

function filterBookings(bookings: BookingResponse[], tab: Tab): BookingResponse[] {
  const now = new Date();

  switch (tab) {
    case "upcoming":
      return bookings.filter(
        (b) =>
          (b.status === "pending" || b.status === "confirmed") &&
          new Date(b.start_time) > now
      );
    case "active":
      return bookings.filter((b) => b.status === "active");
    case "past":
      return bookings.filter((b) => b.status === "completed");
    case "cancelled":
      return bookings.filter((b) =>
        ["cancelled", "rejected", "no_show"].includes(b.status)
      );
    default:
      return bookings;
  }
}

type GroupedEntry =
  | { type: "individual"; booking: BookingResponse }
  | { type: "bundle"; groupId: string; primary: BookingResponse; addons: BookingResponse[] };

function groupBookings(bookings: BookingResponse[]): GroupedEntry[] {
  const groups = new Map<string, BookingResponse[]>();
  const individual: BookingResponse[] = [];

  for (const b of bookings) {
    if (b.booking_group_id) {
      const list = groups.get(b.booking_group_id) ?? [];
      list.push(b);
      groups.set(b.booking_group_id, list);
    } else {
      individual.push(b);
    }
  }

  const entries: GroupedEntry[] = [];

  for (const b of individual) {
    entries.push({ type: "individual", booking: b });
  }

  for (const [groupId, members] of groups) {
    const primary = members.find((m) => !m.parent_booking_id) ?? members[0];
    const addons = members.filter((m) => m.id !== primary.id);
    entries.push({ type: "bundle", groupId, primary, addons });
  }

  entries.sort((a, b) => {
    const dateA = a.type === "individual" ? a.booking.created_at : a.primary.created_at;
    const dateB = b.type === "individual" ? b.booking.created_at : b.primary.created_at;
    return new Date(dateB).getTime() - new Date(dateA).getTime();
  });

  return entries;
}

function BundleAccordion({
  entry,
  totalPrice,
  resourceNames,
  resourceImages,
}: {
  entry: Extract<GroupedEntry, { type: "bundle" }>;
  totalPrice: number;
  resourceNames: Record<string, string>;
  resourceImages: Record<string, string>;
}) {
  const [open, setOpen] = useState(false);
  const fmt = useFormatPrice();

  return (
    <div className="rounded-lg border">
      <div className="p-3">
        <div className="flex items-center gap-2 mb-2">
          <Package className="h-3.5 w-3.5 text-primary" />
          <span className="text-xs font-medium text-primary">Bundle</span>
          <span className="text-[10px] font-mono text-muted-foreground">
            {entry.groupId.slice(0, 8)}
          </span>
          <Badge variant="muted" className="ml-auto text-[10px]">
            {1 + entry.addons.length} items &middot; {fmt(totalPrice, entry.primary.currency)}
          </Badge>
        </div>
        <BookingCardPublic
          booking={entry.primary}
          resourceName={resourceNames[entry.primary.resource_id] ?? "Resource"}
          imageUrl={resourceImages[entry.primary.resource_id]}
        />
      </div>

      {entry.addons.length > 0 && (
        <>
          <button
            type="button"
            onClick={() => setOpen(!open)}
            className="flex w-full items-center justify-center gap-1 border-t px-3 py-2 text-xs font-medium text-muted-foreground hover:bg-muted/50 transition-colors"
          >
            <span>{open ? "Hide" : "Show"} {entry.addons.length} addon{entry.addons.length > 1 ? "s" : ""}</span>
            <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`} />
          </button>

          {open && (
            <div className="space-y-1.5 border-t p-3">
              {entry.addons.map((addon) => (
                <BookingCardPublic
                  key={addon.id}
                  booking={addon}
                  resourceName={resourceNames[addon.resource_id] ?? "Resource"}
                  imageUrl={resourceImages[addon.resource_id]}
                  isAddon
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function CustomerBookingsPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isLoading = useAuthStore((s) => s.isLoading);
  const [activeTab, setActiveTab] = useState<Tab>("all");

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login?returnUrl=/bookings");
    }
  }, [isLoading, isAuthenticated, router]);

  if (!isLoading && !isAuthenticated) {
    return null;
  }

  const { data: bookings, isLoading: bookingsLoading } = useQuery({
    queryKey: ["bookings"],
    queryFn: async () => {
      const { data } = await api.get<BookingResponse[]>("/bookings");
      return data;
    },
    enabled: isAuthenticated,
  });

  const resourceIds = [...new Set(bookings?.map((b) => b.resource_id) ?? [])];

  const { data: resources } = useQuery({
    queryKey: ["resources-by-ids", resourceIds],
    queryFn: async () => {
      const results = await Promise.all(
        resourceIds.map((id) =>
          api.get<ResourceResponse>(`/resources/${id}`).then((r) => r.data)
        )
      );
      return results;
    },
    enabled: resourceIds.length > 0,
  });

  const { data: allAttachments } = useQuery({
    queryKey: ["attachments-for-bookings", resourceIds],
    queryFn: async () => {
      const results = await Promise.all(
        resourceIds.map((id) =>
          api
            .get<AttachmentResponse[]>(
              `/storage/attachments?entity_type=resource&entity_id=${id}`
            )
            .then((r) => ({ resourceId: id, attachments: r.data }))
        )
      );
      return results;
    },
    enabled: resourceIds.length > 0,
  });

  const resourceNames: Record<string, string> = {};
  const resourceImages: Record<string, string> = {};

  resources?.forEach((r) => {
    resourceNames[r.id] = r.name;
  });

  allAttachments?.forEach(({ resourceId, attachments }) => {
    const first = attachments.find((a) => a.download_url);
    if (first?.download_url) {
      resourceImages[resourceId] = first.download_url;
    }
  });

  const filtered = filterBookings(bookings ?? [], activeTab);

  const grouped = groupBookings(filtered);

  if (isLoading || bookingsLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <h1 className="text-2xl font-bold">My Bookings</h1>

      <div className="mt-4 flex gap-1 overflow-x-auto border-b">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={`whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === tab.value
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="mt-6 space-y-3">
        {grouped.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16 text-center">
            <CalendarDays className="h-12 w-12 text-muted-foreground" />
            <p className="mt-3 text-muted-foreground">
              No bookings yet. Browse resources to get started!
            </p>
            <Button variant="outline" className="mt-4" onClick={() => router.push("/browse")}>
              Browse Resources
            </Button>
          </div>
        )}

        {grouped.map((entry) => {
          if (entry.type === "individual") {
            return (
              <BookingCardPublic
                key={entry.booking.id}
                booking={entry.booking}
                resourceName={resourceNames[entry.booking.resource_id] ?? "Resource"}
                imageUrl={resourceImages[entry.booking.resource_id]}
              />
            );
          }

          const totalPrice = [entry.primary, ...entry.addons].reduce((s, b) => s + b.total_price, 0);
          return (
            <BundleAccordion
              key={entry.groupId}
              entry={entry}
              totalPrice={totalPrice}
              resourceNames={resourceNames}
              resourceImages={resourceImages}
            />
          );
        })}
      </div>
    </div>
  );
}
