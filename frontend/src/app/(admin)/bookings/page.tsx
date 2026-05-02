"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { BookingResponse, ResourceResponse } from "@/types/api";
import { BookingTable } from "@/components/bookings/booking-table";

export default function BookingsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-24">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      }
    >
      <BookingsContent />
    </Suspense>
  );
}

function BookingsContent() {
  const searchParams = useSearchParams();
  const status = searchParams.get("status");

  const {
    data: bookings,
    isLoading: bookingsLoading,
  } = useQuery({
    queryKey: ["bookings", status],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (status) params.status = status;
      const { data } = await api.get<BookingResponse[]>("/bookings", { params });
      return data;
    },
  });

  const resourceIds = [
    ...new Set((bookings ?? []).map((b) => b.resource_id)),
  ];

  const {
    data: resourceNames,
    isLoading: resourcesLoading,
  } = useQuery({
    queryKey: ["resource-names", resourceIds],
    queryFn: async () => {
      const map: Record<string, string> = {};
      await Promise.all(
        resourceIds.map(async (id) => {
          try {
            const { data } = await api.get<ResourceResponse>(
              `/resources/${id}`,
            );
            map[id] = data.name;
          } catch {
            // Resource may have been deleted; fallback handled by table
          }
        }),
      );
      return map;
    },
    enabled: resourceIds.length > 0,
  });

  const isLoading = bookingsLoading || (resourceIds.length > 0 && resourcesLoading);

  return (
    <div className="flex-1 space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Bookings</h1>
        <p className="mt-1 text-muted-foreground">
          {status
            ? `Showing ${status} bookings`
            : "View and manage all bookings"}
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-24">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : (
        <BookingTable
          bookings={bookings ?? []}
          resourceNames={resourceNames ?? {}}
        />
      )}
    </div>
  );
}
