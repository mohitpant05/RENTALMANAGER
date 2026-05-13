# Public Resource Detail & Booking — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the public resource detail page with image carousel, booking card (availability check → hold → confirm), and reviews section.

**Architecture:** Extract booking logic from admin `BookResourceSheet` into a shared `useBookingFlow` hook, then build the public resource detail page with two-column layout (content left, sticky booking card right). Reviews section lives below content with rating summary, review list, and review form. All components are public-facing and use the `(public)/` route group.

**Tech Stack:** Next.js 15, TypeScript, React Query v5, shadcn/ui, Zustand, Tailwind CSS

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `hooks/use-booking-flow.ts` | Shared booking logic: check → hold → countdown → confirm |
| Modify | `components/bookings/book-resource-sheet.tsx` | Refactor to use `useBookingFlow` hook |
| Create | `components/public/image-carousel.tsx` | Full-width image gallery with arrows + dots |
| Create | `components/public/booking-card.tsx` | Sticky sidebar booking widget |
| Create | `components/reviews/star-rating.tsx` | Read-only star display |
| Create | `components/reviews/rating-summary.tsx` | Aggregate rating + bar chart breakdown |
| Create | `components/public/star-selector.tsx` | Interactive clickable star input |
| Create | `components/public/review-list.tsx` | Paginated review list |
| Create | `components/public/review-form.tsx` | Review submission in a Sheet |
| Create | `app/(public)/resources/[id]/page.tsx` | Resource detail page |

**Prerequisites:** Plan 14 (types, hooks for reviews/storage/notifications, admin route migration) must be completed first.

---

### Task 1: useBookingFlow Hook

**Files:**
- Create: `frontend/src/hooks/use-booking-flow.ts`

- [ ] **Step 1: Create the hook**

Create `frontend/src/hooks/use-booking-flow.ts`:

