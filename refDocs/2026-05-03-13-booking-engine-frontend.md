# Booking Engine Frontend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build booking management UI — list, detail, status transitions, and resource booking flow with availability hold system.

**Architecture:** Four tasks building bottom-up: types first, then list view, detail view, and finally the booking creation flow on the resource detail page. The booking creation flow uses a 3-step process (check availability → hold → create booking) with a 10-minute hold countdown timer.

**Tech Stack:** Next.js 15, TypeScript, React Query v5, react-hook-form, Zod, shadcn/ui, Tailwind CSS

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `frontend/src/types/api.ts` | Add booking + availability types |
| Create | `frontend/src/components/bookings/booking-table.tsx` | Table component for booking list |
| Modify | `frontend/src/app/(admin)/bookings/page.tsx` | Booking list page with status filter |
| Create | `frontend/src/app/(admin)/bookings/[id]/page.tsx` | Booking detail page with status transitions |
| Create | `frontend/src/components/bookings/booking-actions.tsx` | Confirm/reject/cancel/no-show action buttons |
| Create | `frontend/src/components/bookings/book-resource-sheet.tsx` | Booking creation sheet (availability → hold → book) |
| Modify | `frontend/src/app/(admin)/resources/[typeSlug]/[resourceId]/page.tsx` | Add "Book" button triggering booking sheet |

---

### Task 1: Add Booking & Availability Types

**Files:**
- Modify: `frontend/src/types/api.ts`

- [ ] **Step 1: Add booking types**

Append to the end of `frontend/src/types/api.ts`:

```typescript
// ─── Bookings ───────────────────────────────────────────

export interface BookingResponse {
  id: string;
  resource_id: string;
  user_id: string;
  status: string;
  start_time: string;
  end_time: string;
  total_price: number;
  currency: string;
  hold_token: string | null;
  cancellation_policy: Record<string, unknown> | null;
  notes: string | null;
  auto_confirm: boolean;
  confirmed_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  refund_percent: number | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface BookingCreate {
  resource_id: string;
  hold_token: string;
  start_time: string;
  end_time: string;
  notes?: string;
  auto_confirm?: boolean;
}

export interface BookingCancel {
  reason?: string;
}

export interface BookingReject {
  reason?: string;
}

// ─── Availability ───────────────────────────────────────

export interface AvailabilityCheckRequest {
  start: string;
  end: string;
}

export interface AvailabilityCheckResponse {
  available: boolean;
  price: number | null;
}

export interface HoldRequest {
  start: string;
  end: string;
  hold_minutes?: number;
}

export interface HoldResponse {
  hold_token: string;
  expires: string;
  price: number;
}

export interface ReleaseRequest {
  hold_token: string;
}

export interface PriceCalculateRequest {
  start: string;
  end: string;
}

export interface PriceCalculateResponse {
  price: number;
  currency: string;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/api.ts
git commit -m "feat(bookings): add booking and availability types"
```

---

### Task 2: Booking List Page + Table Component

**Files:**
- Create: `frontend/src/components/bookings/booking-table.tsx`
- Modify: `frontend/src/app/(admin)/bookings/page.tsx`

- [ ] **Step 1: Create booking-table.tsx**

Create `frontend/src/components/bookings/booking-table.tsx`:

```tsx
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

interface BookingTableProps {
  bookings: BookingResponse[];
  resourceNames: Record<string, string>;
}

function formatDateRange(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  const sameDay = s.toLocaleDateString() === e.toLocaleDateString();
  if (sameDay) {
    return `${s.toLocaleDateString()} ${s.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} – ${e.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  }
  return `${s.toLocaleDateString()} – ${e.toLocaleDateString()}`;
}

