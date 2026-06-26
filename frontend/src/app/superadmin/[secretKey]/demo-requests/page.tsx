"use client";

import { useState, useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
  useSlotBlocks,
  useCreateSlotBlock,
  useDeleteSlotBlock,
  type CalendarSlot,
  type SlotBlock,
} from "@/hooks/use-demo-requests";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  confirmed: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
};

const ALL_SLOT_TIMES = Array.from({ length: 16 }, (_, i) => {
  const hour = 9 + Math.floor(i / 2);
  const min = i % 2 === 0 ? "00" : "30";
  return `${hour.toString().padStart(2, "0")}:${min}`;
});

function formatSlotTime(t: string) {
  const [h, m] = t.split(":");
  const hour = parseInt(h);
  const ampm = hour >= 12 ? "PM" : "AM";
  const h12 = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
  return `${h12}:${m} ${ampm}`;
}

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
  const [tab, setTab] = useState<"calendar" | "requests" | "settings">("calendar");
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
  const blockedCount = selectedSlots.filter((s) => s.status === "blocked").length;

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
            Manage demo bookings and slot availability
          </p>
        </div>
        <div className="flex gap-2">
          {(["calendar", "requests", "settings"] as const).map((t) => (
            <Button
              key={t}
              variant={tab === t ? "default" : "outline"}
              size="sm"
              onClick={() => setTab(t)}
            >
              {t === "calendar" ? "Calendar" : t === "requests" ? "All Requests" : "Slot Settings"}
            </Button>
          ))}
        </div>
      </div>

      {tab === "calendar" && (
        <CalendarTab
          calendarLoading={calendarLoading}
          calendarDates={calendarDates}
          calendarGrouped={calendarGrouped}
          selectedDate={selectedDate}
          setSelectedDate={setSelectedDate}
          selectedSlots={selectedSlots}
          availableCount={availableCount}
          bookedCount={bookedCount}
          blockedCount={blockedCount}
          updateStatus={updateStatus}
        />
      )}

      {tab === "requests" && (
        <RequestsTab
          requestsLoading={requestsLoading}
          filtered={filtered}
          filter={filter}
          setFilter={setFilter}
          counts={counts}
          updateStatus={updateStatus}
        />
      )}

      {tab === "settings" && <SlotSettingsTab />}
    </div>
  );
}

function CalendarTab({
  calendarLoading,
  calendarDates,
  calendarGrouped,
  selectedDate,
  setSelectedDate,
  selectedSlots,
  availableCount,
  bookedCount,
  blockedCount,
  updateStatus,
}: {
  calendarLoading: boolean;
  calendarDates: string[];
  calendarGrouped: Record<string, CalendarSlot[]>;
  selectedDate: string | null;
  setSelectedDate: (d: string | null) => void;
  selectedSlots: CalendarSlot[];
  availableCount: number;
  bookedCount: number;
  blockedCount: number;
  updateStatus: ReturnType<typeof useUpdateDemoStatus>;
}) {
  return (
    <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
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
              const dayBlocked = daySlots.filter((s) => s.status === "blocked").length;
              const dayAvail = daySlots.filter((s) => s.status === "available").length;
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
                    {dayAvail}A {dayBooked}B {dayBlocked > 0 ? `${dayBlocked}X` : ""}
                  </span>
                </button>
              );
            })
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">
            {selectedDate
              ? `${formatDateLabel(selectedDate)} — ${availableCount} available, ${bookedCount} booked${blockedCount > 0 ? `, ${blockedCount} blocked` : ""}`
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
                      : slot.status === "blocked"
                      ? "border-red-200 bg-red-50"
                      : "border-border"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-sm font-medium w-24">
                      {formatTime(slot.start)} – {formatTime(slot.end)}
                    </span>
                    {slot.status === "available" && (
                      <Badge variant="outline" className="bg-green-50 text-green-700">
                        Available
                      </Badge>
                    )}
                    {slot.status === "blocked" && (
                      <Badge variant="outline" className="bg-red-50 text-red-700">
                        Blocked
                      </Badge>
                    )}
                    {slot.status === "booked" && slot.booking && (
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
                    )}
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
  );
}