```typescript
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import type {
  AvailabilityCheckResponse,
  BookingCreate,
  BookingResponse,
  HoldResponse,
  ReleaseRequest,
} from "@/types/api";
import { toast } from "sonner";

type Step = "dates" | "held" | "booked";

function buildDatetime(date: string, time: string): string {
  return new Date(`${date}T${time}`).toISOString();
}

function formatCountdown(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface UseBookingFlowOptions {
  resourceId: string;
  availabilityModel: string;
}

export function useBookingFlow({ resourceId, availabilityModel }: UseBookingFlowOptions) {
  const [step, setStep] = useState<Step>("dates");
  const [startDate, setStartDate] = useState("");
  const [startTime, setStartTime] = useState("09:00");
  const [endDate, setEndDate] = useState("");
  const [endTime, setEndTime] = useState("17:00");
  const [notes, setNotes] = useState("");
  const [isPending, setIsPending] = useState(false);

  const [holdToken, setHoldToken] = useState("");
  const [holdPrice, setHoldPrice] = useState(0);
  const [countdown, setCountdown] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const showTime = availabilityModel === "hourly" || availabilityModel === "time_slot";
  const hideEndDate = availabilityModel === "time_slot";

  const clearTimer = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    setStep("dates");
    setStartDate("");
    setStartTime("09:00");
    setEndDate("");
    setEndTime("17:00");
    setNotes("");
    setIsPending(false);
    setHoldToken("");
    setHoldPrice(0);
    setCountdown(0);
    clearTimer();
  }, [clearTimer]);

  const releaseHold = useCallback(
    (token: string) => {
      api
        .post<void>(`/resources/${resourceId}/availability/release`, {
          hold_token: token,
        } satisfies ReleaseRequest)
        .catch(() => {});
    },
    [resourceId]
  );

  useEffect(() => {
    if (step !== "held" || countdown <= 0) return;

    intervalRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearTimer();
          toast.error("Hold expired");
          setStep("dates");
          setHoldToken("");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return clearTimer;
  }, [step, countdown <= 0, clearTimer]); // eslint-disable-line react-hooks/exhaustive-deps

  function getStartDatetime(): string {
    if (availabilityModel === "date_range") {
      return buildDatetime(startDate, "00:00");
    }
    return buildDatetime(startDate, startTime);
  }

  function getEndDatetime(): string {
    if (availabilityModel === "date_range") {
      return buildDatetime(endDate, "23:59");
    }
    const ed = hideEndDate ? startDate : endDate;
    return buildDatetime(ed, endTime);
  }

  async function checkAndHold(): Promise<boolean> {
    if (!startDate) {
      toast.error("Please select a start date");
      return false;
    }
    if (!hideEndDate && !endDate) {
      toast.error("Please select an end date");
      return false;
    }

    setIsPending(true);
    try {
      const start = getStartDatetime();
      const end = getEndDatetime();

      const { data: check } = await api.post<AvailabilityCheckResponse>(
        `/resources/${resourceId}/availability/check`,
        { start, end }
      );

      if (!check.available) {
        toast.error("Resource is not available for the selected dates");
        return false;
      }

      const { data: hold } = await api.post<HoldResponse>(
        `/resources/${resourceId}/availability/hold`,
        { start, end }
      );

      setHoldToken(hold.hold_token);
      setHoldPrice(hold.price);

      const expiresAt = new Date(hold.expires).getTime();
      const secondsLeft = Math.max(0, Math.floor((expiresAt - Date.now()) / 1000));
      setCountdown(secondsLeft);
      setStep("held");
      return true;
    } catch {
      toast.error("Failed to check availability");
      return false;
    } finally {
      setIsPending(false);
    }
  }

  async function confirmBooking(): Promise<BookingResponse | null> {
    setIsPending(true);
    try {
      const payload: BookingCreate = {
        resource_id: resourceId,
        hold_token: holdToken,
        start_time: getStartDatetime(),
        end_time: getEndDatetime(),
        notes: notes || undefined,
      };

      const { data: booking } = await api.post<BookingResponse>("/bookings", payload);
      toast.success("Booking confirmed!");
      clearTimer();
      setStep("booked");
      return booking;
    } catch {
      toast.error("Failed to confirm booking");
      return null;
    } finally {
      setIsPending(false);
    }
  }

  function cancel() {
    if (holdToken) {
      releaseHold(holdToken);
    }
    reset();
  }

  return {
    step,
    startDate,
    setStartDate,
    startTime,
    setStartTime,
    endDate,
    setEndDate,
    endTime,
    setEndTime,
    notes,
    setNotes,
    showTime,
    hideEndDate,
    holdPrice,
    countdown,
    countdownFormatted: formatCountdown(countdown),
    isPending,
    checkAndHold,
    confirmBooking,
    cancel,
    reset,
  };
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit --pretty 2>&1 | head -20
```

Expected: No errors related to `use-booking-flow.ts`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/use-booking-flow.ts
git commit -m "feat(bookings): extract useBookingFlow hook from BookResourceSheet"
```

---

### Task 2: Refactor BookResourceSheet to Use Hook

**Files:**
- Modify: `frontend/src/components/bookings/book-resource-sheet.tsx`

- [ ] **Step 1: Rewrite BookResourceSheet using the hook**

Replace the entire contents of `frontend/src/components/bookings/book-resource-sheet.tsx`:

```tsx
"use client";

import { useRouter } from "next/navigation";
import { CalendarDays, Clock, Loader2 } from "lucide-react";
import { useBookingFlow } from "@/hooks/use-booking-flow";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface BookResourceSheetProps {
  open: boolean;
  onClose: () => void;
  resourceId: string;
  resourceName: string;
  availabilityModel: string;
}