export function BookingTable({ bookings, resourceNames }: BookingTableProps) {
  if (bookings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <p className="text-muted-foreground">No bookings found</p>
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
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
            <TableCell className="font-medium">
              <Link href={`/bookings/${b.id}`} className="hover:underline">
                {resourceNames[b.resource_id] ?? b.resource_id.slice(0, 8)}
              </Link>
            </TableCell>
            <TableCell>
              <Badge variant={STATUS_VARIANT[b.status] ?? "muted"}>
                {b.status.replace(/_/g, " ")}
              </Badge>
            </TableCell>
            <TableCell className="text-sm">
              {formatDateRange(b.start_time, b.end_time)}
            </TableCell>
            <TableCell>
              {b.total_price.toFixed(2)} {b.currency}
            </TableCell>
            <TableCell className="text-muted-foreground">
              {new Date(b.created_at).toLocaleDateString()}
            </TableCell>
            <TableCell>
              <DropdownMenu>
                <DropdownMenuTrigger
                  render={<Button variant="ghost" size="icon" className="h-8 w-8" />}
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
```

- [ ] **Step 2: Replace bookings/page.tsx stub**

Replace `frontend/src/app/(admin)/bookings/page.tsx` with:

```tsx
"use client";

import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { BookingResponse, ResourceResponse } from "@/types/api";
import { BookingTable } from "@/components/bookings/booking-table";

export default function BookingsPage() {
  const searchParams = useSearchParams();
  const statusFilter = searchParams.get("status");

  const { data: bookings, isLoading } = useQuery({
    queryKey: ["bookings", statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      const { data } = await api.get<BookingResponse[]>(
        `/bookings?${params.toString()}`
      );
      return data;
    },
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

  const resourceNames: Record<string, string> = {};
  resources?.forEach((r) => {
    resourceNames[r.id] = r.name;
  });

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Bookings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {statusFilter
            ? `Showing ${statusFilter} bookings`
            : "All bookings"}
        </p>
      </div>

      <BookingTable
        bookings={bookings ?? []}
        resourceNames={resourceNames}
      />
    </div>
  );
}
```

- [ ] **Step 3: Verify manually**

Run the dev server. Navigate to `/bookings`. Verify:
- Empty state shows "No bookings found"
- Sub-nav status filter links work (clicking "Pending" adds ?status=pending and re-fetches)
- If bookings exist, table renders with resource names, status badges, dates, price

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/bookings/booking-table.tsx frontend/src/app/\(admin\)/bookings/page.tsx
git commit -m "feat(bookings): add booking list page with status filter and table"
```

---

### Task 3: Booking Detail Page + Action Buttons

**Files:**
- Create: `frontend/src/components/bookings/booking-actions.tsx`
- Create: `frontend/src/app/(admin)/bookings/[id]/page.tsx`

- [ ] **Step 1: Create booking-actions.tsx**

This component renders action buttons based on current booking status and valid transitions.

Create `frontend/src/components/bookings/booking-actions.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, X, Ban, AlertTriangle, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import api from "@/lib/api";
import type { BookingResponse } from "@/types/api";
import { toast } from "sonner";

const VALID_TRANSITIONS: Record<string, string[]> = {
  pending: ["confirmed", "rejected", "cancelled"],
  confirmed: ["active", "cancelled"],
  active: ["completed", "cancelled", "no_show"],
};

interface BookingActionsProps {
  booking: BookingResponse;
}

export function BookingActions({ booking }: BookingActionsProps) {
  const queryClient = useQueryClient();
  const [reasonSheetOpen, setReasonSheetOpen] = useState(false);
  const [reasonAction, setReasonAction] = useState<"reject" | "cancel">("cancel");
  const [reason, setReason] = useState("");

  const transitions = VALID_TRANSITIONS[booking.status] ?? [];

  const actionMutation = useMutation({
    mutationFn: async ({
      action,
      body,
    }: {
      action: string;
      body?: Record<string, unknown>;
    }) => {
      const { data } = await api.post<BookingResponse>(
        `/bookings/${booking.id}/${action}`,
        body ?? {}
      );
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["booking", booking.id] });
      queryClient.invalidateQueries({ queryKey: ["bookings"] });
      toast.success(`Booking ${data.status.replace(/_/g, " ")}`);
      setReasonSheetOpen(false);
      setReason("");
    },
    onError: () => {
      toast.error("Action failed");
    },
  });

  function openReasonSheet(action: "reject" | "cancel") {
    setReasonAction(action);
    setReason("");
    setReasonSheetOpen(true);
  }

  function submitWithReason() {
    actionMutation.mutate({
      action: reasonAction,
      body: reason ? { reason } : {},
    });
  }

  if (transitions.length === 0) return null;

  return (
    <>
      <div className="flex flex-wrap gap-2">
        {transitions.includes("confirmed") && (
          <Button
            size="sm"
            onClick={() => actionMutation.mutate({ action: "confirm" })}
            disabled={actionMutation.isPending}
          >
            <Check className="mr-2 h-4 w-4" />
            Confirm
          </Button>
        )}
        {transitions.includes("active") && (
          <Button
            size="sm"
            onClick={() => actionMutation.mutate({ action: "activate" })}
            disabled={actionMutation.isPending}
          >
            <CheckCircle className="mr-2 h-4 w-4" />
            Activate
          </Button>
        )}
        {transitions.includes("completed") && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => actionMutation.mutate({ action: "complete" })}
            disabled={actionMutation.isPending}
          >
            <CheckCircle className="mr-2 h-4 w-4" />
            Complete
          </Button>
        )}
        {transitions.includes("rejected") && (
          <Button
            size="sm"
            variant="destructive"
            onClick={() => openReasonSheet("reject")}
            disabled={actionMutation.isPending}
          >
            <X className="mr-2 h-4 w-4" />
            Reject
          </Button>
        )}
        {transitions.includes("cancelled") && (
          <Button
            size="sm"
            variant="destructive"
            onClick={() => openReasonSheet("cancel")}
            disabled={actionMutation.isPending}
          >
            <Ban className="mr-2 h-4 w-4" />
            Cancel
          </Button>
        )}
        {transitions.includes("no_show") && (
          <Button
            size="sm"
            variant="destructive"
            onClick={() => actionMutation.mutate({ action: "no-show" })}
            disabled={actionMutation.isPending}
          >
            <AlertTriangle className="mr-2 h-4 w-4" />
            No-Show
          </Button>
        )}
      </div>

      <Sheet open={reasonSheetOpen} onOpenChange={(o) => !o && setReasonSheetOpen(false)}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>
              {reasonAction === "reject" ? "Reject Booking" : "Cancel Booking"}
            </SheetTitle>
            <SheetDescription>
              Provide an optional reason for this action.
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="reason">Reason</Label>
              <Input
                id="reason"
                placeholder="Optional reason..."
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </div>
            <div className="flex gap-3">
              <Button
                variant="destructive"
                onClick={submitWithReason}
                disabled={actionMutation.isPending}
                className="flex-1"
              >
                {actionMutation.isPending
                  ? "Processing..."
                  : reasonAction === "reject"
                    ? "Reject"
                    : "Cancel Booking"}
              </Button>
              <Button
                variant="outline"
                onClick={() => setReasonSheetOpen(false)}
              >
                Back
              </Button>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
```

**Important note about endpoints:** The backend has these action endpoints:
- `POST /bookings/{id}/confirm` — no body
- `POST /bookings/{id}/reject` — body `{reason?}`
- `POST /bookings/{id}/cancel` — body `{reason?}`
- `POST /bookings/{id}/no-show` — no body

There is **no** `/activate` or `/complete` endpoint in the backend router. The `active` and `completed` transitions are system-managed (e.g., auto-activated when start_time arrives, auto-completed when end_time passes). The implementer **must check the backend router** and only include buttons for endpoints that actually exist. If `activate` and `complete` don't exist, remove those buttons and their entries from `VALID_TRANSITIONS`. Adjust to:

```typescript
const VALID_TRANSITIONS: Record<string, string[]> = {
  pending: ["confirmed", "rejected", "cancelled"],
  confirmed: ["cancelled"],
  active: ["cancelled", "no_show"],
};
```

- [ ] **Step 2: Create booking detail page**

Create `frontend/src/app/(admin)/bookings/[id]/page.tsx`:

```tsx
"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Calendar, Clock } from "lucide-react";
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

export default function BookingDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: booking, isLoading } = useQuery({
    queryKey: ["booking", id],
    queryFn: async () => {
      const { data } = await api.get<BookingResponse>(`/bookings/${id}`);
      return data;
    },
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

  const start = new Date(booking.start_time);
  const end = new Date(booking.end_time);

  return (
    <div className="flex-1 space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Link href="/bookings" className="rounded-md p-1 hover:bg-accent">
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
            Booking #{booking.id.slice(0, 8)}
          </p>
        </div>
      </div>

      <BookingActions booking={booking} />

      <div className="grid gap-6 md:grid-cols-2">
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
              {start.toLocaleDateString()} {start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              End
            </span>
            <span className="text-sm font-medium">
              {end.toLocaleDateString()} {end.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>
        </div>

        <div className="space-y-4 rounded-lg border p-6">
          <h2 className="text-sm font-semibold text-muted-foreground">
            Payment
          </h2>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Total</span>
            <span className="text-lg font-semibold">
              {booking.total_price.toFixed(2)} {booking.currency}
            </span>
          </div>
          {booking.refund_percent !== null && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Refund</span>
              <span className="text-sm font-medium">{booking.refund_percent}%</span>
            </div>
          )}
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Auto-confirm</span>
            <span className="text-sm">{booking.auto_confirm ? "Yes" : "No"}</span>
          </div>
        </div>
      </div>

      {(booking.notes || booking.cancellation_reason || booking.confirmed_at || booking.cancelled_at) && (
        <div className="space-y-4 rounded-lg border p-6">
          <h2 className="text-sm font-semibold text-muted-foreground">
            Details
          </h2>
          {booking.notes && (
            <div className="flex items-start justify-between">
              <span className="text-sm text-muted-foreground">Notes</span>
              <span className="text-sm max-w-xs text-right">{booking.notes}</span>
            </div>
          )}
          {booking.confirmed_at && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Confirmed</span>
              <span className="text-sm">
                {new Date(booking.confirmed_at).toLocaleString()}
              </span>
            </div>
          )}
          {booking.cancelled_at && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Cancelled</span>
              <span className="text-sm">
                {new Date(booking.cancelled_at).toLocaleString()}
              </span>
            </div>
          )}
          {booking.cancellation_reason && (
            <div className="flex items-start justify-between">
              <span className="text-sm text-muted-foreground">Reason</span>
              <span className="text-sm max-w-xs text-right">
                {booking.cancellation_reason}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify manually**

Test: Navigate to `/bookings/{id}` for an existing booking. Verify:
- Booking details display (schedule, price, status badge)
- Action buttons match current status
- Confirm button works (pending → confirmed)
- Reject opens reason sheet, submitting changes status
- Cancel opens reason sheet

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/bookings/booking-actions.tsx frontend/src/app/\(admin\)/bookings/\[id\]/page.tsx
git commit -m "feat(bookings): add booking detail page with status transition actions"
```

---

### Task 4: Book Resource Flow (Availability → Hold → Create)

**Files:**
- Create: `frontend/src/components/bookings/book-resource-sheet.tsx`
- Modify: `frontend/src/app/(admin)/resources/[typeSlug]/[resourceId]/page.tsx`

This is the most complex task. The sheet has 3 steps:
1. **Pick dates** → check availability → show price
2. **Hold** → 10-min countdown timer → show "Book Now" button
3. **Confirm** → create booking → redirect to booking detail

- [ ] **Step 1: Create book-resource-sheet.tsx**

Create `frontend/src/components/bookings/book-resource-sheet.tsx`:

```tsx
"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { CalendarDays, Clock, Loader2 } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import api from "@/lib/api";
import type {
  AvailabilityCheckResponse,
  BookingResponse,
  HoldResponse,
} from "@/types/api";
import { toast } from "sonner";

type Step = "dates" | "held" | "booked";

interface BookResourceSheetProps {
  open: boolean;
  onClose: () => void;
  resourceId: string;
  resourceName: string;
  availabilityModel: string;
}

function formatCountdown(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function BookResourceSheet({
  open,
  onClose,
  resourceId,
  resourceName,
  availabilityModel,
}: BookResourceSheetProps) {
  const router = useRouter();
  const [step, setStep] = useState<Step>("dates");
  const [startDate, setStartDate] = useState("");
  const [startTime, setStartTime] = useState("09:00");
  const [endDate, setEndDate] = useState("");
  const [endTime, setEndTime] = useState("17:00");
  const [notes, setNotes] = useState("");
  const [holdData, setHoldData] = useState<HoldResponse | null>(null);
  const [countdown, setCountdown] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function buildDatetime(date: string, time: string): string {
    return new Date(`${date}T${time}`).toISOString();
  }

  const isHourly = availabilityModel === "hourly";
  const isTimeSlot = availabilityModel === "time_slot";
  const showTime = isHourly || isTimeSlot;

  // Countdown timer
  useEffect(() => {
    if (step !== "held" || !holdData) return;
    const expiresAt = new Date(holdData.expires).getTime();
    function tick() {
      const remaining = Math.max(0, Math.floor((expiresAt - Date.now()) / 1000));
      setCountdown(remaining);
      if (remaining <= 0) {
        if (timerRef.current) clearInterval(timerRef.current);
        toast.error("Hold expired — please try again");
        resetToStart();
      }
    }
    tick();
    timerRef.current = setInterval(tick, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [step, holdData]);

  function resetToStart() {
    setStep("dates");
    setHoldData(null);
    setCountdown(0);
  }

  function handleClose() {
    if (holdData && step === "held") {
      api.post(`/resources/${resourceId}/availability/release`, {
        hold_token: holdData.hold_token,
      }).catch(() => {});
    }
    resetToStart();
    onClose();
  }

  const checkMutation = useMutation({
    mutationFn: async () => {
      const start = buildDatetime(startDate, showTime ? startTime : "00:00");
      const end = buildDatetime(endDate || startDate, showTime ? endTime : "23:59");
      const { data } = await api.post<AvailabilityCheckResponse>(
        `/resources/${resourceId}/availability/check`,
        { start, end }
      );
      return data;
    },
  });

  const holdMutation = useMutation({
    mutationFn: async () => {
      const start = buildDatetime(startDate, showTime ? startTime : "00:00");
      const end = buildDatetime(endDate || startDate, showTime ? endTime : "23:59");
      const { data } = await api.post<HoldResponse>(
        `/resources/${resourceId}/availability/hold`,
        { start, end, hold_minutes: 10 }
      );
      return data;
    },
    onSuccess: (data) => {
      setHoldData(data);
      setStep("held");
      toast.success("Hold placed — 10 minutes to complete booking");
    },
    onError: () => {
      toast.error("Could not hold — resource may be unavailable");
    },
  });

  const bookMutation = useMutation({
    mutationFn: async () => {
      const start = buildDatetime(startDate, showTime ? startTime : "00:00");
      const end = buildDatetime(endDate || startDate, showTime ? endTime : "23:59");
      const { data } = await api.post<BookingResponse>("/bookings", {
        resource_id: resourceId,
        hold_token: holdData!.hold_token,
        start_time: start,
        end_time: end,
        notes: notes || undefined,
        auto_confirm: true,
      });
      return data;
    },
    onSuccess: (data) => {
      setStep("booked");
      toast.success("Booking created!");
      onClose();
      router.push(`/bookings/${data.id}`);
    },
    onError: () => {
      toast.error("Booking failed — hold may have expired");
      resetToStart();
    },
  });

  async function handleCheckAndHold() {
    const result = await checkMutation.mutateAsync();
    if (!result.available) {
      toast.error("Resource not available for selected dates");
      return;
    }
    holdMutation.mutate();
  }

  const isPending = checkMutation.isPending || holdMutation.isPending;

  return (
    <Sheet open={open} onOpenChange={(o) => !o && handleClose()}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Book {resourceName}</SheetTitle>
          <SheetDescription>
            {step === "dates" && "Select dates and check availability"}
            {step === "held" && `Hold active — ${formatCountdown(countdown)} remaining`}
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-4">
          {step === "dates" && (
            <>
              <div className="space-y-2">
                <Label>Start Date</Label>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
              {showTime && (
                <div className="space-y-2">
                  <Label>Start Time</Label>
                  <Input
                    type="time"
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                  />
                </div>
              )}
              {!isTimeSlot && (
                <div className="space-y-2">
                  <Label>End Date</Label>
                  <Input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
              )}
              {showTime && (
                <div className="space-y-2">
                  <Label>End Time</Label>
                  <Input
                    type="time"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                  />
                </div>
              )}
              <div className="space-y-2">
                <Label>Notes (optional)</Label>
                <Input
                  placeholder="Any special requests..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </div>

              {checkMutation.data && checkMutation.data.available && (
                <div className="rounded-lg bg-muted p-3 text-sm">
                  Estimated price: <span className="font-semibold">${checkMutation.data.price?.toFixed(2)}</span>
                </div>
              )}

              <Button
                onClick={handleCheckAndHold}
                disabled={!startDate || isPending}
                className="w-full"
              >
                {isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Checking...
                  </>
                ) : (
                  <>
                    <CalendarDays className="mr-2 h-4 w-4" />
                    Check & Hold
                  </>
                )}
              </Button>
            </>
          )}

          {step === "held" && holdData && (
            <>
              <div className="rounded-lg border-2 border-primary/50 bg-primary/5 p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Price</span>
                  <span className="text-lg font-semibold">
                    ${holdData.price.toFixed(2)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Hold expires</span>
                  <span className="flex items-center gap-1 text-sm font-mono font-semibold">
                    <Clock className="h-4 w-4" />
                    {formatCountdown(countdown)}
                  </span>
                </div>
              </div>

              <Button
                onClick={() => bookMutation.mutate()}
                disabled={bookMutation.isPending}
                className="w-full"
                size="lg"
              >
                {bookMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating booking...
                  </>
                ) : (
                  "Confirm Booking"
                )}
              </Button>
              <Button
                variant="outline"
                onClick={handleClose}
                className="w-full"
              >
                Cancel
              </Button>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

- [ ] **Step 2: Add Book button to resource detail page**

Modify `frontend/src/app/(admin)/resources/[typeSlug]/[resourceId]/page.tsx`:

Add import at top:

```tsx
import { CalendarDays } from "lucide-react";
import { BookResourceSheet } from "@/components/bookings/book-resource-sheet";
```

Add state inside the component (after `const [editOpen, setEditOpen] = useState(false)`):

```tsx
const [bookOpen, setBookOpen] = useState(false);
```

Add a "Book" button in the header, before the Edit button:

```tsx
<Button onClick={() => setBookOpen(true)} disabled={resource.status !== "active"}>
  <CalendarDays className="mr-2 h-4 w-4" />
  Book
</Button>
```

Add the `BookResourceSheet` at the bottom of the return JSX (after `CreateResourceSheet`):

```tsx
<BookResourceSheet
  open={bookOpen}
  onClose={() => setBookOpen(false)}
  resourceId={resource.id}
  resourceName={resource.name}
  availabilityModel={currentType.availability_model}
/>
```

- [ ] **Step 3: Verify manually**

Test the full booking flow:
1. Navigate to a resource detail page (resource must be status="active")
2. Click "Book" → sheet opens with date inputs
3. Select dates → "Check & Hold" → should show price and start countdown
4. Click "Confirm Booking" → booking created, redirect to booking detail
5. Verify countdown timer ticks down
6. Test hold expiry: open hold, wait 10 minutes (or set `hold_minutes: 1` temporarily), verify "Hold expired" toast

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/bookings/book-resource-sheet.tsx frontend/src/app/\(admin\)/resources/\[typeSlug\]/\[resourceId\]/page.tsx
git commit -m "feat(bookings): add resource booking flow with availability hold and countdown"
```

---

## Verification Checklist

After all tasks, verify end-to-end:

- [ ] Booking list page shows bookings with resource names, status badges, dates, prices
- [ ] Sub-nav status filters work (All, Pending, Confirmed, Active, Completed, Cancelled)
- [ ] Booking detail page shows all fields
- [ ] Confirm button works on pending bookings
- [ ] Reject with reason works on pending bookings
- [ ] Cancel with reason works on pending/confirmed bookings
- [ ] No-show works on active bookings
- [ ] Resource detail "Book" button disabled when resource not active
- [ ] Booking flow: dates → check availability → hold (countdown visible) → confirm booking
- [ ] Hold release on sheet close/cancel
- [ ] Hold expiry shows error toast and resets to date picker
- [ ] New booking appears in bookings list after creation
