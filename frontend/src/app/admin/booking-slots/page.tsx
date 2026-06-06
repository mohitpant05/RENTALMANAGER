"use client";

import { Suspense, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  CalendarDays,
  Clock,
  Search,
  X,
} from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";
import type { AvailabilitySlotResponse, ResourceTypeResponse } from "@/types/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const STATUS_VARIANT: Record<string, "default" | "warning" | "outline" | "secondary" | "destructive" | "success" | "muted"> = {
  booked: "default",
  held: "warning",
};

export default function BookingSlotsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-24">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      }
    >
      <BookingSlotsContent />
    </Suspense>
  );
}

function BookingSlotsContent() {
  const today = new Date().toISOString().split("T")[0];
  const [selectedDate, setSelectedDate] = useState(today);
  const [selectedTypeId, setSelectedTypeId] = useState<string>("");
  const [searchInput, setSearchInput] = useState("");

  const { data: types } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types");
      return data;
    },
    staleTime: 30_000,
  });

  const startDate = `${selectedDate}T00:00:00Z`;
  const endDate = `${selectedDate}T23:59:59Z`;

  const search = searchInput.trim();

  const { data: slots, isLoading } = useQuery({
    queryKey: ["availability-slots", selectedDate, selectedTypeId, search],
    queryFn: async () => {
      const params: Record<string, string> = {
        start_date: startDate,
        end_date: endDate,
        limit: "500",
      };
      if (selectedTypeId) params.resource_type_id = selectedTypeId;
      if (search) params.search = search;
      const { data } = await api.get<AvailabilitySlotResponse[]>(
        "/resources/availability/slots",
        { params }
      );
      return data;
    },
  });

  function goToDay(delta: number) {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + delta);
    setSelectedDate(d.toISOString().split("T")[0]);
  }

  function formatTime(iso: string) {
    return new Date(iso).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  const grouped = (slots ?? []).reduce(
    (acc, s) => {
      if (!acc[s.resource_id]) acc[s.resource_id] = { name: s.resource_name, type: s.resource_type_name, slots: [] };
      acc[s.resource_id].slots.push(s);
      return acc;
    },
    {} as Record<string, { name: string; type: string; slots: AvailabilitySlotResponse[] }>,
  );

  return (
    <div className="flex-1 space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Booking Slots</h1>
        <p className="mt-1 text-muted-foreground">
          Daily view of booked and held time slots across all resources
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => goToDay(-1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="relative">
            <CalendarDays className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-48 pl-9"
            />
          </div>
          <Button variant="outline" size="icon" onClick={() => goToDay(1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedDate(today)}
          >
            Today
          </Button>
        </div>

        <Select value={selectedTypeId} onValueChange={setSelectedTypeId}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All types</SelectItem>
            {types?.map((t) => (
              <SelectItem key={t.id} value={t.id}>
                {t.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by resource or customer name..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-9 pr-8"
          />
          {searchInput && (
            <button
              onClick={() => setSearchInput("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      <div className="text-sm text-muted-foreground">
        {new Date(selectedDate).toLocaleDateString("en-US", {
          weekday: "long",
          year: "numeric",
          month: "long",
          day: "numeric",
        })}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-24">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : slots?.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed py-24 text-muted-foreground">
          <CalendarDays className="mb-2 h-12 w-12" />
          <p className="text-lg font-medium">No slots for this day</p>
          <p className="text-sm">Try selecting a different date or resource type</p>
        </div>
      ) : (
        <div className="space-y-8">
          {Object.entries(grouped).map(([resourceId, group]) => (
            <div key={resourceId}>
              <div className="mb-3 flex items-center gap-2">
                <h3 className="text-lg font-semibold">{group.name}</h3>
                <Badge variant="outline" className="text-xs">
                  {group.type}
                </Badge>
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[120px]">Time</TableHead>
                    <TableHead className="w-[100px]">Status</TableHead>
                    <TableHead>Customer</TableHead>
                    <TableHead className="w-[100px]">Booking</TableHead>
                    <TableHead>Hold Token</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {group.slots.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="font-mono text-sm">
                        <span className="inline-flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatTime(s.start_time)} – {formatTime(s.end_time)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge variant={STATUS_VARIANT[s.status] ?? "muted"}>
                          {s.status}
                          {s.status === "held" &&
                            ` (exp ${new Date(s.hold_expires ?? "").toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })})`}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">
                        {s.customer_name ?? <span className="text-muted-foreground">—</span>}
                      </TableCell>
                      <TableCell>
                        {s.booking_id ? (
                          <Link
                            href={`/bookings/${s.booking_id}`}
                            className="text-primary hover:underline text-sm"
                          >
                            {s.booking_id.slice(0, 8)}
                          </Link>
                        ) : (
                          <span className="text-muted-foreground text-sm">—</span>
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {s.hold_token ?? "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