function RequestsTab({
  requestsLoading,
  filtered,
  filter,
  setFilter,
  counts,
  updateStatus,
}: {
  requestsLoading: boolean;
  filtered: ReturnType<typeof useDemoRequests>["data"];
  filter: string;
  setFilter: (f: string) => void;
  counts: Record<string, number> | undefined;
  updateStatus: ReturnType<typeof useUpdateDemoStatus>;
}) {
  return (
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
  );
}

function SlotSettingsTab() {
  const { data: blocks, isLoading } = useSlotBlocks();
  const createBlock = useCreateSlotBlock();
  const deleteBlock = useDeleteSlotBlock();
  const [overrideDate, setOverrideDate] = useState("");
  const [overrideTime, setOverrideTime] = useState(ALL_SLOT_TIMES[0]);
  const [overrideAction, setOverrideAction] = useState<"block" | "unblock">("unblock");

  const globalBlocks = useMemo(
    () => blocks?.filter((b) => !b.specific_date) ?? [],
    [blocks]
  );
  const dateOverrides = useMemo(
    () => blocks?.filter((b) => b.specific_date) ?? [],
    [blocks]
  );

  const globalBlockedTimes = new Set(globalBlocks.map((b) => b.slot_time.slice(0, 5)));

  function handleGlobalToggle(time: string) {
    const existing = globalBlocks.find((b) => b.slot_time.slice(0, 5) === time);
    if (existing) {
      deleteBlock.mutate(existing.id);
    } else {
      createBlock.mutate({ slot_time: time, action: "block" });
    }
  }

  function handleAddOverride() {
    if (!overrideDate) return;
    createBlock.mutate({
      slot_time: overrideTime,
      specific_date: overrideDate,
      action: overrideAction,
    });
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Global Blocks */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Global Time Blocks</CardTitle>
          <p className="text-sm text-muted-foreground">
            Block time slots across all dates. Red = blocked.
          </p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-2">
            {ALL_SLOT_TIMES.map((time) => {
              const isBlocked = globalBlockedTimes.has(time);
              return (
                <button
                  key={time}
                  onClick={() => handleGlobalToggle(time)}
                  disabled={createBlock.isPending || deleteBlock.isPending}
                  className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors ${
                    isBlocked
                      ? "border-red-300 bg-red-100 text-red-800 hover:bg-red-200"
                      : "border-green-300 bg-green-50 text-green-800 hover:bg-green-100"
                  }`}
                >
                  {formatSlotTime(time)}
                </button>
              );
            })}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Click to toggle. Green = available, Red = blocked globally.
          </p>
        </CardContent>
      </Card>

      {/* Date Overrides */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Date Overrides</CardTitle>
          <p className="text-sm text-muted-foreground">
            Override global rules for specific dates.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2 items-end">
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Date</label>
              <Input
                type="date"
                value={overrideDate}
                onChange={(e) => setOverrideDate(e.target.value)}
                className="w-40"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Time</label>
              <select
                value={overrideTime}
                onChange={(e) => setOverrideTime(e.target.value)}
                className="h-9 rounded-md border border-input bg-background px-3 text-sm"
              >
                {ALL_SLOT_TIMES.map((t) => (
                  <option key={t} value={t}>{formatSlotTime(t)}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Action</label>
              <select
                value={overrideAction}
                onChange={(e) => setOverrideAction(e.target.value as "block" | "unblock")}
                className="h-9 rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="block">Block</option>
                <option value="unblock">Unblock</option>
              </select>
            </div>
            <Button
              size="sm"
              onClick={handleAddOverride}
              disabled={!overrideDate || createBlock.isPending}
            >
              Add
            </Button>
          </div>

          {dateOverrides.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground text-center">
              No date overrides yet
            </p>
          ) : (
            <div className="space-y-2 max-h-[350px] overflow-y-auto">
              {dateOverrides.map((ov) => (
                <div
                  key={ov.id}
                  className={`flex items-center justify-between rounded-md border p-2 ${
                    ov.action === "block"
                      ? "border-red-200 bg-red-50"
                      : "border-green-200 bg-green-50"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Badge
                      variant="outline"
                      className={ov.action === "block" ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"}
                    >
                      {ov.action}
                    </Badge>
                    <span className="text-sm font-medium">
                      {formatSlotTime(ov.slot_time.slice(0, 5))}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      on {ov.specific_date}
                    </span>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 text-red-600 hover:text-red-800"
                    disabled={deleteBlock.isPending}
                    onClick={() => deleteBlock.mutate(ov.id)}
                  >
                    Remove
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
