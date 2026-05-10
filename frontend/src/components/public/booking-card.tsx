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
