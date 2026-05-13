# Customer Bookings & Profile — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build customer-facing booking management (list + detail with timeline), profile page with reviews, and public notifications page.

**Architecture:** Card-based booking list with tab filters, detail page with visual status timeline and cancel action. Profile page shows user info form (submit disabled until backend supports it) plus "My Reviews" list. Notifications page reuses shared hooks from Plan 14. All pages require authentication and redirect to login if not authenticated.

**Tech Stack:** Next.js 15, TypeScript, React Query v5, shadcn/ui, Zustand, Tailwind CSS

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `components/public/booking-card-public.tsx` | Card component for customer booking list |
| Create | `components/public/booking-timeline.tsx` | Visual status progression dots + lines |
| Create | `app/(public)/bookings/page.tsx` | Customer bookings list page |
| Create | `app/(public)/bookings/[id]/page.tsx` | Customer booking detail page |
| Create | `components/public/profile-form.tsx` | User profile form |
| Create | `app/(public)/profile/page.tsx` | Customer profile page |
| Create | `app/(public)/notifications/page.tsx` | Customer notifications page |

**Prerequisites:** Plan 14 (types, hooks, admin route migration) and Plan 22 (review components) must be completed first.

---

### Task 1: BookingCardPublic Component

**Files:**
- Create: `frontend/src/components/public/booking-card-public.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/public/booking-card-public.tsx`:

```tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/public/booking-card-public.tsx
git commit -m "feat(public): add BookingCardPublic component"
```

---

### Task 2: BookingTimeline Component

**Files:**
- Create: `frontend/src/components/public/booking-timeline.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/public/booking-timeline.tsx`:

```tsx
import { cn } from "@/lib/utils";

interface BookingTimelineProps {
  currentStatus: string;
}

const STEPS = ["pending", "confirmed", "active", "completed"];

const STEP_LABELS: Record<string, string> = {
  pending: "Pending",
  confirmed: "Confirmed",
  active: "Active",
  completed: "Completed",
};

const CANCELLED_STATUSES = ["cancelled", "rejected", "no_show"];

export function BookingTimeline({ currentStatus }: BookingTimelineProps) {
  if (CANCELLED_STATUSES.includes(currentStatus)) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3">
        <div className="h-3 w-3 rounded-full bg-destructive" />
        <span className="text-sm font-medium capitalize text-destructive">
          {currentStatus.replace(/_/g, " ")}
        </span>
      </div>
    );
  }

  const currentIndex = STEPS.indexOf(currentStatus);

  return (
    <div className="flex items-center">
      {STEPS.map((step, i) => {
        const isPast = i < currentIndex;
        const isCurrent = i === currentIndex;
        const isFuture = i > currentIndex;

        return (
          <div key={step} className="flex items-center">
            <div className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-semibold",
                  isPast && "border-primary bg-primary text-primary-foreground",
                  isCurrent && "border-primary bg-primary/10 text-primary",
                  isFuture && "border-muted-foreground/30 bg-muted text-muted-foreground/50"
                )}
              >
                {i + 1}
              </div>
              <span
                className={cn(
                  "text-xs",
                  isCurrent ? "font-medium text-foreground" : "text-muted-foreground"
                )}
              >
                {STEP_LABELS[step]}
              </span>
            </div>

            {i < STEPS.length - 1 && (
              <div
                className={cn(
                  "mx-1 h-0.5 w-8 sm:w-12",
                  i < currentIndex ? "bg-primary" : "bg-muted-foreground/20"
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/public/booking-timeline.tsx
git commit -m "feat(public): add BookingTimeline visual status component"
```

---

### Task 3: Customer Bookings List Page

**Files:**
- Create: `frontend/src/app/(public)/bookings/page.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/src/app/(public)/bookings/page.tsx`:

```tsx
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
    if (attachments.length > 0) {
      resourceImages[resourceId] = attachments[0].url;
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
            <Button asChild variant="outline" className="mt-4">
              <Link href="/">Browse Resources</Link>
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
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npx tsc --noEmit --pretty 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(public\)/bookings/page.tsx
git commit -m "feat(public): add customer bookings list page with tab filters"
```

---

### Task 4: Customer Booking Detail Page

**Files:**
- Create: `frontend/src/app/(public)/bookings/[id]/page.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/src/app/(public)/bookings/[id]/page.tsx`:

