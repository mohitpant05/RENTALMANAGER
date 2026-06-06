"use client";

import { MoreHorizontal, ExternalLink } from "lucide-react";
import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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

function formatDateRange(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);

  const dateOpts: Intl.DateTimeFormatOptions = {
    month: "short",
    day: "numeric",
    year: "numeric",
  };
  const timeOpts: Intl.DateTimeFormatOptions = {
    hour: "numeric",
    minute: "2-digit",
  };

  const sameDay =
    s.getFullYear() === e.getFullYear() &&
    s.getMonth() === e.getMonth() &&
    s.getDate() === e.getDate();

  if (sameDay) {
    return `${s.toLocaleDateString(undefined, dateOpts)} ${s.toLocaleTimeString(undefined, timeOpts)} – ${e.toLocaleTimeString(undefined, timeOpts)}`;
  }

  return `${s.toLocaleDateString(undefined, dateOpts)} – ${e.toLocaleDateString(undefined, dateOpts)}`;
}

interface BookingTableProps {
  bookings: BookingResponse[];
  resourceNames: Record<string, string>;
  customerNames?: Record<string, string>;
}

export function BookingTable({ bookings, resourceNames, customerNames }: BookingTableProps) {
  if (bookings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <p className="text-muted-foreground">No bookings found</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Bookings will appear here once created
        </p>
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Booking ID</TableHead>
          <TableHead>Customer</TableHead>
          <TableHead>Resource</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>When</TableHead>
          <TableHead>Price</TableHead>
          <TableHead>Created</TableHead>
          <TableHead className="w-[50px]" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {bookings.map((b) => (
          <TableRow key={b.id}>
            <TableCell className="font-mono text-xs text-muted-foreground">
              {b.id.slice(0, 8)}
            </TableCell>
            <TableCell>
              <span className="text-sm">{customerNames?.[b.user_id] ?? b.user_id.slice(0, 8)}</span>
            </TableCell>
            <TableCell className="font-medium">
              <Link
                href={`/bookings/${b.id}`}
                className="hover:underline"
              >
                {resourceNames[b.resource_id] ?? b.resource_id.slice(0, 8)}
              </Link>
            </TableCell>
            <TableCell>
              <Badge variant={STATUS_VARIANT[b.status] ?? "muted"}>
                {b.status.replace(/_/g, " ")}
              </Badge>
            </TableCell>
            <TableCell>{formatDateRange(b.start_time, b.end_time)}</TableCell>
            <TableCell>
              {b.total_price.toFixed(2)} {b.currency}
            </TableCell>
            <TableCell className="text-muted-foreground">
              {new Date(b.created_at).toLocaleDateString()}
            </TableCell>
            <TableCell>
              <DropdownMenu>
                <DropdownMenuTrigger
                  render={
                    <Button variant="ghost" size="icon" className="h-8 w-8" />
                  }
                >
                  <MoreHorizontal className="h-4 w-4" />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    render={
                      <Link href={`/bookings/${b.id}`}>
                        <ExternalLink className="mr-2 h-4 w-4" />
                        View Details
                      </Link>
                    }
                  />
                </DropdownMenuContent>
              </DropdownMenu>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
