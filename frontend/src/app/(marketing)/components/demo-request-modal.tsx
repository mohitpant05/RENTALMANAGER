"use client";

import { useState, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  useAvailableSlots,
  useSubmitDemoRequest,
  type DemoSlot,
} from "@/hooks/use-demo-requests";

function groupSlotsByDate(slots: DemoSlot[]) {
  const grouped: Record<string, DemoSlot[]> = {};
  for (const slot of slots) {
    const date = new Date(slot.start).toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
    if (!grouped[date]) grouped[date] = [];
    grouped[date].push(slot);
  }
  return grouped;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

export function DemoRequestModal({
  trigger,
}: {
  trigger: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<"form" | "slots" | "done">("form");
  const [form, setForm] = useState({
    name: "",
    email: "",
    company: "",
    message: "",
  });
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: slots, isLoading: slotsLoading } = useAvailableSlots();
  const submit = useSubmitDemoRequest();

  const grouped = useMemo(
    () => (slots ? groupSlotsByDate(slots) : {}),
    [slots]
  );
  const dateKeys = Object.keys(grouped);

  function handleNext() {
    if (!form.name.trim() || !form.email.trim()) {
      setError("Name and email are required");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      setError("Enter a valid email");
      return;
    }
    setError(null);
    setStep("slots");
    if (dateKeys.length > 0 && !selectedDate) {
      setSelectedDate(dateKeys[0]);
    }
  }

  async function handleSubmit() {
    if (!selectedSlot) {
      setError("Pick a time slot");
      return;
    }
    setError(null);
    try {
      await submit.mutateAsync({
        name: form.name.trim(),
        email: form.email.trim().toLowerCase(),
        company: form.company.trim() || undefined,
        message: form.message.trim() || undefined,
        slot_start: selectedSlot,
      });
      setStep("done");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Something went wrong. Try again.";
      setError(msg);
    }
  }

  function handleClose() {
    setOpen(false);
    setTimeout(() => {
      setStep("form");
      setForm({ name: "", email: "", company: "", message: "" });
      setSelectedSlot(null);
      setSelectedDate(null);
      setError(null);
    }, 200);
  }

  return (
    <>
      <span onClick={() => setOpen(true)}>{trigger}</span>
      <Dialog open={open} onOpenChange={(v) => (v ? setOpen(true) : handleClose())}>
      <DialogContent className="max-w-lg">
        {step === "form" && (
          <>
            <DialogHeader>
              <DialogTitle>Book a Demo</DialogTitle>
              <DialogDescription>
                Tell us about yourself and we&apos;ll schedule a 30-minute walkthrough.
              </DialogDescription>
            </DialogHeader>
            <div className="mt-4 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="demo-name">Name *</Label>
                <Input
                  id="demo-name"
                  value={form.name}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, name: e.target.value }))
                  }
                  placeholder="Your full name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="demo-email">Email *</Label>
                <Input
                  id="demo-email"
                  type="email"
                  value={form.email}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, email: e.target.value }))
                  }
                  placeholder="you@company.com"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="demo-company">Company</Label>
                <Input
                  id="demo-company"
                  value={form.company}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, company: e.target.value }))
                  }
                  placeholder="Your company name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="demo-message">Message</Label>
                <Textarea
                  id="demo-message"
                  value={form.message}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, message: e.target.value }))
                  }
                  placeholder="What are you looking to manage?"
                  rows={3}
                />
              </div>
              {error && (
                <p className="text-sm text-destructive">{error}</p>
              )}
              <Button onClick={handleNext} className="w-full">
                Choose a Time Slot
              </Button>
            </div>
          </>
        )}

        {step === "slots" && (
          <>
            <DialogHeader>
              <DialogTitle>Pick a Slot</DialogTitle>
              <DialogDescription>
                30-minute sessions, Mon–Fri, 9 AM – 5 PM UTC
              </DialogDescription>
            </DialogHeader>
            <div className="mt-4">
              {slotsLoading ? (
                <div className="flex justify-center py-8">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                </div>
              ) : dateKeys.length === 0 ? (
                <p className="py-8 text-center text-muted-foreground">
                  No slots available right now. Try again later.
                </p>
              ) : (
                <>
                  <div className="mb-4 flex gap-2 overflow-x-auto pb-2">
                    {dateKeys.map((date) => (
                      <button
                        key={date}
                        onClick={() => {
                          setSelectedDate(date);
                          setSelectedSlot(null);
                        }}
                        className={`shrink-0 rounded-md border px-3 py-1.5 text-sm transition-colors ${
                          selectedDate === date
                            ? "border-primary bg-primary text-primary-foreground"
                            : "border-border hover:bg-accent"
                        }`}
                      >
                        {date}
                      </button>
                    ))}
                  </div>
                  {selectedDate && grouped[selectedDate] && (
                    <div className="grid max-h-48 grid-cols-3 gap-2 overflow-y-auto">
                      {grouped[selectedDate].map((slot) => (
                        <button
                          key={slot.start}
                          onClick={() => setSelectedSlot(slot.start)}
                          className={`rounded-md border px-2 py-1.5 text-sm transition-colors ${
                            selectedSlot === slot.start
                              ? "border-primary bg-primary text-primary-foreground"
                              : "border-border hover:bg-accent"
                          }`}
                        >
                          {formatTime(slot.start)}
                        </button>
                      ))}
                    </div>
                  )}
                </>
              )}
              {error && (
                <p className="mt-3 text-sm text-destructive">{error}</p>
              )}
              <div className="mt-4 flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setStep("form");
                    setError(null);
                  }}
                  className="flex-1"
                >
                  Back
                </Button>
                <Button
                  onClick={handleSubmit}
                  disabled={!selectedSlot || submit.isPending}
                  className="flex-1"
                >
                  {submit.isPending ? "Booking…" : "Confirm Booking"}
                </Button>
              </div>
            </div>
          </>
        )}

        {step === "done" && (
          <>
            <DialogHeader>
              <DialogTitle>Demo Booked!</DialogTitle>
              <DialogDescription>
                We&apos;ll send a confirmation to {form.email}
              </DialogDescription>
            </DialogHeader>
            <div className="mt-4 space-y-4 text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                <svg className="h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-muted-foreground">
                {selectedSlot &&
                  new Date(selectedSlot).toLocaleString("en-US", {
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                    hour: "numeric",
                    minute: "2-digit",
                    hour12: true,
                  })}{" "}
                UTC
              </p>
              <Button onClick={handleClose} className="w-full">
                Done
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
    </>
  );
}
