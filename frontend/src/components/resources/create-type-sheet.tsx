"use client";

import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import api from "@/lib/api";
import type { ResourceTypeCreate, ResourceTypeResponse, ResourceTypeUpdate } from "@/types/api";
import { toast } from "sonner";

const typeSchema = z.object({
  name: z.string().min(1, "Name is required"),
  slug: z
    .string()
    .min(1, "Slug is required")
    .regex(/^[a-z0-9-]+$/, "Lowercase letters, numbers, and hyphens only"),
  description: z.string().optional(),
  availability_model: z.enum(["date_range", "time_slot", "hourly"]),
  pricing_model: z.enum([
    "fixed_per_day",
    "fixed_per_slot",
    "per_hour",
    "tiered",
  ]),
});

interface CreateTypeSheetProps {
  open: boolean;
  onClose: () => void;
  editingType?: ResourceTypeResponse | null;
}

export function CreateTypeSheet({ open, onClose, editingType }: CreateTypeSheetProps) {
  const isEditing = !!editingType;
  const router = useRouter();
  const queryClient = useQueryClient();
  const [formRole, setFormRole] = useState("standalone");
  const [formRadius, setFormRadius] = useState("");
  const [formDisplayOrder, setFormDisplayOrder] = useState("0");
  const [holdEnabled, setHoldEnabled] = useState(false);
  const [holdUnit, setHoldUnit] = useState<"seconds" | "minutes">("minutes");
  const [holdValue, setHoldValue] = useState("10");
  const [bookingMode, setBookingMode] = useState<"individual" | "bundled" | "both">("both");
  const [opHoursEnabled, setOpHoursEnabled] = useState(false);
  const [opHoursStart, setOpHoursStart] = useState("09:00");
  const [opHoursEnd, setOpHoursEnd] = useState("18:00");
  const [bufferMinutes, setBufferMinutes] = useState("0");
  const [fixedSlots, setFixedSlots] = useState<{ start: string; end: string }[]>([]);
  const [newSlotStart, setNewSlotStart] = useState("09:00");
  const [newSlotEnd, setNewSlotEnd] = useState("11:00");
  const [durationOptions, setDurationOptions] = useState<string[]>([]);
  const [newDuration, setNewDuration] = useState("");
  const [deletePassword, setDeletePassword] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(typeSchema),
    defaultValues: {
      name: "",
      slug: "",
      description: "",
      availability_model: "date_range",
      pricing_model: "fixed_per_day",
    },
  });

  useEffect(() => {
    if (editingType) {
      reset({
        name: editingType.name,
        slug: editingType.slug,
        description: editingType.description ?? "",
        availability_model: editingType.availability_model as "date_range" | "time_slot" | "hourly",
        pricing_model: editingType.pricing_model as "fixed_per_day" | "fixed_per_slot" | "per_hour" | "tiered",
      });
      setFormRole(editingType.role ?? "standalone");
      setFormRadius(editingType.discovery_radius_km?.toString() ?? "");
      setFormDisplayOrder(editingType.display_order?.toString() ?? "0");
      if (editingType.hold_config) {
        setHoldEnabled(true);
        setHoldUnit(editingType.hold_config.unit);
        setHoldValue(editingType.hold_config.value.toString());
      } else {
        setHoldEnabled(false);
        setHoldUnit("minutes");
        setHoldValue("10");
      }
      setBookingMode((editingType.booking_mode as "individual" | "bundled" | "both") ?? "both");
      if (editingType.operating_hours) {
        setOpHoursEnabled(true);
        setOpHoursStart(editingType.operating_hours.start);
        setOpHoursEnd(editingType.operating_hours.end);
      } else {
        setOpHoursEnabled(false);
        setOpHoursStart("09:00");
        setOpHoursEnd("18:00");
      }
      setBufferMinutes(editingType.buffer_minutes?.toString() ?? "0");
      const sc = editingType.slot_config as Record<string, unknown> | null;
      setFixedSlots((sc?.fixed_slots as { start: string; end: string }[]) ?? []);
      setDurationOptions((sc?.duration_options as string[]) ?? []);
      setShowDeleteConfirm(false);
      setDeletePassword("");
    } else {
      reset({
        name: "",
        slug: "",
        description: "",
        availability_model: "date_range",
        pricing_model: "fixed_per_day",
      });
      setFormRole("standalone");
      setFormRadius("");
      setFormDisplayOrder("0");
      setHoldEnabled(false);
      setHoldUnit("minutes");
      setHoldValue("10");
      setBookingMode("both");
      setOpHoursEnabled(false);
      setOpHoursStart("09:00");
      setOpHoursEnd("18:00");
      setBufferMinutes("0");
      setFixedSlots([]);
      setDurationOptions([]);
      setShowDeleteConfirm(false);
      setDeletePassword("");
    }
  }, [editingType, reset]);

  const nameValue = watch("name");
  const availModel = watch("availability_model");

  function handleNameChange(e: React.ChangeEvent<HTMLInputElement>) {
    const name = e.target.value;
    setValue("name", name);
    setValue(
      "slug",
      name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/(^-|-$)/g, "")
    );
  }

  const mutation = useMutation({
    mutationFn: async (formData: { name: string; slug: string; availability_model: string; pricing_model: string; description?: string }) => {
      const role = formRole as "primary" | "addon" | "standalone" | "hidden";
      const display_order = Number(formDisplayOrder) || 0;
      const discovery_radius_km = formRadius && formRadius !== "" ? Number(formRadius) : null;
      const hold_config = holdEnabled ? { unit: holdUnit, value: Number(holdValue) || 10 } : null;
      const operating_hours = opHoursEnabled ? { start: opHoursStart, end: opHoursEnd } : null;
      const buffer_mins = Number(bufferMinutes) || 0;
      let slot_config: Record<string, unknown> | null = null;
      if (formData.availability_model === "time_slot") {
        slot_config = {};
        if (fixedSlots.length > 0) slot_config.fixed_slots = fixedSlots;
        if (durationOptions.length > 0) slot_config.duration_options = durationOptions;
        if (Object.keys(slot_config).length === 0) slot_config = null;
      }
      const payload = { name: formData.name, slug: formData.slug, role, availability_model: formData.availability_model, pricing_model: formData.pricing_model, display_order, discovery_radius_km, description: formData.description, hold_config, booking_mode: bookingMode, operating_hours, buffer_minutes: buffer_mins, slot_config };
      if (isEditing) {
        const { data: res } = await api.put<ResourceTypeResponse>(
          `/resource-types/${editingType.id}`,
          payload,
        );
        return res;
      }
      const { data: res } = await api.post<ResourceTypeResponse>(
        "/resource-types",
        payload,
      );
      return res;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["resource-types"] });
      toast.success(isEditing ? `${data.name} updated` : `${data.name} created`);
      onClose();
      router.push(`/admin/resources/${data.slug}`);
    },
    onError: () => {
      toast.error(isEditing ? "Failed to update" : "Failed to create resource type");
    },
  });

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{isEditing ? "Edit Type" : "Create Custom Type"}</SheetTitle>
          <SheetDescription>
            {isEditing ? "Update this resource type's configuration" : "Define a new resource category for your business"}
          </SheetDescription>
        </SheetHeader>

        <form
          onSubmit={handleSubmit((d) => mutation.mutate(d))}
          className="mt-6 space-y-4 px-6"
        >
          <div className="space-y-2">
            <Label htmlFor="type-name">Name</Label>
            <Input
              id="type-name"
              placeholder="e.g. Meeting Rooms"
              value={nameValue}
              onChange={handleNameChange}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="type-slug">Slug</Label>
            <Input id="type-slug" {...register("slug")} />
            {errors.slug && (
              <p className="text-sm text-destructive">{errors.slug.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="type-description">Description</Label>
            <Input
              id="type-description"
              placeholder="Brief description"
              {...register("description")}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="availability_model">Availability Model</Label>
            <select
              id="availability_model"
              {...register("availability_model")}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="date_range">Date Range (per day)</option>
              <option value="time_slot">Time Slot (fixed slots)</option>
              <option value="hourly">Hourly</option>
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="pricing_model">Pricing Model</Label>
            <select
              id="pricing_model"
              {...register("pricing_model")}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="fixed_per_day">Fixed per Day</option>
              <option value="fixed_per_slot">Fixed per Slot</option>
              <option value="per_hour">Per Hour</option>
              <option value="tiered">Tiered</option>
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="type-role">Role</Label>
            <select
              id="type-role"
              value={formRole}
              onChange={(e) => setFormRole(e.target.value)}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
            >
              <option value="standalone">Standalone</option>
              <option value="primary">Primary Venue</option>
              <option value="addon">Addon Service</option>
              <option value="hidden">Hidden</option>
            </select>
            <p className="text-xs text-muted-foreground">
              Primary venues show addon discovery. Addon services can be bundled with primary venues. Hidden types are excluded from public pages.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="type-radius">Discovery Radius (km)</Label>
            <Input
              id="type-radius"
              type="number"
              min="0"
              max="50000"
              step="0.1"
              placeholder="e.g. 50"
              value={formRadius}
              onChange={(e) => {
                const v = parseFloat(e.target.value);
                if (e.target.value === "" || (v >= 0 && v <= 50000)) setFormRadius(e.target.value);
              }}
              onKeyDown={(e) => { if (e.key === "-") e.preventDefault(); }}
            />
            <p className="text-xs text-muted-foreground">
              Only applies when role is "addon". Limits how far from a venue this service can be discovered.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="type-display-order">Display Order</Label>
            <Input
              id="type-display-order"
              type="number"
              min="0"
              max="1000000"
              step="1"
              placeholder="0"
              value={formDisplayOrder}
              onChange={(e) => {
                const v = parseInt(e.target.value, 10);
                if (e.target.value === "" || (v >= 0 && v <= 1_000_000)) setFormDisplayOrder(e.target.value);
              }}
              onKeyDown={(e) => { if (e.key === "-") e.preventDefault(); }}
            />
            <p className="text-xs text-muted-foreground">
              Lower values appear first in filters and listings.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="type-booking-mode">Booking Mode</Label>
            <select
              id="type-booking-mode"
              value={bookingMode}
              onChange={(e) => setBookingMode(e.target.value as "individual" | "bundled" | "both")}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="individual">Individual Only</option>
              <option value="bundled">Bundled Only</option>
              <option value="both">Both (Individual + Bundled)</option>
            </select>
            <p className="text-xs text-muted-foreground">
              Individual: single resource per booking. Bundled: primary + addons together. Both: allows either.
            </p>
          </div>

          <div className="space-y-2 rounded-lg border p-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="hold-enabled"
                className="h-4 w-4 rounded border-input"
                checked={holdEnabled}
                onChange={(e) => setHoldEnabled(e.target.checked)}
              />
              <Label htmlFor="hold-enabled" className="text-sm font-medium">Enable Hold Before Booking</Label>
            </div>
            <p className="text-xs text-muted-foreground">
              When enabled, customers must hold a resource before confirming. When disabled, bookings are instant with real-time availability check.
            </p>
            {holdEnabled && (
              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="space-y-1">
                  <Label className="text-xs">Unit</Label>
                  <select
                    value={holdUnit}
                    onChange={(e) => setHoldUnit(e.target.value as "seconds" | "minutes")}
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  >
                    <option value="minutes">Minutes</option>
                    <option value="seconds">Seconds</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Duration</Label>
                  <Input
                    type="number"
                    min="1"
                    max={holdUnit === "minutes" ? 60 : 3600}
                    step="1"
                    value={holdValue}
                    onKeyDown={(e) => { if (e.key === "-") e.preventDefault(); }}
                    onChange={(e) => {
                      const max = holdUnit === "minutes" ? 60 : 3600;
                      const v = parseInt(e.target.value, 10);
                      if (e.target.value === "" || (v >= 1 && v <= max)) setHoldValue(e.target.value);
                    }}
                  />
                </div>
              </div>
            )}
          </div>

          <div className="space-y-2 rounded-lg border p-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="op-hours-enabled"
                className="h-4 w-4 rounded border-input"
                checked={opHoursEnabled}
                onChange={(e) => setOpHoursEnabled(e.target.checked)}
              />
              <Label htmlFor="op-hours-enabled" className="text-sm font-medium">Operating Hours</Label>
            </div>
            <p className="text-xs text-muted-foreground">
              Set service hours. Resources of this type can only be booked within these hours.
            </p>
            {opHoursEnabled && (
              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="space-y-1">
                  <Label className="text-xs">Start Time</Label>
                  <Input type="time" value={opHoursStart} onChange={(e) => setOpHoursStart(e.target.value)} />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">End Time</Label>
                  <Input type="time" value={opHoursEnd} onChange={(e) => setOpHoursEnd(e.target.value)} />
                </div>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="buffer-minutes">Buffer Time (minutes)</Label>
            <Input
              id="buffer-minutes"
              type="number"
              min="0"
              max="120"
              step="1"
              value={bufferMinutes}
              onChange={(e) => {
                const v = parseInt(e.target.value, 10);
                if (e.target.value === "" || (v >= 0 && v <= 120)) setBufferMinutes(e.target.value);
              }}
              onKeyDown={(e) => { if (e.key === "-") e.preventDefault(); }}
            />
            <p className="text-xs text-muted-foreground">
              Gap after each booking before next one can start. E.g. 30 min buffer means a 9-1pm booking blocks until 1:30pm.
            </p>
          </div>

          {availModel === "time_slot" && (
            <div className="space-y-4 rounded-lg border p-4">
              <p className="text-sm font-medium">Time Slot Configuration</p>
              <p className="text-xs text-muted-foreground">
                Define fixed time slots customers can book. If none are set, customers choose any time within operating hours.
              </p>

              <div className="space-y-2">
                <Label className="text-xs font-medium">Fixed Time Slots</Label>
                {fixedSlots.map((slot, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="text-sm font-mono flex-1">{slot.start} – {slot.end}</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-7 px-2 text-destructive"
                      onClick={() => setFixedSlots(fixedSlots.filter((_, j) => j !== i))}
                    >
                      Remove
                    </Button>
                  </div>
                ))}
                <div className="flex items-end gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs">Start</Label>
                    <Input type="time" value={newSlotStart} onChange={(e) => setNewSlotStart(e.target.value)} className="w-28" />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">End</Label>
                    <Input type="time" value={newSlotEnd} onChange={(e) => setNewSlotEnd(e.target.value)} className="w-28" />
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      if (newSlotStart && newSlotEnd && newSlotStart < newSlotEnd) {
                        const exists = fixedSlots.some((s) => s.start === newSlotStart && s.end === newSlotEnd);
                        if (!exists) {
                          setFixedSlots([...fixedSlots, { start: newSlotStart, end: newSlotEnd }].sort((a, b) => a.start.localeCompare(b.start)));
                        }
                      }
                    }}
                  >
                    Add
                  </Button>
                </div>
              </div>

              {fixedSlots.length === 0 && (
                <div className="space-y-2">
                  <Label className="text-xs font-medium">Duration Options (fallback)</Label>
                  <div className="flex flex-wrap gap-1">
                    {durationOptions.map((d, i) => (
                      <span key={i} className="inline-flex items-center gap-1 rounded-full bg-secondary px-2.5 py-0.5 text-xs">
                        {d}
                        <button type="button" className="text-muted-foreground hover:text-foreground" onClick={() => setDurationOptions(durationOptions.filter((_, j) => j !== i))}>
                          &times;
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Input
                      placeholder="e.g. 2h or 30min"
                      value={newDuration}
                      onChange={(e) => setNewDuration(e.target.value)}
                      className="flex-1"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const d = newDuration.trim();
                        if (d && /^\d+(\.\d+)?\s*(h|min)$/.test(d) && !durationOptions.includes(d)) {
                          setDurationOptions([...durationOptions, d]);
                          setNewDuration("");
                        }
                      }}
                    >
                      Add
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    When no fixed slots are defined, constrain allowed booking durations (e.g. &quot;1h&quot;, &quot;2h&quot;, &quot;30min&quot;).
                  </p>
                </div>
              )}
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <Button type="submit" disabled={isSubmitting} className="flex-1">
              {isSubmitting ? "Saving..." : isEditing ? "Update Type" : "Create Type"}
            </Button>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
          </div>

          {isEditing && (
            <div className="border-t pt-4">
              {!showDeleteConfirm ? (
                <Button
                  type="button"
                  variant="destructive"
                  className="w-full"
                  onClick={() => setShowDeleteConfirm(true)}
                >
                  Delete Resource Type
                </Button>
              ) : (
                <div className="space-y-3 rounded-lg border border-destructive p-4">
                  <p className="text-sm font-medium text-destructive">Confirm deletion — enter your password</p>
                  <Input
                    type="password"
                    placeholder="Enter password"
                    value={deletePassword}
                    onChange={(e) => setDeletePassword(e.target.value)}
                  />
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="destructive"
                      disabled={!deletePassword || deleteLoading}
                      className="flex-1"
                      onClick={async () => {
                        setDeleteLoading(true);
                        try {
                          await api.post(`/resource-types/${editingType!.id}/delete`, { password: deletePassword });
                          queryClient.invalidateQueries({ queryKey: ["resource-types"] });
                          toast.success("Resource type deleted");
                          onClose();
                          router.push("/admin/resources");
                        } catch (err: unknown) {
                          const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Delete failed";
                          toast.error(msg);
                        } finally {
                          setDeleteLoading(false);
                        }
                      }}
                    >
                      {deleteLoading ? "Deleting..." : "Confirm Delete"}
                    </Button>
                    <Button type="button" variant="outline" onClick={() => { setShowDeleteConfirm(false); setDeletePassword(""); }}>
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </form>
      </SheetContent>
    </Sheet>
  );
}
