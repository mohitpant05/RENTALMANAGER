"use client";

import Link from "next/link";
import { CalendarDays, Image as ImageIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { BookingResponse } from "@/types/api";

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

interface BookingCardPublicProps {
  booking: BookingResponse;
  resourceName: string;
  imageUrl?: string;
}

function formatDateRange(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  const opts: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "numeric",
    year: "numeric",
  };
  const sameDay = s.toLocaleDateString() === e.toLocaleDateString();
  if (sameDay) {
    return `${s.toLocaleDateString(undefined, opts)}, ${s.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} – ${e.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  }
  return `${s.toLocaleDateString(undefined, opts)} – ${e.toLocaleDateString(undefined, opts)}`;
}

export function BookingCardPublic({
  booking,
  resourceName,
  imageUrl,
}: BookingCardPublicProps) {
  return (
    <Link href={`/bookings/${booking.id}`}>
      <Card className="transition-colors hover:bg-muted/50">
        <CardContent className="flex gap-4 p-4">
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={resourceName}
              className="h-20 w-20 shrink-0 rounded-lg object-cover"
            />
          ) : (
            <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-lg bg-muted">
              <ImageIcon className="h-8 w-8 text-muted-foreground" />
            </div>
          )}

          <div className="flex flex-1 flex-col justify-between min-w-0">
            <div>
              <div className="flex items-center justify-between gap-2">
                <Link
                  href={`/resources/${booking.resource_id}`}
                  className="truncate font-medium hover:underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  {resourceName}
                </Link>
                <Badge variant={STATUS_VARIANT[booking.status] ?? "muted"} className="shrink-0">
                  {booking.status.replace(/_/g, " ")}
                </Badge>
              </div>

              <div className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
                <CalendarDays className="h-3.5 w-3.5" />
                <span>{formatDateRange(booking.start_time, booking.end_time)}</span>
              </div>
            </div>

            <div className="mt-2 text-sm font-semibold">
              {booking.currency} {booking.total_price.toFixed(2)}
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
