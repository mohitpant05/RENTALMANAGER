"use client";

import { useMemo } from "react";
import { Check, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { AddonSchedule } from "@/types/api";

function getDaysBetween(start: string, end: string): string[] {
  const days: string[] = [];
  const current = new Date(start + "T00:00:00");
  const last = new Date(end + "T00:00:00");
  while (current <= last) {
    const y = current.getFullYear();
    const m = String(current.getMonth() + 1).padStart(2, "0");
    const d = String(current.getDate()).padStart(2, "0");
    days.push(`${y}-${m}-${d}`);
    current.setDate(current.getDate() + 1);
  }
  return days;
}

function formatDayLabel(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function addDurationToTime(startTime: string, durationStr: string): string {
  const match = durationStr.match(/^(\d+(?:\.\d+)?)\s*(h|min)$/);
  if (!match) return "11:00";
  const [hour, min] = startTime.split(":").map(Number);
  const val = parseFloat(match[1]);
  const unit = match[2];
  const totalMinutes = hour * 60 + min + (unit === "h" ? val * 60 : val);
  const resultHour = Math.floor(totalMinutes / 60) % 24;
  const resultMin = totalMinutes % 60;
  return `${String(resultHour).padStart(2, "0")}:${String(resultMin).padStart(2, "0")}`;
}

interface AddonSchedulePickerProps {
  availabilityModel: string;
  slotConfig: Record<string, unknown> | null;
  startDate: string;
  endDate: string;
  basePrice: number;
  pricingModel: string;
  schedules: AddonSchedule[];
  onChange: (schedules: AddonSchedule[]) => void;
}

export function AddonSchedulePicker({
  availabilityModel,
  slotConfig,
  startDate,
  endDate,
  basePrice,
  pricingModel,
  schedules,
  onChange,
}: AddonSchedulePickerProps) {
  const days = useMemo(() => getDaysBetween(startDate, endDate), [startDate, endDate]);

  const selectedDates = useMemo(
    () => new Set(schedules.map((s) => s.date)),
    [schedules],
  );

  const getScheduleForDay = (date: string) => schedules.find((s) => s.date === date);

  function toggleDay(date: string) {
    if (selectedDates.has(date)) {
      onChange(schedules.filter((s) => s.date !== date));
    } else {
      if (availabilityModel === "time_slot") {
        const opts = (slotConfig?.duration_options as string[]) ?? ["2h"];
        onChange([...schedules, { date, start_time: "09:00", end_time: addDurationToTime("09:00", opts[0]) }]);
      } else {
        onChange([...schedules, { date }]);
      }
    }
  }

  function updateSlotTime(date: string, field: "start_time" | "end_time", value: string) {
    const existing = getScheduleForDay(date);
    if (existing) {
      onChange(
        schedules.map((s) => (s.date === date ? { ...s, [field]: value } : s)),
      );
    }
  }

  const totalPrice = useMemo(() => basePrice * schedules.length, [basePrice, schedules.length]);

  if (days.length === 0) return null;

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-muted-foreground">
        Select days{availabilityModel === "time_slot" ? " & time slots" : ""}
      </p>

      <div className="max-h-48 space-y-1 overflow-y-auto">
        {days.map((date) => {
          const slot = getScheduleForDay(date);
          const isSelected = !!slot;

          return (
            <div
              key={date}
              className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors ${
                isSelected ? "border-primary/50 bg-primary/5" : "border-transparent"
              }`}
            >
              <Button
                variant={isSelected ? "default" : "outline"}
                size="icon"
                className="h-5 w-5 shrink-0"
                onClick={() => toggleDay(date)}
                aria-label={isSelected ? "Remove day" : "Add day"}
              >
                {isSelected ? <Check className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
              </Button>
              <span
                className="min-w-28 flex-1 cursor-pointer text-xs font-normal"
                onClick={() => toggleDay(date)}
              >
                {formatDayLabel(date)}
              </span>

              {availabilityModel === "time_slot" && isSelected && (
                <div className="flex items-center gap-1.5">
                  <Input
                    type="time"
                    value={slot?.start_time ?? "09:00"}
                    onChange={(e) => updateSlotTime(date, "start_time", e.target.value)}
                    className="h-7 w-24 text-xs"
                  />
                  <span className="text-xs text-muted-foreground">to</span>
                  <Input
                    type="time"
                    value={slot?.end_time ?? "11:00"}
                    onChange={(e) => updateSlotTime(date, "end_time", e.target.value)}
                    className="h-7 w-24 text-xs"
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {schedules.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Subtotal: ₹{(totalPrice).toLocaleString()} ({schedules.length} day{schedules.length > 1 ? "s" : ""})
        </p>
      )}
    </div>
  );
}
