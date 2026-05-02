"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Calendar, Clock, DollarSign } from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";
import type { BookingResponse, ResourceResponse } from "@/types/api";
import { Badge } from "@/components/ui/badge";
import { BookingActions } from "@/components/bookings/booking-actions";

const STATUS_VARIANT: Record<
  string,
  "muted" | "success" | "warning" | "destructive" | "default"
> = {
  pending: "warning",
  confirmed: "default",
  active: "success",
  completed: "muted",
  cancelled: "destructive",
  rejected: "destructive",
  no_show: "destructive",
};

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function BookingDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: booking, isLoading } = useQuery({
    queryKey: ["booking", id],
    queryFn: async () => {
      const { data } = await api.get<BookingResponse>(`/bookings/${id}`);
      return data;
    },
    enabled: !!id,
  });

  const { data: resource } = useQuery({
    queryKey: ["resource", booking?.resource_id],
    queryFn: async () => {
      const { data } = await api.get<ResourceResponse>(
        `/resources/${booking!.resource_id}`
      );
      return data;
    },
    enabled: !!booking?.resource_id,
  });

  if (isLoading || !booking) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  const hasDetails =
    booking.notes ||
    booking.cancellation_reason ||
    booking.confirmed_at ||
    booking.cancelled_at;

  return (
    <div className="flex-1 space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          href="/bookings"
          className="rounded-md p-1 hover:bg-accent"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">
              {resource?.name ?? "Booking"}
            </h1>
            <Badge variant={STATUS_VARIANT[booking.status] ?? "muted"}>
              {booking.status.replace(/_/g, " ")}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {booking.id.slice(0, 8)}
          </p>
        </div>
        <BookingActions booking={booking} />
      </div>

      {/* Two-column grid */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Schedule card */}
        <div className="space-y-4 rounded-lg border p-6">
          <h2 className="text-sm font-semibold text-muted-foreground">
            Schedule
          </h2>
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2 text-sm text-muted-foreground">
              <Calendar className="h-4 w-4" />
              Start
            </span>
            <span className="text-sm font-medium">
              {formatDateTime(booking.start_time)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              End
            </span>
            <span className="text-sm font-medium">
              {formatDateTime(booking.end_time)}
            </span>
          </div>
        </div>

        {/* Payment card */}
        <div className="space-y-4 rounded-lg border p-6">
          <h2 className="text-sm font-semibold text-muted-foreground">
            Payment
          </h2>
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2 text-sm text-muted-foreground">
              <DollarSign className="h-4 w-4" />
              Total Price
            </span>
            <span className="text-sm font-medium">
              {booking.total_price.toFixed(2)} {booking.currency}
            </span>
          </div>
          {booking.refund_percent != null && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                Refund Percent
              </span>
              <span className="text-sm font-medium">
                {booking.refund_percent}%
              </span>
            </div>
          )}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Auto-Confirm</span>
            <span className="text-sm font-medium">
              {booking.auto_confirm ? "Yes" : "No"}
            </span>
          </div>
        </div>
      </div>

      {/* Details card (conditional) */}
      {hasDetails && (
        <div className="space-y-4 rounded-lg border p-6">
          <h2 className="text-sm font-semibold text-muted-foreground">
            Details
          </h2>
          {booking.notes && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Notes</span>
              <span className="text-sm font-medium">{booking.notes}</span>
            </div>
          )}
          {booking.confirmed_at && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Confirmed</span>
              <span className="text-sm font-medium">
                {formatDateTime(booking.confirmed_at)}
              </span>
            </div>
          )}
          {booking.cancelled_at && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Cancelled</span>
              <span className="text-sm font-medium">
                {formatDateTime(booking.cancelled_at)}
              </span>
            </div>
          )}
          {booking.cancellation_reason && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                Cancellation Reason
              </span>
              <span className="text-sm font-medium">
                {booking.cancellation_reason}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
