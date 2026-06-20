"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { CalendarDays } from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { BookingResponse, ResourceResponse, AttachmentResponse } from "@/types/api";
import { BookingCardPublic } from "@/components/public/booking-card-public";
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

export default function CustomerBookingsPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isLoading = useAuthStore((s) => s.isLoading);
  const [activeTab, setActiveTab] = useState<Tab>("all");

  if (!isLoading && !isAuthenticated) {
    router.push("/login?returnUrl=/bookings");
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
        {filtered.length === 0 && (
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

        {filtered.map((booking) => (
          <BookingCardPublic
            key={booking.id}
            booking={booking}
            resourceName={resourceNames[booking.resource_id] ?? "Resource"}
            imageUrl={resourceImages[booking.resource_id]}
          />
        ))}
      </div>
    </div>
  );
}
