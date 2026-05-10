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
  }, [step, countdown <= 0, clearTimer]);

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
