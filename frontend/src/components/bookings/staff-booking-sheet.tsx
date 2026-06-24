"use client";

import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, Check, X } from "lucide-react";
import api from "@/lib/api";
import type {
  CustomerLookupResponse,
  OnBehalfBookingResponse,
  ResourceResponse,
  ResourceTypeResponse,
} from "@/types/api";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

interface StaffBookingSheetProps {
  open: boolean;
  onClose: () => void;
}

export function StaffBookingSheet({ open, onClose }: StaffBookingSheetProps) {
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [isNewCustomer, setIsNewCustomer] = useState(false);
  const [foundCustomer, setFoundCustomer] = useState<CustomerLookupResponse | null>(null);
  const [lookupDone, setLookupDone] = useState(false);

  const [typeId, setTypeId] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (!open) {
      setEmail("");
      setCustomerName("");
      setCustomerPhone("");
      setIsNewCustomer(false);
      setFoundCustomer(null);
      setLookupDone(false);
      setTypeId("");
      setResourceId("");
      setStartTime("");
      setEndTime("");
      setNotes("");
    }
  }, [open]);

  useEffect(() => {
    if (!email || email.length < 3) {
      setFoundCustomer(null);
      setIsNewCustomer(false);
      setLookupDone(false);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const { data } = await api.get<CustomerLookupResponse>("/auth/users/lookup", {
          params: { email },
        });
        setFoundCustomer(data);
        setIsNewCustomer(false);
        setCustomerName(data.full_name);
        setCustomerPhone(data.phone ?? "");
      } catch {
        setFoundCustomer(null);
        setIsNewCustomer(true);
        setCustomerName("");
        setCustomerPhone("");
      }
      setLookupDone(true);
    }, 500);
    return () => clearTimeout(timer);
  }, [email]);

  const { data: types = [] } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types");
      return data;
    },
    enabled: open,
  });

  const { data: resources = [] } = useQuery({
    queryKey: ["resources-for-type", typeId],
    queryFn: async () => {
      const { data } = await api.get<ResourceResponse[]>("/resources", {
        params: { type_id: typeId, limit: 100 },
      });
      return data;
    },
    enabled: !!typeId,
  });

  const selectedType = types.find((t) => t.id === typeId);

  const createMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<OnBehalfBookingResponse>("/bookings/on-behalf", {
        customer_email: email,
        customer_name: isNewCustomer ? customerName : undefined,
        customer_phone: isNewCustomer && customerPhone ? customerPhone : undefined,
        resource_id: resourceId,
        start_time: startTime,
        end_time: endTime,
        notes: notes || undefined,
      });
      return data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["bookings"] });
      const msg = data.created_customer
        ? "Booking created — new customer account created"
        : "Booking created";
      toast.success(msg);
      onClose();
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to create booking";
      toast.error(detail);
    },
  });

  const canSubmit =
    email &&
    (foundCustomer || (isNewCustomer && customerName)) &&
    resourceId &&
    startTime &&
    endTime;

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-[480px] sm:max-w-[480px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Create Booking (On Behalf)</SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {/* Step 1: Customer */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold">Customer</h3>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="customer@example.com"
              />
            </div>
            {lookupDone && foundCustomer && (
              <div className="flex items-center gap-2 text-sm text-green-600">
                <Check className="h-4 w-4" />
                Found: {foundCustomer.full_name}
                {foundCustomer.phone && ` (${foundCustomer.phone})`}
              </div>
            )}
            {lookupDone && isNewCustomer && (
              <>
                <div className="flex items-center gap-2 text-sm text-orange-600">
                  <X className="h-4 w-4" />
                  No match — new customer will be created
                </div>
                <div className="space-y-2">
                  <Label htmlFor="name">Name *</Label>
                  <Input
                    id="name"
                    value={customerName}
                    onChange={(e) => setCustomerName(e.target.value)}
                    placeholder="Full name"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone">Phone</Label>
                  <Input
                    id="phone"
                    value={customerPhone}
                    onChange={(e) => setCustomerPhone(e.target.value)}
                    placeholder="+1234567890"
                  />
                </div>
              </>
            )}
          </div>

          {/* Step 2: Resource */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold">Resource</h3>
            <div className="space-y-2">
              <Label>Type</Label>
              <Select value={typeId} onValueChange={(v) => { setTypeId(v); setResourceId(""); }}>
                <SelectTrigger>
                  <SelectValue placeholder="Select type..." />
                </SelectTrigger>
                <SelectContent>
                  {types.map((t) => (
                    <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {typeId && (
              <div className="space-y-2">
                <Label>Resource</Label>
                <Select value={resourceId} onValueChange={setResourceId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select resource..." />
                  </SelectTrigger>
                  <SelectContent>
                    {resources.map((r) => (
                      <SelectItem key={r.id} value={r.id}>{r.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>

          {/* Step 3: Schedule */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold">Schedule</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Start</Label>
                <Input
                  type="datetime-local"
                  value={startTime}
                  onChange={(e) => setStartTime(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>End</Label>
                <Input
                  type="datetime-local"
                  value={endTime}
                  onChange={(e) => setEndTime(e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Optional notes..."
                rows={2}
              />
            </div>
            {selectedType && (
              <p className="text-xs text-muted-foreground">
                Auto-confirm: {selectedType.staff_booking_auto_confirm ? "Yes" : "No"} (per resource type setting)
              </p>
            )}
          </div>

          <Button
            className="w-full"
            onClick={() => createMutation.mutate()}
            disabled={!canSubmit || createMutation.isPending}
          >
            {createMutation.isPending ? (
              <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Creating...</>
            ) : (
              "Create Booking"
            )}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
