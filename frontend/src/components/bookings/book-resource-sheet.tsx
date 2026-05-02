"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { CalendarDays, Clock, Loader2 } from "lucide-react";
import api from "@/lib/api";
import type {
  AvailabilityCheckResponse,
  BookingCreate,
  BookingResponse,
  HoldResponse,
  ReleaseRequest,
} from "@/types/api";
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
import { toast } from "sonner";

interface BookResourceSheetProps {
  open: boolean;
  onClose: () => void;
  resourceId: string;
  resourceName: string;
  availabilityModel: string; // "date_range" | "hourly" | "time_slot"
}

type Step = "dates" | "held" | "booked";

function formatCountdown(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function buildDatetime(date: string, time: string): string {
  return new Date(`${date}T${time}`).toISOString();
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
  const [loading, setLoading] = useState(false);

  const [holdToken, setHoldToken] = useState("");
  const [holdPrice, setHoldPrice] = useState(0);
  const [countdown, setCountdown] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const showTime = availabilityModel === "hourly" || availabilityModel === "time_slot";
  const hideEndDate = availabilityModel === "time_slot";

  const resetState = useCallback(() => {
    setStep("dates");
    setStartDate("");
    setStartTime("09:00");
    setEndDate("");
    setEndTime("17:00");
    setNotes("");
    setLoading(false);
    setHoldToken("");
    setHoldPrice(0);
    setCountdown(0);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

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

  // Countdown timer
  useEffect(() => {
    if (step !== "held" || countdown <= 0) return;

    intervalRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          toast.error("Hold expired");
          setStep("dates");
          setHoldToken("");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [step, countdown <= 0]); // eslint-disable-line react-hooks/exhaustive-deps

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

  async function handleCheckAndHold() {
    if (!startDate) {
      toast.error("Please select a start date");
      return;
    }
    if (!hideEndDate && !endDate) {
      toast.error("Please select an end date");
      return;
    }

    setLoading(true);
    try {
      const start = getStartDatetime();
      const end = getEndDatetime();

      // Step 1: Check availability
      const { data: check } = await api.post<AvailabilityCheckResponse>(
        `/resources/${resourceId}/availability/check`,
        { start, end }
      );

      if (!check.available) {
        toast.error("Resource is not available for the selected dates");
        setLoading(false);
        return;
      }

      // Step 2: Hold
      const { data: hold } = await api.post<HoldResponse>(
        `/resources/${resourceId}/availability/hold`,
        { start, end }
      );

      setHoldToken(hold.hold_token);
      setHoldPrice(hold.price);

      const expiresAt = new Date(hold.expires).getTime();
      const now = Date.now();
      const secondsLeft = Math.max(0, Math.floor((expiresAt - now) / 1000));
      setCountdown(secondsLeft);

      setStep("held");
    } catch {
      toast.error("Failed to check availability");
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm() {
    setLoading(true);
    try {
      const payload: BookingCreate = {
        resource_id: resourceId,
        hold_token: holdToken,
        start_time: getStartDatetime(),
        end_time: getEndDatetime(),
        notes: notes || undefined,
        auto_confirm: true,
      };

      const { data: booking } = await api.post<BookingResponse>(
        "/bookings",
        payload
      );

      toast.success("Booking confirmed!");
      resetState();
      onClose();
      router.push(`/bookings/${booking.id}`);
    } catch {
      toast.error("Failed to confirm booking");
    } finally {
      setLoading(false);
    }
  }

  function handleCancel() {
    if (holdToken) {
      releaseHold(holdToken);
    }
    resetState();
    onClose();
  }

  function handleOpenChange(isOpen: boolean) {
    if (!isOpen) {
      if (step === "held" && holdToken) {
        releaseHold(holdToken);
      }
      resetState();
      onClose();
    }
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
            {step === "dates" && "Select dates to check availability"}
            {step === "held" && "Review and confirm your booking"}
          </SheetDescription>
        </SheetHeader>

        <div className="flex-1 space-y-4 px-4">
          {step === "dates" && (
            <>
              <div className="space-y-2">
                <Label htmlFor="start-date">Start Date</Label>
                <Input
                  id="start-date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>

              {showTime && (
                <div className="space-y-2">
                  <Label htmlFor="start-time">Start Time</Label>
                  <Input
                    id="start-time"
                    type="time"
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                  />
                </div>
              )}

              {!hideEndDate && (
                <div className="space-y-2">
                  <Label htmlFor="end-date">End Date</Label>
                  <Input
                    id="end-date"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
              )}

              {showTime && (
                <div className="space-y-2">
                  <Label htmlFor="end-time">End Time</Label>
                  <Input
                    id="end-time"
                    type="time"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                  />
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="notes">Notes (optional)</Label>
                <Input
                  id="notes"
                  placeholder="Any special requests..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </div>
            </>
          )}

          {step === "held" && (
            <>
              <div className="rounded-lg border p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Price</span>
                  <span className="text-lg font-semibold">
                    ${holdPrice.toFixed(2)}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">
                    <Clock className="mr-1 inline h-4 w-4" />
                    Hold expires in
                  </span>
                  <span
                    className={`font-mono text-sm font-semibold ${
                      countdown < 60
                        ? "text-destructive"
                        : "text-foreground"
                    }`}
                  >
                    {formatCountdown(countdown)}
                  </span>
                </div>
              </div>

              <div className="rounded-lg border p-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Start</span>
                  <span>
                    {startDate}
                    {showTime ? ` ${startTime}` : ""}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">End</span>
                  <span>
                    {hideEndDate ? startDate : endDate}
                    {showTime ? ` ${endTime}` : ""}
                  </span>
                </div>
                {notes && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Notes</span>
                    <span className="text-right max-w-[200px]">{notes}</span>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        <SheetFooter>
          {step === "dates" && (
            <Button onClick={handleCheckAndHold} disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Check & Hold
            </Button>
          )}

          {step === "held" && (
            <div className="flex w-full gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={handleCancel}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button
                className="flex-1"
                onClick={handleConfirm}
                disabled={loading}
              >
                {loading && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Confirm Booking
              </Button>
            </div>
          )}
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
