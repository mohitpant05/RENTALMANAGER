"use client";

import { useState, useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useDemoRequests,
  useDemoCalendar,
  useUpdateDemoStatus,
  type CalendarSlot,
  type DemoRequest,
} from "@/hooks/use-demo-requests";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  confirmed: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
};

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "UTC",
  });
}

function formatDateLabel(isoDate: string) {
  const d = new Date(isoDate + "T00:00:00Z");
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

function formatDateFull(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function groupByDate(slots: CalendarSlot[]) {
  const grouped: Record<string, CalendarSlot[]> = {};
  for (const slot of slots) {
    const dateKey = slot.start.slice(0, 10);
    if (!grouped[dateKey]) grouped[dateKey] = [];
    grouped[dateKey].push(slot);
  }
  return grouped;
}

export default function DemoRequestsPage() {
  const { data: requests, isLoading: requestsLoading } = useDemoRequests();
  const { data: calendar, isLoading: calendarLoading } = useDemoCalendar();
  const updateStatus = useUpdateDemoStatus();
  const [tab, setTab] = useState<"calendar" | "requests">("calendar");
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");

  const calendarGrouped = useMemo(
    () => (calendar ? groupByDate(calendar) : {}),
    [calendar]
  );
  const calendarDates = Object.keys(calendarGrouped).sort();

  const selectedSlots = selectedDate ? calendarGrouped[selectedDate] ?? [] : [];
  const bookedCount = selectedSlots.filter((s) => s.status === "booked").length;
  const availableCount = selectedSlots.filter((s) => s.status === "available").length;

  const filtered =
    filter === "all"
      ? requests
      : requests?.filter((r) => r.status === filter);

  const counts = requests?.reduce(
    (acc, r) => {
      acc[r.status] = (acc[r.status] || 0) + 1;
      acc.all = (acc.all || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Demo Requests</h1>
          <p className="text-muted-foreground">
            Manage demo bookings and view slot availability
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={tab === "calendar" ? "default" : "outline"}
            size="sm"
            onClick={() => setTab("calendar")}
          >
            Calendar
          </Button>
          <Button
            variant={tab === "requests" ? "default" : "outline"}
            size="sm"
            onClick={() => setTab("requests")}
          >
            All Requests
          </Button>
        </div>
      </div>

      {tab === "calendar" && (
        <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          {/* Date picker */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Select Date</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 max-h-[500px] overflow-y-auto">
              {calendarLoading ? (
                <div className="flex justify-center py-8">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                </div>
              ) : calendarDates.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4">No upcoming slots</p>
              ) : (
                calendarDates.map((dateKey) => {
                  const daySlots = calendarGrouped[dateKey];
                  const dayBooked = daySlots.filter((s) => s.status === "booked").length;
                  const dayTotal = daySlots.length;
                  return (
                    <button
                      key={dateKey}
                      onClick={() => setSelectedDate(dateKey)}
                      className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-sm transition-colors ${
                        selectedDate === dateKey
                          ? "bg-primary text-primary-foreground"
                          : "hover:bg-accent"
                      }`}
                    >
                      <span className="font-medium">{formatDateLabel(dateKey)}</span>
                      <span className={`text-xs ${selectedDate === dateKey ? "text-primary-foreground/70" : "text-muted-foreground"}`}>
                        {dayBooked}/{dayTotal} booked
                      </span>
                    </button>
                  );
                })
              )}
            </CardContent>
          </Card>

          {/* Slots for selected date */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">
                {selectedDate
                  ? `${formatDateLabel(selectedDate)} — ${availableCount} available, ${bookedCount} booked`
                  : "Select a date to view slots"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!selectedDate ? (
                <p className="py-8 text-center text-muted-foreground">
                  Pick a date from the left panel
                </p>
              ) : (
                <div className="space-y-2 max-h-[450px] overflow-y-auto">
                  {selectedSlots.map((slot) => (
                    <div
                      key={slot.start}
                      className={`flex items-center justify-between rounded-md border p-3 ${
                        slot.status === "booked"
                          ? "border-primary/20 bg-primary/5"
                          : "border-border"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-sm font-medium w-24">
                          {formatTime(slot.start)} – {formatTime(slot.end)}
                        </span>
                        {slot.status === "available" ? (
                          <Badge variant="outline" className="bg-green-50 text-green-700">
                            Available
                          </Badge>
                        ) : slot.booking ? (
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className={STATUS_COLORS[slot.booking.status]}>
                              {slot.booking.status}
                            </Badge>
                            <span className="text-sm font-medium">{slot.booking.name}</span>
                            <span className="text-xs text-muted-foreground">{slot.booking.email}</span>
                            {slot.booking.company && (
                              <span className="text-xs text-muted-foreground">({slot.booking.company})</span>
                            )}
                          </div>
                        ) : null}
                      </div>

                      {slot.booking && (
                        <div className="flex items-center gap-2">
                          {slot.booking.meeting_link && (
                            <a
                              href={slot.booking.meeting_link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-blue-600 underline"
                            >
                              Meeting Link
                            </a>
                          )}
                          {slot.booking.status === "pending" && (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={updateStatus.isPending}
                              onClick={() =>
                                updateStatus.mutate({
                                  id: slot.booking!.id,
                                  status: "confirmed",
                                })
                              }
                            >
                              Confirm
                            </Button>
                          )}
                          {slot.booking.status === "confirmed" && (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={updateStatus.isPending}
                              onClick={() =>
                                updateStatus.mutate({
                                  id: slot.booking!.id,
                                  status: "completed",
                                })
                              }
                            >
                              Complete
                            </Button>
                          )}
                          {(slot.booking.status === "pending" || slot.booking.status === "confirmed") && (
                            <Button
                              size="sm"
                              variant="destructive"
                              disabled={updateStatus.isPending}
                              onClick={() =>
                                updateStatus.mutate({
                                  id: slot.booking!.id,
                                  status: "cancelled",
                                })
                              }
                            >
                              Cancel
                            </Button>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {tab === "requests" && (
        <>
          <div className="flex gap-2">
            {["all", "pending", "confirmed", "completed", "cancelled"].map((s) => (
              <Button
                key={s}
                variant={filter === s ? "default" : "outline"}
                size="sm"
                onClick={() => setFilter(s)}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)}{" "}
                {counts?.[s] ? `(${counts[s]})` : ""}
              </Button>
            ))}
          </div>

          {requestsLoading ? (
            <div className="flex justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : !filtered?.length ? (
            <div className="rounded-md border py-12 text-center text-muted-foreground">
              No demo requests found
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Company</TableHead>
                    <TableHead>Slot</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Meeting</TableHead>
                    <TableHead>Requested</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered?.map((req) => (
                    <TableRow key={req.id}>
                      <TableCell className="font-medium">{req.name}</TableCell>
                      <TableCell>{req.email}</TableCell>
                      <TableCell>{req.company || "—"}</TableCell>
                      <TableCell className="whitespace-nowrap">
                        {new Date(req.slot_start).toLocaleString("en-US", {
                          weekday: "short",
                          month: "short",
                          day: "numeric",
                          hour: "numeric",
                          minute: "2-digit",
                          hour12: true,
                          timeZone: "UTC",
                        })}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className={STATUS_COLORS[req.status] || ""}>
                          {req.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {req.meeting_link ? (
                          <a
                            href={req.meeting_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-blue-600 underline"
                          >
                            Link
                          </a>
                        ) : (
                          "—"
                        )}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        {formatDateFull(req.created_at)}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          {req.status === "pending" && (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={updateStatus.isPending}
                              onClick={() =>
                                updateStatus.mutate({ id: req.id, status: "confirmed" })
                              }
                            >
                              Confirm
                            </Button>
                          )}
                          {req.status === "confirmed" && (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={updateStatus.isPending}
                              onClick={() =>
                                updateStatus.mutate({ id: req.id, status: "completed" })
                              }
                            >
                              Complete
                            </Button>
                          )}
                          {(req.status === "pending" || req.status === "confirmed") && (
                            <Button
                              size="sm"
                              variant="destructive"
                              disabled={updateStatus.isPending}
                              onClick={() =>
                                updateStatus.mutate({ id: req.id, status: "cancelled" })
                              }
                            >
                              Cancel
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