export function BookResourceSheet({
  open,
  onClose,
  resourceId,
  resourceName,
  availabilityModel,
}: BookResourceSheetProps) {
  const router = useRouter();
  const flow = useBookingFlow({ resourceId, availabilityModel });

  function handleOpenChange(isOpen: boolean) {
    if (!isOpen) {
      flow.cancel();
      onClose();
    }
  }

  async function handleCheckAndHold() {
    await flow.checkAndHold();
  }

  async function handleConfirm() {
    const booking = await flow.confirmBooking();
    if (booking) {
      flow.reset();
      onClose();
      router.push(`/admin/bookings/${booking.id}`);
    }
  }

  function handleCancel() {
    flow.cancel();
    onClose();
  }

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>
            <CalendarDays className="mr-2 inline h-5 w-5" />
            Book {resourceName}
          </SheetTitle>
          <SheetDescription>
            {flow.step === "dates" && "Select dates to check availability"}
            {flow.step === "held" && "Review and confirm your booking"}
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 space-y-4 px-4">
          {flow.step === "dates" && (
            <>
              <div className="space-y-2">
                <Label htmlFor="start-date">Start Date</Label>
                <Input
                  id="start-date"
                  type="date"
                  value={flow.startDate}
                  onChange={(e) => flow.setStartDate(e.target.value)}
                />
              </div>

              {flow.showTime && (
                <div className="space-y-2">
                  <Label htmlFor="start-time">Start Time</Label>
                  <Input
                    id="start-time"
                    type="time"
                    value={flow.startTime}
                    onChange={(e) => flow.setStartTime(e.target.value)}
                  />
                </div>
              )}

              {!flow.hideEndDate && (
                <div className="space-y-2">
                  <Label htmlFor="end-date">End Date</Label>
                  <Input
                    id="end-date"
                    type="date"
                    value={flow.endDate}
                    onChange={(e) => flow.setEndDate(e.target.value)}
                  />
                </div>
              )}

              {flow.showTime && (
                <div className="space-y-2">
                  <Label htmlFor="end-time">End Time</Label>
                  <Input
                    id="end-time"
                    type="time"
                    value={flow.endTime}
                    onChange={(e) => flow.setEndTime(e.target.value)}
                  />
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="notes">Notes (optional)</Label>
                <Input
                  id="notes"
                  placeholder="Any special requests..."
                  value={flow.notes}
                  onChange={(e) => flow.setNotes(e.target.value)}
                />
              </div>
            </>
          )}

          {flow.step === "held" && (
            <>
              <div className="rounded-lg border p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Price</span>
                  <span className="text-lg font-semibold">
                    ${flow.holdPrice.toFixed(2)}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">
                    <Clock className="mr-1 inline h-4 w-4" />
                    Hold expires in
                  </span>
                  <span
                    className={`font-mono text-sm font-semibold ${
                      flow.countdown < 60 ? "text-destructive" : "text-foreground"
                    }`}
                  >
                    {flow.countdownFormatted}
                  </span>
                </div>
              </div>

              <div className="rounded-lg border p-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Start</span>
                  <span>
                    {flow.startDate}
                    {flow.showTime ? ` ${flow.startTime}` : ""}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">End</span>
                  <span>
                    {flow.hideEndDate ? flow.startDate : flow.endDate}
                    {flow.showTime ? ` ${flow.endTime}` : ""}
                  </span>
                </div>
                {flow.notes && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Notes</span>
                    <span className="text-right max-w-[200px]">{flow.notes}</span>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        <SheetFooter>
          {flow.step === "dates" && (
            <Button onClick={handleCheckAndHold} disabled={flow.isPending}>
              {flow.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Check & Hold
            </Button>
          )}

          {flow.step === "held" && (
            <div className="flex w-full gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={handleCancel}
                disabled={flow.isPending}
              >
                Cancel
              </Button>
              <Button
                className="flex-1"
                onClick={handleConfirm}
                disabled={flow.isPending}
              >
                {flow.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Confirm Booking
              </Button>
            </div>
          )}
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit --pretty 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/bookings/book-resource-sheet.tsx
git commit -m "refactor(bookings): use useBookingFlow hook in BookResourceSheet"
```

---

### Task 3: StarRating + RatingSummary Components

**Files:**
- Create: `frontend/src/components/reviews/star-rating.tsx`
- Create: `frontend/src/components/reviews/rating-summary.tsx`

- [ ] **Step 1: Create star-rating.tsx**

Create `frontend/src/components/reviews/star-rating.tsx`:

```tsx
import { Star } from "lucide-react";
import { cn } from "@/lib/utils";

interface StarRatingProps {
  rating: number;
  max?: number;
  size?: "sm" | "md";
}

export function StarRating({ rating, max = 5, size = "sm" }: StarRatingProps) {
  const sizeClass = size === "sm" ? "h-3.5 w-3.5" : "h-5 w-5";

  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: max }, (_, i) => {
        const filled = i < Math.floor(rating);
        const half = !filled && i < rating;

        return (
          <Star
            key={i}
            className={cn(
              sizeClass,
              filled
                ? "fill-yellow-400 text-yellow-400"
                : half
                  ? "fill-yellow-400/50 text-yellow-400"
                  : "fill-muted text-muted-foreground/30"
            )}
          />
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Create rating-summary.tsx**

Create `frontend/src/components/reviews/rating-summary.tsx`:

```tsx
"use client";

import { useRatingSummary } from "@/hooks/use-reviews";
import { StarRating } from "./star-rating";

interface RatingSummaryProps {
  resourceId: string;
}

export function RatingSummary({ resourceId }: RatingSummaryProps) {
  const { data, isLoading } = useRatingSummary(resourceId);

  if (isLoading) {
    return (
      <div className="h-32 animate-pulse rounded-lg bg-muted" />
    );
  }

  if (!data || data.count === 0) {
    return (
      <p className="text-sm text-muted-foreground">No reviews yet</p>
    );
  }

  const maxCount = Math.max(...Object.values(data.distribution), 1);

  return (
    <div className="flex gap-6">
      <div className="flex flex-col items-center justify-center">
        <span className="text-4xl font-bold">{data.average.toFixed(1)}</span>
        <StarRating rating={data.average} size="md" />
        <span className="mt-1 text-sm text-muted-foreground">
          {data.count} {data.count === 1 ? "review" : "reviews"}
        </span>
      </div>

      <div className="flex-1 space-y-1.5">
        {[5, 4, 3, 2, 1].map((star) => {
          const count = data.distribution[String(star)] ?? 0;
          const pct = (count / maxCount) * 100;

          return (
            <div key={star} className="flex items-center gap-2 text-sm">
              <span className="w-3 text-right text-muted-foreground">{star}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-yellow-400"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="w-6 text-right text-xs text-muted-foreground">{count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/reviews/star-rating.tsx frontend/src/components/reviews/rating-summary.tsx
git commit -m "feat(reviews): add StarRating and RatingSummary components"
```

---

### Task 4: ImageCarousel Component

**Files:**
- Create: `frontend/src/components/public/image-carousel.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/public/image-carousel.tsx`:

```tsx
"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Image as ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ImageCarouselProps {
  images: string[];
  alt: string;
}

export function ImageCarousel({ images, alt }: ImageCarouselProps) {
  const [current, setCurrent] = useState(0);

  if (images.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl bg-gradient-to-br from-muted to-muted/50 sm:h-80 lg:h-96">
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <ImageIcon className="h-12 w-12" />
          <span className="text-sm">No images available</span>
        </div>
      </div>
    );
  }

  if (images.length === 1) {
    return (
      <div className="overflow-hidden rounded-xl">
        <img
          src={images[0]}
          alt={alt}
          className="h-64 w-full object-cover sm:h-80 lg:h-96"
        />
      </div>
    );
  }

  function prev() {
    setCurrent((c) => (c === 0 ? images.length - 1 : c - 1));
  }

  function next() {
    setCurrent((c) => (c === images.length - 1 ? 0 : c + 1));
  }

  return (
    <div className="group relative overflow-hidden rounded-xl">
      <img
        src={images[current]}
        alt={`${alt} — image ${current + 1}`}
        className="h-64 w-full object-cover sm:h-80 lg:h-96"
      />

      <Button
        variant="secondary"
        size="icon"
        className="absolute left-3 top-1/2 h-9 w-9 -translate-y-1/2 opacity-0 transition-opacity group-hover:opacity-100"
        onClick={prev}
      >
        <ChevronLeft className="h-5 w-5" />
      </Button>

      <Button
        variant="secondary"
        size="icon"
        className="absolute right-3 top-1/2 h-9 w-9 -translate-y-1/2 opacity-0 transition-opacity group-hover:opacity-100"
        onClick={next}
      >
        <ChevronRight className="h-5 w-5" />
      </Button>

      <div className="absolute bottom-3 left-1/2 flex -translate-x-1/2 gap-1.5">
        {images.map((_, i) => (
          <button
            key={i}
            onClick={() => setCurrent(i)}
            className={cn(
              "h-2 w-2 rounded-full transition-colors",
              i === current ? "bg-white" : "bg-white/50"
            )}
          />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/public/image-carousel.tsx
git commit -m "feat(public): add ImageCarousel component"
```

---

### Task 5: StarSelector Input Component

**Files:**
- Create: `frontend/src/components/public/star-selector.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/public/star-selector.tsx`:

```tsx
"use client";

import { useState } from "react";
import { Star } from "lucide-react";
import { cn } from "@/lib/utils";

interface StarSelectorProps {
  value: number;
  onChange: (rating: number) => void;
  max?: number;
}

export function StarSelector({ value, onChange, max = 5 }: StarSelectorProps) {
  const [hover, setHover] = useState(0);

  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: max }, (_, i) => {
        const starValue = i + 1;
        const active = starValue <= (hover || value);

        return (
          <button
            key={i}
            type="button"
            onMouseEnter={() => setHover(starValue)}
            onMouseLeave={() => setHover(0)}
            onClick={() => onChange(starValue)}
            className="rounded-sm p-0.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Star
              className={cn(
                "h-7 w-7 transition-colors",
                active
                  ? "fill-yellow-400 text-yellow-400"
                  : "fill-muted text-muted-foreground/30"
              )}
            />
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/public/star-selector.tsx
git commit -m "feat(public): add StarSelector interactive input component"
```

---

### Task 6: BookingCard Component

**Files:**
- Create: `frontend/src/components/public/booking-card.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/public/booking-card.tsx`:

```tsx
"use client";

import { useRouter } from "next/navigation";
import { Clock, Loader2 } from "lucide-react";
import { useBookingFlow } from "@/hooks/use-booking-flow";
import { useAuthStore } from "@/lib/auth-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ResourceResponse } from "@/types/api";

interface BookingCardProps {
  resource: ResourceResponse;
  availabilityModel: string;
}

function priceUnit(model: string): string {
  switch (model) {
    case "hourly":
      return "/ hour";
    case "time_slot":
      return "/ slot";
    case "date_range":
      return "/ day";
    default:
      return "";
  }
}

export function BookingCard({ resource, availabilityModel }: BookingCardProps) {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const flow = useBookingFlow({ resourceId: resource.id, availabilityModel });

  async function handleCheckAndHold() {
    if (!isAuthenticated) {
      const returnUrl = `/resources/${resource.id}`;
      router.push(`/login?returnUrl=${encodeURIComponent(returnUrl)}`);
      return;
    }
    await flow.checkAndHold();
  }

  async function handleConfirm() {
    const booking = await flow.confirmBooking();
    if (booking) {
      flow.reset();
      router.push(`/bookings/${booking.id}`);
    }
  }

  return (
    <Card className="sticky top-24">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-baseline gap-1">
          <span className="text-2xl font-bold">
            {resource.currency} {resource.base_price.toFixed(2)}
          </span>
          <span className="text-sm font-normal text-muted-foreground">
            {priceUnit(availabilityModel)}
          </span>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {flow.step === "dates" && (
          <>
            <div className="space-y-2">
              <Label htmlFor="bc-start-date">Start Date</Label>
              <Input
                id="bc-start-date"
                type="date"
                value={flow.startDate}
                onChange={(e) => flow.setStartDate(e.target.value)}
              />
            </div>

            {flow.showTime && (
              <div className="space-y-2">
                <Label htmlFor="bc-start-time">Start Time</Label>
                <Input
                  id="bc-start-time"
                  type="time"
                  value={flow.startTime}
                  onChange={(e) => flow.setStartTime(e.target.value)}
                />
              </div>
            )}

            {!flow.hideEndDate && (
              <div className="space-y-2">
                <Label htmlFor="bc-end-date">End Date</Label>
                <Input
                  id="bc-end-date"
                  type="date"
                  value={flow.endDate}
                  onChange={(e) => flow.setEndDate(e.target.value)}
                />
              </div>
            )}

            {flow.showTime && (
              <div className="space-y-2">
                <Label htmlFor="bc-end-time">End Time</Label>
                <Input
                  id="bc-end-time"
                  type="time"
                  value={flow.endTime}
                  onChange={(e) => flow.setEndTime(e.target.value)}
                />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="bc-notes">Notes (optional)</Label>
              <Input
                id="bc-notes"
                placeholder="Any special requests..."
                value={flow.notes}
                onChange={(e) => flow.setNotes(e.target.value)}
              />
            </div>

            <Button
              className="w-full"
              onClick={handleCheckAndHold}
              disabled={flow.isPending}
            >
              {flow.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Check Availability
            </Button>
          </>
        )}

        {flow.step === "held" && (
          <>
            <div className="rounded-lg border p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Total Price</span>
                <span className="text-lg font-semibold">
                  {resource.currency} {flow.holdPrice.toFixed(2)}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">
                  <Clock className="mr-1 inline h-4 w-4" />
                  Hold expires in
                </span>
                <span
                  className={`font-mono text-sm font-semibold ${
                    flow.countdown < 60 ? "text-destructive" : "text-foreground"
                  }`}
                >
                  {flow.countdownFormatted}
                </span>
              </div>
            </div>

            <div className="rounded-lg border p-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Start</span>
                <span>
                  {flow.startDate}
                  {flow.showTime ? ` ${flow.startTime}` : ""}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">End</span>
                <span>
                  {flow.hideEndDate ? flow.startDate : flow.endDate}
                  {flow.showTime ? ` ${flow.endTime}` : ""}
                </span>
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => flow.cancel()}
                disabled={flow.isPending}
              >
                Cancel
              </Button>
              <Button
                className="flex-1"
                onClick={handleConfirm}
                disabled={flow.isPending}
              >
                {flow.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Book Now
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/public/booking-card.tsx
git commit -m "feat(public): add BookingCard component with availability flow"
```

---

### Task 7: ReviewList + ReviewForm Components

**Files:**
- Create: `frontend/src/components/public/review-list.tsx`
- Create: `frontend/src/components/public/review-form.tsx`

- [ ] **Step 1: Create review-list.tsx**

Create `frontend/src/components/public/review-list.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useReviews } from "@/hooks/use-reviews";
import { useAuthStore } from "@/lib/auth-store";
import { StarRating } from "@/components/reviews/star-rating";
import { RatingSummary } from "@/components/reviews/rating-summary";
import { ReviewForm } from "./review-form";
import { Button } from "@/components/ui/button";

interface ReviewListProps {
  resourceId: string;
}

const PAGE_SIZE = 10;

export function ReviewList({ resourceId }: ReviewListProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [formOpen, setFormOpen] = useState(false);

  const { data: reviews, isLoading, refetch } = useReviews({
    resource_id: resourceId,
    direction: "guest_to_resource",
    limit,
  });

  return (
    <section id="reviews" className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Reviews</h2>
        {isAuthenticated && (
          <Button variant="outline" size="sm" onClick={() => setFormOpen(true)}>
            Write a Review
          </Button>
        )}
      </div>

      <RatingSummary resourceId={resourceId} />

      {isLoading && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      )}

      {reviews && reviews.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No reviews yet. Be the first to leave a review!
        </p>
      )}

      {reviews && reviews.length > 0 && (
        <div className="space-y-4">
          {reviews.map((review) => (
            <div key={review.id} className="space-y-1.5 border-b pb-4 last:border-0">
              <div className="flex items-center gap-3">
                <StarRating rating={review.rating} size="sm" />
                <span className="text-xs text-muted-foreground">
                  {new Date(review.created_at).toLocaleDateString()}
                </span>
              </div>
              {review.comment && (
                <p className="text-sm leading-relaxed">{review.comment}</p>
              )}
            </div>
          ))}

          {reviews.length >= limit && (
            <Button
              variant="ghost"
              className="w-full"
              onClick={() => setLimit((l) => l + PAGE_SIZE)}
            >
              Show more reviews
            </Button>
          )}
        </div>
      )}

      <ReviewForm
        resourceId={resourceId}
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSuccess={() => {
          setFormOpen(false);
          refetch();
        }}
      />
    </section>
  );
}
```

- [ ] **Step 2: Create review-form.tsx**

Create `frontend/src/components/public/review-form.tsx`:

```tsx
"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { useCreateReview } from "@/hooks/use-reviews";
import { StarSelector } from "./star-selector";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import type { AxiosError } from "axios";

interface ReviewFormProps {
  resourceId: string;
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function ReviewForm({ resourceId, open, onClose, onSuccess }: ReviewFormProps) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const createReview = useCreateReview();

  async function handleSubmit() {
    if (rating === 0) {
      toast.error("Please select a rating");
      return;
    }

    try {
      await createReview.mutateAsync({
        resource_id: resourceId,
        rating,
        comment: comment || undefined,
        direction: "guest_to_resource",
      });
      toast.success("Review submitted!");
      setRating(0);
      setComment("");
      onSuccess();
    } catch (err) {
      const axiosErr = err as AxiosError;
      if (axiosErr.response?.status === 403) {
        toast.error("You need a completed booking to leave a review");
      } else {
        toast.error("Failed to submit review");
      }
    }
  }

  function handleOpenChange(isOpen: boolean) {
    if (!isOpen) {
      setRating(0);
      setComment("");
      onClose();
    }
  }

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Write a Review</SheetTitle>
          <SheetDescription>
            Share your experience with this resource.
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-4 px-4">
          <div className="space-y-2">
            <Label>Rating</Label>
            <StarSelector value={rating} onChange={setRating} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="review-comment">Comment (optional)</Label>
            <Textarea
              id="review-comment"
              placeholder="Tell others about your experience..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={4}
            />
          </div>
        </div>

        <SheetFooter>
          <Button
            onClick={handleSubmit}
            disabled={createReview.isPending || rating === 0}
          >
            {createReview.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Submit Review
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/public/review-list.tsx frontend/src/components/public/review-form.tsx
git commit -m "feat(public): add ReviewList and ReviewForm components"
```

---

### Task 8: Public Resource Detail Page

**Files:**
- Create: `frontend/src/app/(public)/resources/[id]/page.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/src/app/(public)/resources/[id]/page.tsx`:

```tsx
"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { MapPin } from "lucide-react";
import api from "@/lib/api";
import type { ResourceResponse, ResourceTypeResponse } from "@/types/api";
import { useAttachments } from "@/hooks/use-storage";
import { StarRating } from "@/components/reviews/star-rating";
import { ImageCarousel } from "@/components/public/image-carousel";
import { BookingCard } from "@/components/public/booking-card";
import { ReviewList } from "@/components/public/review-list";
import { Badge } from "@/components/ui/badge";

export default function ResourceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const { data: resource, isLoading: resourceLoading } = useQuery({
    queryKey: ["resource", id],
    queryFn: async () => {
      const { data } = await api.get<ResourceResponse>(`/resources/${id}`);
      return data;
    },
  });

  const { data: resourceTypes } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types");
      return data;
    },
  });

  const { data: attachments } = useAttachments("resource", id);

  const resourceType = resourceTypes?.find((t) => t.id === resource?.type_id);
  const images = attachments?.map((a) => a.url) ?? [];
  const attributes = resource?.attributes as Record<string, unknown> | null;

  if (resourceLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!resource) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-2">
        <h1 className="text-2xl font-bold">Resource not found</h1>
        <p className="text-muted-foreground">This resource may have been removed.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <ImageCarousel images={images} alt={resource.name} />

      <div className="mt-6 grid gap-8 lg:grid-cols-[1fr_380px]">
        {/* Left column — content */}
        <div className="space-y-8">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold sm:text-3xl">{resource.name}</h1>
              {resourceType && (
                <Badge variant="secondary">{resourceType.name}</Badge>
              )}
            </div>

            {(resource.rating_count ?? 0) > 0 && (
              <button
                onClick={() => document.getElementById("reviews")?.scrollIntoView({ behavior: "smooth" })}
                className="mt-1 flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
              >
                <StarRating rating={resource.rating_avg} size="sm" />
                <span>
                  {resource.rating_avg.toFixed(1)} ({resource.rating_count}{" "}
                  {resource.rating_count === 1 ? "review" : "reviews"})
                </span>
              </button>
            )}
          </div>

          {resource.location_address && (
            <div className="flex items-start gap-2 text-sm text-muted-foreground">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{resource.location_address}</span>
            </div>
          )}

          {resource.description && (
            <div>
              <h2 className="mb-2 text-lg font-semibold">About</h2>
              <p className="leading-relaxed text-muted-foreground">
                {resource.description}
              </p>
            </div>
          )}

          {attributes && Object.keys(attributes).length > 0 && (
            <div>
              <h2 className="mb-3 text-lg font-semibold">Details</h2>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {Object.entries(attributes).map(([key, val]) => (
                  <div key={key} className="rounded-lg border p-3">
                    <p className="text-xs text-muted-foreground capitalize">
                      {key.replace(/_/g, " ")}
                    </p>
                    <p className="mt-0.5 text-sm font-medium">
                      {Array.isArray(val) ? val.join(", ") : String(val)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <ReviewList resourceId={id} />
        </div>

        {/* Right column — booking card (hidden on mobile, shown at bottom) */}
        <div className="hidden lg:block">
          <BookingCard
            resource={resource}
            availabilityModel={resourceType?.availability_model ?? "date_range"}
          />
        </div>
      </div>

      {/* Mobile fixed bottom bar */}
      <div className="fixed bottom-0 left-0 right-0 border-t bg-background p-4 lg:hidden">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div>
            <span className="text-lg font-bold">
              {resource.currency} {resource.base_price.toFixed(2)}
            </span>
            <span className="ml-1 text-sm text-muted-foreground">
              {priceUnitShort(resourceType?.availability_model ?? "date_range")}
            </span>
          </div>
          <a
            href="#booking-mobile"
            className="inline-flex items-center rounded-md bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground"
            onClick={(e) => {
              e.preventDefault();
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          >
            Book Now
          </a>
        </div>
      </div>

      {/* Mobile booking card (visible only on mobile, below content) */}
      <div className="mt-8 lg:hidden" id="booking-mobile">
        <BookingCard
          resource={resource}
          availabilityModel={resourceType?.availability_model ?? "date_range"}
        />
      </div>

      {/* Bottom padding for fixed mobile bar */}
      <div className="h-20 lg:hidden" />
    </div>
  );
}

function priceUnitShort(model: string): string {
  switch (model) {
    case "hourly":
      return "/hr";
    case "time_slot":
      return "/slot";
    case "date_range":
      return "/day";
    default:
      return "";
  }
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npx tsc --noEmit --pretty 2>&1 | head -30
```

- [ ] **Step 3: Manual verification**

Run the dev server. Navigate to a resource detail page (e.g., `/resources/{some-id}`). Verify:
- Image carousel renders (placeholder if no images)
- Two-column layout on desktop, single column on mobile
- Booking card sticky on desktop, fixed bottom bar on mobile
- Check Availability → Hold → Confirm flow works
- Reviews section renders with rating summary + list
- "Write a Review" button opens sheet (if authenticated)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/\(public\)/resources/\[id\]/page.tsx
git commit -m "feat(public): add resource detail page with booking and reviews"
```

---

## Verification Checklist

- [ ] `useBookingFlow` hook extracted and both admin sheet + public card use it
- [ ] ImageCarousel handles 0, 1, and multiple images
- [ ] BookingCard redirects unauthenticated users to login with returnUrl
- [ ] Hold countdown works, releases on cancel/expiry
- [ ] StarRating displays read-only stars, StarSelector allows interactive selection
- [ ] RatingSummary shows aggregate rating + distribution bars
- [ ] ReviewList paginates with "Show more", ReviewForm handles 403 (not eligible)
- [ ] Resource detail page two-column on desktop, single column on mobile
- [ ] Mobile fixed bottom bar shows price + "Book Now"
- [ ] TypeScript compiles with no errors
