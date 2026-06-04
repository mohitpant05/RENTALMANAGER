"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Check, CheckCircle2, Clock, Loader2 } from "lucide-react";
import { useBookingFlow } from "@/hooks/use-booking-flow";
import { useAuthStore } from "@/lib/auth-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { ResourceResponse } from "@/types/api";
import {
  useCurrencyStore,
  useRates,
  convertPrice,
  formatPrice,
} from "@/hooks/use-currency";
import { CurrencySelect } from "@/components/ui/currency-select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

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

const STEPS = [
  { key: "dates", label: "Select Dates" },
  { key: "available", label: "Availability" },
  { key: "held", label: "Confirm" },
] as const;

function StepIndicator({ currentStep }: { currentStep: string }) {
  const currentIdx = STEPS.findIndex((s) => s.key === currentStep);
  return (
    <div className="flex items-center gap-1 sm:gap-2">
      {STEPS.map((s, i) => {
        const done = i < currentIdx;
        const active = i === currentIdx;
        return (
          <div key={s.key} className="flex items-center gap-1 sm:gap-2">
            {i > 0 && (
              <div
                className={`h-px w-4 sm:w-8 ${done || active ? "bg-primary" : "bg-border"}`}
              />
            )}
            <div className="flex items-center gap-1 sm:gap-1.5">
              <div
                className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium ${
                  done
                    ? "bg-primary text-primary-foreground"
                    : active
                      ? "border-2 border-primary text-primary"
                      : "border border-border text-muted-foreground"
                }`}
              >
                {done ? <Check className="h-3 w-3" /> : i + 1}
              </div>
              <span
                className={`hidden text-xs sm:inline ${active ? "font-medium" : "text-muted-foreground"}`}
              >
                {s.label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function BookingCard({ resource, availabilityModel }: BookingCardProps) {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const flow = useBookingFlow({ resourceId: resource.id, availabilityModel });
  const { displayCurrency, setDisplayCurrency } = useCurrencyStore();
  const { data: rates } = useRates();
  const convertedBase = convertPrice(
    resource.base_price,
    resource.currency,
    displayCurrency,
    rates,
  );
  const convertedCheck = convertPrice(
    flow.checkPrice,
    resource.currency,
    displayCurrency,
    rates,
  );
  const convertedHold = convertPrice(
    flow.holdPrice,
    resource.currency,
    displayCurrency,
    rates,
  );

  const [open, setOpen] = useState(false);

  function handleOpen() {
    if (!isAuthenticated) {
      const returnUrl = `/resources/${resource.id}`;
      router.push(`/login?returnUrl=${encodeURIComponent(returnUrl)}`);
      return;
    }
    flow.reset();
    setOpen(true);
  }

  function handleClose() {
    if (flow.step === "held") {
      flow.cancel();
    } else {
      flow.reset();
    }
    setOpen(false);
  }

  async function handleCheckAvailability() {
    await flow.checkAvailability();
  }

  async function handleHoldAndConfirm() {
    const held = await flow.holdResource();
    if (!held) return;
  }

  async function handleConfirm() {
    const booking = await flow.confirmBooking();
    if (booking) {
      flow.reset();
      setOpen(false);
      router.push(`/bookings/${booking.id}`);
    }
  }

  return (
    <>
      <div className="rounded-xl border bg-card p-4 sm:p-6 sm:sticky sm:top-24">
        <div className="flex items-baseline gap-1">
          <span className="text-2xl font-bold">
            {formatPrice(convertedBase, displayCurrency)}
          </span>
          <span className="text-sm font-normal text-muted-foreground">
            {priceUnit(availabilityModel)}
          </span>
        </div>
        <CurrencySelect
          value={displayCurrency}
          onChange={setDisplayCurrency}
          className="mt-2 w-[130px]"
        />
        <Button className="mt-4 w-full" size="lg" onClick={handleOpen}>
          Book Now
        </Button>
      </div>

      <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Book {resource.name}</DialogTitle>
            <DialogDescription>
              {formatPrice(convertedBase, displayCurrency)}{" "}
              {priceUnit(availabilityModel)}
            </DialogDescription>
          </DialogHeader>

          <StepIndicator currentStep={flow.step} />

          {flow.step === "dates" && (
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="bc-start-date">Start Date</Label>
                <Input
                  id="bc-start-date"
                  type="date"
                  value={flow.startDate}
                  onChange={(e) => flow.setStartDate(e.target.value)}
                />
              </div>

              {flow.showTime && (
                <div className="space-y-1.5">
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
                <div className="space-y-1.5">
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
                <div className="space-y-1.5">
                  <Label htmlFor="bc-end-time">End Time</Label>
                  <Input
                    id="bc-end-time"
                    type="time"
                    value={flow.endTime}
                    onChange={(e) => flow.setEndTime(e.target.value)}
                  />
                </div>
              )}

              <div className="space-y-1.5">
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
                onClick={handleCheckAvailability}
                disabled={flow.isPending}
              >
                {flow.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Check Availability
              </Button>
            </div>
          )}

          {flow.step === "available" && (
            <div className="space-y-4">
              <div className="rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-900 dark:bg-green-950">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                  <span className="font-medium text-green-800 dark:text-green-200">
                    Available!
                  </span>
                </div>
                <p className="mt-1 text-sm text-green-700 dark:text-green-300">
                  Resource is available for your selected dates.
                </p>
              </div>

              <div className="rounded-lg border p-3 space-y-2 text-sm">
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
                {flow.checkPrice > 0 && (
                  <div className="flex justify-between border-t pt-2">
                    <span className="font-medium">Estimated Total</span>
                    <span className="font-semibold">
                      {formatPrice(convertedCheck, displayCurrency)}
                    </span>
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => flow.setStep("dates")}
                >
                  Back
                </Button>
                <Button
                  className="flex-1"
                  onClick={handleHoldAndConfirm}
                  disabled={flow.isPending}
                >
                  {flow.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Reserve & Book
                </Button>
              </div>
            </div>
          )}

          {flow.step === "held" && (
            <div className="space-y-4">
              <div className="rounded-lg border p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">
                    Total Price
                  </span>
                  <span className="text-lg font-semibold">
                    {formatPrice(convertedHold, displayCurrency)}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">
                    <Clock className="mr-1 inline h-4 w-4" />
                    Hold expires in
                  </span>
                  <span
                    className={`font-mono text-sm font-semibold ${
                      flow.countdown < 60
                        ? "text-destructive"
                        : "text-foreground"
                    }`}
                  >
                    {flow.countdownFormatted}
                  </span>
                </div>
              </div>

              <div className="rounded-lg border p-3 space-y-2 text-sm">
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
                  onClick={handleClose}
                  disabled={flow.isPending}
                >
                  Cancel
                </Button>
                <Button
                  className="flex-1"
                  onClick={handleConfirm}
                  disabled={flow.isPending}
                >
                  {flow.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Confirm Booking
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
