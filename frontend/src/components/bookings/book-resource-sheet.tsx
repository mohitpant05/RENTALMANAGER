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
  slotConfig?: Record<string, unknown> | null;
}

export function BookResourceSheet({
  open,
  onClose,
  resourceId,
  resourceName,
  availabilityModel,
  slotConfig,
}: BookResourceSheetProps) {
  const router = useRouter();
  const flow = useBookingFlow({ resourceId, availabilityModel, slotConfig });

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

              {flow.allowedDurations.length > 0 && flow.showTime && (
                <p className="text-xs text-muted-foreground">
                  Available slot durations:{" "}
                  {(slotConfig?.duration_options as string[])?.join(", ")}
                </p>
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
