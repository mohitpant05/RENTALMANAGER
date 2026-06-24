"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import api from "@/lib/api";
import type {
  AvailabilityCheckResponse,
  BookingCreate,
  BookingResponse,
  HoldResponse,
  ReleaseRequest,
} from "@/types/api";
import { toast } from "sonner";

type Step = "dates" | "available" | "held" | "booked" | "confirm";

function buildDatetime(date: string, time: string): string {
  return new Date(`${date}T${time}`).toISOString();
}

function formatCountdown(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function parseDuration(s: string): number {
  const m = s.match(/^(\d+(?:\.\d+)?)\s*(h|min)$/);
  if (!m) return 0;
  return m[2] === "h" ? parseFloat(m[1]) * 60 : parseFloat(m[1]);
}

function formatDuration(minutes: number): string {
  if (minutes >= 60) {
    const h = minutes / 60;
    return h % 1 === 0 ? `${h}h` : `${h.toFixed(1)}h`;
  }
  return `${minutes}min`;
}

interface HoldConfig {
  unit: "seconds" | "minutes";
  value: number;
}

interface UseBookingFlowOptions {
  resourceId: string;
  availabilityModel: string;
  slotConfig?: Record<string, unknown> | null;
  holdConfig?: HoldConfig | null;
}

export function useBookingFlow({ resourceId, availabilityModel, slotConfig, holdConfig }: UseBookingFlowOptions) {
  const allowedDurations = useMemo(() => {
    if (!slotConfig?.duration_options) return [];
    return (slotConfig.duration_options as string[]).map(parseDuration);
  }, [slotConfig]);
  const fixedSlots = useMemo(() => {
    if (!slotConfig?.fixed_slots) return [] as { start: string; end: string }[];
    return slotConfig.fixed_slots as { start: string; end: string }[];
  }, [slotConfig]);
  const hasFixedSlots = fixedSlots.length > 0;

  const [step, setStep] = useState<Step>("dates");
  const [startDate, setStartDate] = useState("");
  const [startTime, setStartTime] = useState(fixedSlots[0]?.start ?? "09:00");
  const [endDate, setEndDate] = useState("");
  const [endTime, setEndTime] = useState(fixedSlots[0]?.end ?? "17:00");
  const [notes, setNotes] = useState("");
  const [isPending, setIsPending] = useState(false);

  const [holdToken, setHoldToken] = useState("");
  const [holdPrice, setHoldPrice] = useState(0);
  const [checkPrice, setCheckPrice] = useState(0);
  const [countdown, setCountdown] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const showTime = availabilityModel === "hourly" || availabilityModel === "time_slot";
  const hideEndDate = availabilityModel === "time_slot";
  const holdEnabled = holdConfig != null;

  const clearTimer = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    setStep("dates");
    setStartDate("");
    setStartTime(fixedSlots[0]?.start ?? "09:00");
    setEndDate("");
    setEndTime(fixedSlots[0]?.end ?? "17:00");
    setNotes("");
    setIsPending(false);
    setHoldToken("");
    setHoldPrice(0);
    setCheckPrice(0);
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
      const next = new Date(`${endDate}T00:00:00`);
      next.setDate(next.getDate() + 1);
      return next.toISOString();
    }
    const ed = hideEndDate ? startDate : endDate;
    return buildDatetime(ed, endTime);
  }

  async function checkAvailability(): Promise<boolean> {
    if (!startDate) {
      toast.error("Please select a start date");
      return false;
    }
    if (!hideEndDate && !endDate) {
      toast.error("Please select an end date");
      return false;
    }

    // Client-side slot duration validation
    if (allowedDurations.length > 0 && showTime && startTime && endTime) {
      const start = new Date(`${startDate}T${startTime}`);
      const end = new Date(`${hideEndDate ? startDate : endDate}T${endTime}`);
      const durationMin = (end.getTime() - start.getTime()) / 60000;
      if (durationMin > 0 && !allowedDurations.some((a) => Math.abs(durationMin - a) < 1)) {
        const opts = slotConfig!.duration_options as string[];
        toast.error(
          `This resource is available in slots of ${opts.join(", ")}`
        );
        return false;
      }
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

      setCheckPrice(check.price ?? 0);
      setStep("available");
      return true;
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response: { data: { detail?: { validation_errors?: string[] } } } }).response
              ?.data?.detail?.validation_errors?.join(". ")
          : null;
      toast.error(msg ?? "Failed to check availability");
      return false;
    } finally {
      setIsPending(false);
    }
  }

  async function holdResource(): Promise<boolean> {
    setIsPending(true);
    try {
      const start = getStartDatetime();
      const end = getEndDatetime();

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
      toast.error("Failed to hold resource");
      return false;
    } finally {
      setIsPending(false);
    }
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
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
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

  async function directBook(): Promise<BookingResponse | null> {
    if (!startDate) {
      toast.error("Please select a start date");
      return null;
    }
    if (!hideEndDate && !endDate) {
      toast.error("Please select an end date");
      return null;
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
        return null;
      }

      const payload: BookingCreate = {
        resource_id: resourceId,
        start_time: start,
        end_time: end,
        notes: notes || undefined,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      };

      const { data: booking } = await api.post<BookingResponse>("/bookings", payload);
      toast.success("Booking confirmed!");
      setStep("booked");
      return booking;
    } catch {
      toast.error("Failed to book resource");
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
    setStep,
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
    holdEnabled,
    allowedDurations,
    fixedSlots,
    hasFixedSlots,
    checkPrice,
    holdPrice,
    countdown,
    countdownFormatted: formatCountdown(countdown),
    isPending,
    checkAvailability,
    holdResource,
    checkAndHold,
    confirmBooking,
    directBook,
    selectFixedSlot: (slot: { start: string; end: string }) => {
      setStartTime(slot.start);
      setEndTime(slot.end);
    },
    cancel,
    reset,
  };
}
