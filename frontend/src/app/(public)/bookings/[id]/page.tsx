"use client";

import { use, useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CalendarDays, Loader2, Image as ImageIcon, PackagePlus } from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { BookingResponse, ResourceResponse, AttachmentResponse, ResourceTypeResponse } from "@/types/api";
import { BookingTimeline } from "@/components/public/booking-timeline";
import { AddonDiscoveredSection } from "@/components/public/addon-discovered-section";
import type { AddonSelections } from "@/components/public/addon-discovered-section";
import { useAddons } from "@/hooks/use-addons";
import { Separator } from "@/components/ui/separator";
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
  const [addonSelections, setAddonSelections] = useState<AddonSelections>({});
  const [addingAddons, setAddingAddons] = useState(false);

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

  const { data: resourceTypes } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types");
      return data;
    },
  });

  const { holdAndAddAddon } = useAddons();

  const resourceType = resourceTypes?.find((t) => t.id === resource?.type_id);
  const isPrimaryVenue = resourceType?.role === "primary";
  const canAddAddons = isPrimaryVenue && (booking?.status === "pending" || booking?.status === "confirmed");

  const handleAddAddons = useCallback(async () => {
    const entries = Object.entries(addonSelections);
    if (entries.length === 0) return;

    setAddingAddons(true);
    let successCount = 0;
    const bookingStart = booking!.start_time;
    const bookingEnd = booking!.end_time;

    for (const [resourceId, item] of entries) {
      const result = await holdAndAddAddon(
        id, resourceId, bookingStart, bookingEnd,
        item.schedules.length > 0 ? item.schedules : undefined,
        item.availabilityModel,
      );
      if (result) successCount++;
    }

    setAddingAddons(false);
    if (successCount > 0) {
      toast.success(`${successCount} addon(s) added successfully`);
      setAddonSelections({});
      queryClient.invalidateQueries({ queryKey: ["booking", id] });
    }
  }, [addonSelections, booking, id, holdAndAddAddon, queryClient]);

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

  const imageUrl = attachments?.find((a) => a.download_url)?.download_url;
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
      <Link href="/bookings" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="mr-1 h-4 w-4" />
        Back to bookings
      </Link>

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

      {canAddAddons && (
        <Card className="mb-6">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg">
              <PackagePlus className="h-5 w-5" />
              Add Add-ons
            </CardTitle>
          </CardHeader>
          <CardContent>
            <AddonDiscoveredSection
              resourceId={booking.resource_id}
              startDate={booking.start_time.slice(0, 10)}
              endDate={booking.end_time.slice(0, 10)}
              onSelectionChange={setAddonSelections}
            />
            {Object.keys(addonSelections).length > 0 && (
              <div className="mt-4">
                <Separator className="mb-4" />
                <Button
                  className="w-full"
                  onClick={handleAddAddons}
                  disabled={addingAddons}
                >
                  {addingAddons && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Add Selected Add-ons
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

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
          <Button variant="outline" onClick={() => router.push(`/resources/${booking.resource_id}#reviews`)}>
              Write a Review
            </Button>
        )}
      </div>

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
