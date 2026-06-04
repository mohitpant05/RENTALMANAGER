"use client";

import { useEffect, useState } from "react";
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
    }
  }, [editingType, reset]);

  const nameValue = watch("name");

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
      if (isEditing) {
        const { data: res } = await api.put<ResourceTypeResponse>(
          `/resource-types/${editingType.id}`,
          { name: formData.name, slug: formData.slug, role, availability_model: formData.availability_model, pricing_model: formData.pricing_model, display_order, discovery_radius_km, description: formData.description }
        );
        return res;
      }
      const { data: res } = await api.post<ResourceTypeResponse>(
        "/resource-types",
        { name: formData.name, slug: formData.slug, role, availability_model: formData.availability_model, pricing_model: formData.pricing_model, display_order, discovery_radius_km, description: formData.description }
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
              disabled={isEditing}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
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
              disabled={isEditing}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
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
              step="0.1"
              placeholder="e.g. 50"
              value={formRadius}
              onChange={(e) => setFormRadius(e.target.value)}
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
              step="1"
              placeholder="0"
              value={formDisplayOrder}
              onChange={(e) => setFormDisplayOrder(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Lower values appear first in filters and listings.
            </p>
          </div>

          <div className="flex gap-3 pt-4">
            <Button type="submit" disabled={isSubmitting} className="flex-1">
              {isSubmitting ? "Saving..." : isEditing ? "Update Type" : "Create Type"}
            </Button>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
