"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, X, Ban, AlertTriangle } from "lucide-react";
import api from "@/lib/api";
import type { BookingResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from "@/components/ui/sheet";
import { toast } from "sonner";

const VALID_TRANSITIONS: Record<string, string[]> = {
  pending: ["confirmed", "rejected", "cancelled"],
  confirmed: ["cancelled"],
  active: ["cancelled", "no_show"],
};

const ACTION_MAP: Record<string, string> = {
  confirmed: "confirm",
  rejected: "reject",
  cancelled: "cancel",
  no_show: "no-show",
};

interface BookingActionsProps {
  booking: BookingResponse;
}

export function BookingActions({ booking }: BookingActionsProps) {
  const queryClient = useQueryClient();
  const [reasonSheetAction, setReasonSheetAction] = useState<string | null>(null);
  const [reason, setReason] = useState("");

  const transitions = VALID_TRANSITIONS[booking.status];

  const actionMutation = useMutation({
    mutationFn: async ({
      action,
      body,
    }: {
      action: string;
      body?: Record<string, unknown>;
    }) => {
      const { data } = await api.post(`/bookings/${booking.id}/${action}`, body);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["booking", booking.id] });
      queryClient.invalidateQueries({ queryKey: ["bookings"] });
      toast.success("Booking updated successfully");
      closeReasonSheet();
    },
    onError: () => {
      toast.error("Failed to update booking");
    },
  });

  function closeReasonSheet() {
    setReasonSheetAction(null);
    setReason("");
  }

  function handleAction(targetStatus: string) {
    const action = ACTION_MAP[targetStatus];
    if (targetStatus === "rejected" || targetStatus === "cancelled") {
      setReasonSheetAction(action);
    } else {
      actionMutation.mutate({ action });
    }
  }

  function handleReasonSubmit() {
    if (!reasonSheetAction) return;
    actionMutation.mutate({
      action: reasonSheetAction,
      body: reason.trim() ? { reason: reason.trim() } : undefined,
    });
  }

  if (!transitions || transitions.length === 0) {
    return null;
  }

  const sheetLabel = reasonSheetAction === "reject" ? "Reject" : "Cancel";

  return (
    <>
      <div className="flex items-center gap-2">
        {transitions.includes("confirmed") && (
          <Button
            size="sm"
            onClick={() => handleAction("confirmed")}
            disabled={actionMutation.isPending}
          >
            <Check className="mr-1 h-3.5 w-3.5" />
            Confirm
          </Button>
        )}
        {transitions.includes("rejected") && (
          <Button
            size="sm"
            variant="destructive"
            onClick={() => handleAction("rejected")}
            disabled={actionMutation.isPending}
          >
            <X className="mr-1 h-3.5 w-3.5" />
            Reject
          </Button>
        )}
        {transitions.includes("cancelled") && (
          <Button
            size="sm"
            variant="destructive"
            onClick={() => handleAction("cancelled")}
            disabled={actionMutation.isPending}
          >
            <Ban className="mr-1 h-3.5 w-3.5" />
            Cancel
          </Button>
        )}
        {transitions.includes("no_show") && (
          <Button
            size="sm"
            variant="destructive"
            onClick={() => handleAction("no_show")}
            disabled={actionMutation.isPending}
          >
            <AlertTriangle className="mr-1 h-3.5 w-3.5" />
            No-Show
          </Button>
        )}
      </div>

      <Sheet open={!!reasonSheetAction} onOpenChange={(open) => { if (!open) closeReasonSheet(); }}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>{sheetLabel} Booking</SheetTitle>
            <SheetDescription>
              Provide an optional reason for {sheetLabel.toLowerCase()}ing this booking.
            </SheetDescription>
          </SheetHeader>
          <div className="px-4">
            <Label htmlFor="reason">Reason</Label>
            <Input
              id="reason"
              className="mt-1.5"
              placeholder="Optional reason..."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
          <SheetFooter>
            <Button
              variant="destructive"
              onClick={handleReasonSubmit}
              disabled={actionMutation.isPending}
            >
              {actionMutation.isPending ? `${sheetLabel}ing...` : sheetLabel}
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </>
  );
}