```tsx
"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CalendarDays, Loader2, Image as ImageIcon } from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { BookingResponse, ResourceResponse, AttachmentResponse } from "@/types/api";
import { BookingTimeline } from "@/components/public/booking-timeline";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

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
  return `${d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" })} at ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}

export default function CustomerBookingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const authLoading = useAuthStore((s) => s.isLoading);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");

  if (!authLoading && !isAuthenticated) {
    router.push(`/login?returnUrl=/bookings/${id}`);
    return null;
  }

  const { data: booking, isLoading } = useQuery({
    queryKey: ["booking", id],
    queryFn: async () => {
      const { data } = await api.get<BookingResponse>(`/bookings/${id}`);
      return data;
    },
    enabled: isAuthenticated,
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

  const { data: attachments } = useQuery({
    queryKey: ["attachments", "resource", booking?.resource_id],
    queryFn: async () => {
      const { data } = await api.get<AttachmentResponse[]>(
        `/storage/attachments?entity_type=resource&entity_id=${booking!.resource_id}`
      );
      return data;
    },
    enabled: !!booking?.resource_id,
  });

  const cancelMutation = useMutation({
    mutationFn: async (reason: string) => {
      const { data } = await api.post<BookingResponse>(
        `/bookings/${id}/cancel`,
        reason ? { reason } : {}
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["booking", id] });
      queryClient.invalidateQueries({ queryKey: ["bookings"] });
      toast.success("Booking cancelled");
      setCancelOpen(false);
      setCancelReason("");
    },
    onError: () => {
      toast.error("Failed to cancel booking");
    },
  });

  const imageUrl = attachments?.[0]?.url;
  const canCancel = booking?.status === "pending" || booking?.status === "confirmed";

  if (authLoading || isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!booking) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-2">
        <h1 className="text-2xl font-bold">Booking not found</h1>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <Button variant="ghost" size="sm" asChild className="mb-4">
        <Link href="/bookings">
          <ArrowLeft className="mr-1 h-4 w-4" />
          Back to bookings
        </Link>
      </Button>

      {/* Resource info card */}
      <Card className="mb-6">
        <CardContent className="flex gap-4 p-4">
          {imageUrl ? (
            <img
              src={imageUrl}
              alt={resource?.name ?? "Resource"}
              className="h-24 w-24 shrink-0 rounded-lg object-cover"
            />
          ) : (
            <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-lg bg-muted">
              <ImageIcon className="h-10 w-10 text-muted-foreground" />
            </div>
          )}
          <div className="flex flex-col justify-center">
            <Link
              href={`/resources/${booking.resource_id}`}
              className="text-lg font-semibold hover:underline"
            >
              {resource?.name ?? "Resource"}
            </Link>
            {resource?.location_address && (
              <p className="text-sm text-muted-foreground">{resource.location_address}</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Status + Timeline */}
      <Card className="mb-6">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Status</CardTitle>
            <Badge variant={STATUS_VARIANT[booking.status] ?? "muted"}>
              {booking.status.replace(/_/g, " ")}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <BookingTimeline currentStatus={booking.status} />
        </CardContent>
      </Card>

      {/* Booking details */}
      <Card className="mb-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">
              <CalendarDays className="mr-1.5 inline h-4 w-4" />
              Start
            </span>
            <span className="text-sm font-medium">
              {formatDateTime(booking.start_time)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">
              <CalendarDays className="mr-1.5 inline h-4 w-4" />
              End
            </span>
            <span className="text-sm font-medium">
              {formatDateTime(booking.end_time)}
            </span>
          </div>
          <div className="flex items-center justify-between border-t pt-3">
            <span className="text-sm text-muted-foreground">Total Price</span>
            <span className="text-lg font-bold">
              {booking.currency} {booking.total_price.toFixed(2)}
            </span>
          </div>
          {booking.notes && (
            <div className="border-t pt-3">
              <span className="text-sm text-muted-foreground">Notes</span>
              <p className="mt-1 text-sm">{booking.notes}</p>
            </div>
          )}
          {booking.cancellation_reason && (
            <div className="border-t pt-3">
              <span className="text-sm text-muted-foreground">Cancellation Reason</span>
              <p className="mt-1 text-sm">{booking.cancellation_reason}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex gap-3">
        {canCancel && (
          <Button
            variant="destructive"
            onClick={() => setCancelOpen(true)}
          >
            Cancel Booking
          </Button>
        )}
        {booking.status === "completed" && (
          <Button variant="outline" asChild>
            <Link href={`/resources/${booking.resource_id}#reviews`}>
              Write a Review
            </Link>
          </Button>
        )}
      </div>

      {/* Cancel Sheet */}
      <Sheet open={cancelOpen} onOpenChange={(o) => !o && setCancelOpen(false)}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Cancel Booking</SheetTitle>
            <SheetDescription>
              Are you sure you want to cancel this booking? This cannot be undone.
            </SheetDescription>
          </SheetHeader>

          <div className="space-y-4 px-4">
            <div className="space-y-2">
              <Label htmlFor="cancel-reason">Reason (optional)</Label>
              <Textarea
                id="cancel-reason"
                placeholder="Why are you cancelling?"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                rows={3}
              />
            </div>
          </div>

          <SheetFooter>
            <div className="flex w-full gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setCancelOpen(false)}
              >
                Keep Booking
              </Button>
              <Button
                variant="destructive"
                className="flex-1"
                onClick={() => cancelMutation.mutate(cancelReason)}
                disabled={cancelMutation.isPending}
              >
                {cancelMutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Cancel Booking
              </Button>
            </div>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npx tsc --noEmit --pretty 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(public\)/bookings/\[id\]/page.tsx
git commit -m "feat(public): add customer booking detail page with cancel action"
```

---

### Task 5: ProfileForm Component

**Files:**
- Create: `frontend/src/components/public/profile-form.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/public/profile-form.tsx`:

```tsx
"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { UserResponse } from "@/types/api";

const profileSchema = z.object({
  full_name: z.string().min(1, "Name is required"),
  email: z.string().email(),
  phone: z.string().optional(),
});

type ProfileFormData = z.infer<typeof profileSchema>;

interface ProfileFormProps {
  user: UserResponse;
}

export function ProfileForm({ user }: ProfileFormProps) {
  const {
    register,
    formState: { errors },
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user.full_name,
      email: user.email,
      phone: user.phone ?? "",
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Personal Information</CardTitle>
        <CardDescription>Profile updates coming soon</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="full_name">Full Name</Label>
            <Input id="full_name" {...register("full_name")} />
            {errors.full_name && (
              <p className="text-xs text-destructive">{errors.full_name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" {...register("email")} disabled className="bg-muted" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="phone">Phone</Label>
            <Input id="phone" {...register("phone")} placeholder="Optional" />
          </div>

          <Button type="button" disabled>
            Save Changes
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/public/profile-form.tsx
git commit -m "feat(public): add ProfileForm component (submit disabled until backend ready)"
```

---

### Task 6: Customer Profile Page

**Files:**
- Create: `frontend/src/app/(public)/profile/page.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/src/app/(public)/profile/page.tsx`:

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/auth-store";
import { useMyReviews } from "@/hooks/use-reviews";
import { ProfileForm } from "@/components/public/profile-form";
import { StarRating } from "@/components/reviews/star-rating";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Lock } from "lucide-react";

export default function ProfilePage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isLoading = useAuthStore((s) => s.isLoading);

  if (!isLoading && !isAuthenticated) {
    router.push("/login?returnUrl=/profile");
    return null;
  }

  const { data: reviews, isLoading: reviewsLoading } = useMyReviews({ limit: 20 });

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="mx-auto max-w-2xl px-4 py-6 space-y-6">
      <h1 className="text-2xl font-bold">Profile</h1>

      <ProfileForm user={user} />

      {/* My Reviews */}
      <Card>
        <CardHeader>
          <CardTitle>My Reviews</CardTitle>
          <CardDescription>Reviews you have written</CardDescription>
        </CardHeader>
        <CardContent>
          {reviewsLoading && (
            <div className="space-y-3">
              {[1, 2].map((i) => (
                <div key={i} className="h-16 animate-pulse rounded bg-muted" />
              ))}
            </div>
          )}

          {reviews && reviews.length === 0 && (
            <p className="text-sm text-muted-foreground">
              You haven't written any reviews yet.
            </p>
          )}

          {reviews && reviews.length > 0 && (
            <div className="space-y-4">
              {reviews.map((review) => (
                <div key={review.id} className="space-y-1 border-b pb-3 last:border-0">
                  <div className="flex items-center gap-3">
                    <StarRating rating={review.rating} size="sm" />
                    <span className="text-xs text-muted-foreground">
                      {new Date(review.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {review.comment && (
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {review.comment}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Change Password — coming soon */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lock className="h-4 w-4" />
            Change Password
          </CardTitle>
          <CardDescription>Coming soon</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Password changes will be available in a future update.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/\(public\)/profile/page.tsx
git commit -m "feat(public): add customer profile page with reviews and placeholder sections"
```

---

### Task 7: Public Notifications Page

**Files:**
- Create: `frontend/src/app/(public)/notifications/page.tsx`

- [ ] **Step 1: Create the page**

Create `frontend/src/app/(public)/notifications/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bell, Check, CheckCheck } from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import {
  useNotifications,
  useMarkRead,
  useMarkAllRead,
} from "@/hooks/use-notifications";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 20;

const EVENT_ICONS: Record<string, string> = {
  booking_created: "CalendarPlus",
  booking_confirmed: "CheckCircle",
  booking_cancelled: "XCircle",
  booking_rejected: "XCircle",
  review_received: "Star",
};

function getNavigationUrl(notification: { event_type: string; payload: Record<string, unknown> }): string {
  const bookingId = notification.payload.booking_id as string | undefined;
  switch (notification.event_type) {
    case "booking_created":
    case "booking_confirmed":
    case "booking_cancelled":
    case "booking_rejected":
      return bookingId ? `/bookings/${bookingId}` : "/notifications";
    case "review_received":
      return "/profile";
    default:
      return "/notifications";
  }
}

export default function PublicNotificationsPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const authLoading = useAuthStore((s) => s.isLoading);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [limit, setLimit] = useState(PAGE_SIZE);

  if (!authLoading && !isAuthenticated) {
    router.push("/login?returnUrl=/notifications");
    return null;
  }

  const { data: notifications, isLoading } = useNotifications({
    unread_only: unreadOnly || undefined,
    limit,
  });
  const markRead = useMarkRead();
  const markAllRead = useMarkAllRead();

  function handleClick(notification: { id: string; is_read: boolean; event_type: string; payload: Record<string, unknown> }) {
    if (!notification.is_read) {
      markRead.mutate(notification.id);
    }
    const url = getNavigationUrl(notification);
    router.push(url);
  }

  if (authLoading || isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Notifications</h1>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => markAllRead.mutate()}
          disabled={markAllRead.isPending}
        >
          <CheckCheck className="mr-1.5 h-4 w-4" />
          Mark all read
        </Button>
      </div>

      <div className="mt-4 flex gap-2">
        <Button
          variant={!unreadOnly ? "default" : "outline"}
          size="sm"
          onClick={() => setUnreadOnly(false)}
        >
          All
        </Button>
        <Button
          variant={unreadOnly ? "default" : "outline"}
          size="sm"
          onClick={() => setUnreadOnly(true)}
        >
          Unread
        </Button>
      </div>

      <div className="mt-6 space-y-2">
        {notifications && notifications.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
            <Bell className="h-12 w-12 text-muted-foreground" />
            <p className="mt-3 text-muted-foreground">No notifications</p>
          </div>
        )}

        {notifications?.map((n) => (
          <Card
            key={n.id}
            className={cn(
              "cursor-pointer transition-colors hover:bg-muted/50",
              !n.is_read && "border-primary/20 bg-primary/5"
            )}
            onClick={() => handleClick(n)}
          >
            <CardContent className="flex items-start gap-3 p-4">
              <div className="mt-0.5">
                {!n.is_read ? (
                  <div className="h-2.5 w-2.5 rounded-full bg-primary" />
                ) : (
                  <Check className="h-3 w-3 text-muted-foreground" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className={cn("text-sm", !n.is_read && "font-medium")}>
                  {n.message}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {new Date(n.created_at).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>
            </CardContent>
          </Card>
        ))}

        {notifications && notifications.length >= limit && (
          <Button
            variant="ghost"
            className="w-full"
            onClick={() => setLimit((l) => l + PAGE_SIZE)}
          >
            Load more
          </Button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npx tsc --noEmit --pretty 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(public\)/notifications/page.tsx
git commit -m "feat(public): add customer notifications page"
```

---

## Verification Checklist

- [ ] BookingCardPublic shows image, resource name, dates, status badge, price
- [ ] BookingTimeline renders 4-step progression for normal statuses, red badge for cancelled/rejected/no_show
- [ ] Customer bookings list has working tab filters: All, Upcoming, Active, Past, Cancelled
- [ ] Empty state shows "No bookings yet" with browse link
- [ ] Booking detail shows resource card, timeline, schedule, price, notes
- [ ] Cancel button works for pending/confirmed bookings with reason sheet
- [ ] "Write a Review" link shows on completed bookings → resource detail #reviews
- [ ] Profile form renders with disabled submit, email is read-only
- [ ] My Reviews section shows user's reviews with star ratings
- [ ] Change Password section shows "Coming soon"
- [ ] Notifications page loads, unread filter works, mark all read works
- [ ] Clicking notification marks it read and navigates to correct page
- [ ] All pages redirect to login if unauthenticated
- [ ] TypeScript compiles with no errors
