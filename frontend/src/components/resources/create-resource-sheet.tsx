"use client";

import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ImagePlus, X } from "lucide-react";
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
import { useAttachments, useUpload } from "@/hooks/use-storage";
import type {
  AttributeField,
  ResourceCreate,
  ResourceResponse,
  ResourceUpdate,
  TenantResponse,
} from "@/types/api";
import { CurrencySelect } from "@/components/ui/currency-select";
import { ResourcePreviewModal } from "@/components/resources/resource-preview-modal";
import { toast } from "sonner";

const resourceSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
  base_price: z.number().min(0, "Price must be non-negative").max(1_000_000, "Price cannot exceed 1,000,000"),
  currency: z.string().min(1),
  location_address: z.string().optional(),
  location_lat: z.number().min(-90).max(90).optional(),
  location_lng: z.number().min(-180).max(180).optional(),
});

type ResourceForm = z.infer<typeof resourceSchema>;

const PLACEHOLDERS: Record<string, { name: string; description: string; location: string }> = {
  Vehicles: {
    name: "e.g. Tata Harrier, Honda City, Royal Enfield 350",
    description: "Year, condition, mileage, special features...",
    location: "e.g. Koramangala, Bangalore",
  },
  Venues: {
    name: "e.g. Lakeside Banquet Hall, Rooftop Studio",
    description: "Capacity, ambience, available facilities...",
    location: "e.g. MG Road, Mumbai",
  },
  Cooks: {
    name: "e.g. Chef Ramesh, Anita's Kitchen",
    description: "Specialties, experience, cuisines offered...",
    location: "e.g. Indiranagar, Bangalore",
  },
};

function getPlaceholders(typeName: string) {
  const match = PLACEHOLDERS[typeName];
  if (match) return match;
  const singular = typeName.replace(/s$/, "").toLowerCase();
  return {
    name: `e.g. My ${singular} name`,
    description: `Describe this ${singular}...`,
    location: "Address or area",
  };
}

interface FixedSlot {
  start: string;
  end: string;
}

interface CreateResourceSheetProps {
  open: boolean;
  onClose: () => void;
  typeId: string;
  typeName: string;
  attributeSchema: AttributeField[] | null;
  editingResource?: ResourceResponse | null;
  availabilityModel?: string;
}

export function CreateResourceSheet({
  open,
  onClose,
  typeId,
  typeName,
  attributeSchema,
  editingResource,
  availabilityModel,
}: CreateResourceSheetProps) {
  const queryClient = useQueryClient();
  const { data: tenant } = useQuery({
    queryKey: ["admin-tenant"],
    queryFn: async () => {
      const { data } = await api.get<TenantResponse>("/admin/tenant");
      return data;
    },
  });
  const defaultCurrency = tenant?.base_currency ?? "USD";
  const isEditing = !!editingResource;
  const [attributes, setAttributes] = useState<Record<string, unknown>>({});
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [imagePreviews, setImagePreviews] = useState<string[]>([]);
  const [fixedSlots, setFixedSlots] = useState<FixedSlot[]>([]);
  const [newSlotStart, setNewSlotStart] = useState("09:00");
  const [newSlotEnd, setNewSlotEnd] = useState("10:00");
  const [durationOptions, setDurationOptions] = useState<string[]>([]);
  const [newDuration, setNewDuration] = useState("");
  const [showPreview, setShowPreview] = useState(false);
  const [pendingFormData, setPendingFormData] = useState<ResourceForm | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const ph = getPlaceholders(typeName);

  const resourceId = editingResource?.id ?? "";
  const { data: existingAttachments } = useAttachments("resource", resourceId);
  const { deleteAttachment, isDeleting } = useUpload("resource", resourceId);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ResourceForm>({
    resolver: zodResolver(resourceSchema),
    defaultValues: {
      name: "",
      description: "",
      base_price: 0,
      currency: defaultCurrency,
      location_address: "",
      location_lat: undefined,
      location_lng: undefined,
    },
  });

  useEffect(() => {
    if (editingResource) {
      reset({
        name: editingResource.name,
        description: editingResource.description ?? "",
        base_price: editingResource.base_price,
        currency: editingResource.currency,
        location_address: editingResource.location_address ?? "",
        location_lat: editingResource.location_lat ?? undefined,
        location_lng: editingResource.location_lng ?? undefined,
      });
      setAttributes(editingResource.attributes ?? {});
      const sc = editingResource.slot_config as Record<string, unknown> | null;
      if (sc) {
        setFixedSlots((sc.fixed_slots as FixedSlot[]) ?? []);
        setDurationOptions((sc.duration_options as string[]) ?? []);
      } else {
        setFixedSlots([]);
        setDurationOptions([]);
      }
    } else {
      reset({
        name: "",
        description: "",
        base_price: 0,
        currency: defaultCurrency,
        location_address: "",
        location_lat: undefined,
        location_lng: undefined,
      });
      setAttributes({});
      setFixedSlots([]);
      setDurationOptions([]);
      setImageFiles([]);
      setImagePreviews([]);
    }
  }, [editingResource, reset, defaultCurrency]);

  function handleImageSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    const valid = files.filter(
      (f) => f.type.startsWith("image/") && f.size <= 10 * 1024 * 1024
    );
    if (valid.length < files.length) {
      toast.error("Some files skipped (must be images under 10MB)");
    }
    setImageFiles((prev) => [...prev, ...valid]);
    const previews = valid.map((f) => URL.createObjectURL(f));
    setImagePreviews((prev) => [...prev, ...previews]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function removeImage(index: number) {
    URL.revokeObjectURL(imagePreviews[index]);
    setImageFiles((prev) => prev.filter((_, i) => i !== index));
    setImagePreviews((prev) => prev.filter((_, i) => i !== index));
  }

  function handleAttributeChange(name: string, value: unknown) {
    setAttributes((prev) => ({ ...prev, [name]: value }));
  }

  const [attrErrors, setAttrErrors] = useState<Record<string, string>>({});

  function validateAttributes(): boolean {
    if (!attributeSchema) return true;
    const errors: Record<string, string> = {};
    for (const attr of attributeSchema) {
      if (!attr.required) continue;
      const val = attributes[attr.name];
      if (val === undefined || val === null || val === "") {
        errors[attr.name] = `${attr.name.replace(/_/g, " ")} is required`;
      } else if (Array.isArray(val) && val.length === 0) {
        errors[attr.name] = `${attr.name.replace(/_/g, " ")} is required`;
      }
    }
    setAttrErrors(errors);
    return Object.keys(errors).length === 0;
  }

  // Upload image via the backend proxy — no direct S3/MinIO from the browser.
  // POST /storage/upload → Next.js rewrites to backend → internal put_object to MinIO.
  async function uploadImage(resourceId: string, file: File) {
    const form = new FormData();
    form.append("file", file);
    form.append("entity_type", "resource");
    form.append("entity_id", resourceId);
    await api.post("/storage/upload", form);
  }

  const createMutation = useMutation({
    mutationFn: async (data: ResourceForm) => {
      let slot_config: Record<string, unknown> | undefined = undefined;
      if (availabilityModel === "time_slot" && (fixedSlots.length > 0 || durationOptions.length > 0)) {
        slot_config = {};
        if (fixedSlots.length > 0) slot_config.fixed_slots = fixedSlots;
        if (durationOptions.length > 0) slot_config.duration_options = durationOptions;
      }
      const payload: Record<string, unknown> = {
        ...data,
        attributes: Object.keys(attributes).length > 0 ? attributes : undefined,
        slot_config: slot_config ?? null,
      };
      if (isEditing) {
        const { data: res } = await api.put<ResourceResponse>(
          `/resources/${editingResource.id}`,
          payload as ResourceUpdate
        );
        return res;
      }
      const { data: res } = await api.post<ResourceResponse>("/resources", {
        ...payload,
        type_id: typeId,
      } as ResourceCreate);
      return res;
    },
    onSuccess: async (resource) => {
      if (imageFiles.length > 0) {
        for (const file of imageFiles) {
          try {
            await uploadImage(resource.id, file);
          } catch {
            toast.error(`Failed to upload ${file.name}`);
          }
        }
      }
      queryClient.invalidateQueries({ queryKey: ["resources", typeId] });
      queryClient.invalidateQueries({ queryKey: ["resource", editingResource?.id] });
      queryClient.invalidateQueries({ queryKey: ["attachments", "resource", resource.id] });
      toast.success(isEditing ? "Resource updated" : "Resource created");
      setImageFiles([]);
      setImagePreviews([]);
      onClose();
    },
    onError: () => {
      toast.error(isEditing ? "Failed to update" : "Failed to create");
    },
  });

  function getAttributeValue(attr: AttributeField): unknown {
    return attributes[attr.name] ?? "";
  }

  return (
    <>
    <Sheet open={open && !showPreview} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="overflow-y-auto sm:max-w-md">
        <SheetHeader className="px-6 pt-6">
          <SheetTitle>
            {isEditing ? "Edit Resource" : `Add ${typeName}`}
          </SheetTitle>
          <SheetDescription>
            {isEditing
              ? "Update resource details"
              : `Create a new ${typeName.toLowerCase()} resource`}
          </SheetDescription>
        </SheetHeader>

        <form
          onSubmit={handleSubmit((d) => {
            if (!validateAttributes()) return;
            setPendingFormData(d);
            setShowPreview(true);
          })}
          className="space-y-5 px-6 pb-6"
        >
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" placeholder={ph.name} {...register("name")} />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <textarea
              id="description"
              placeholder={ph.description}
              rows={3}
              className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              {...register("description")}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="base_price">Base Price</Label>
              <Input
                id="base_price"
                type="number"
                step="0.01"
                min="0"
                max="1000000"
                onKeyDown={(e) => { if (e.key === "-") e.preventDefault(); }}
                {...register("base_price", { valueAsNumber: true })}
              />
              {errors.base_price && (
                <p className="text-sm text-destructive">
                  {errors.base_price.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label>Currency</Label>
              <CurrencySelect
                value={watch("currency")}
                onChange={(val) => setValue("currency", val)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="location_address">Location</Label>
            <Input
              id="location_address"
              placeholder={ph.location}
              {...register("location_address")}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="location_lat">Latitude</Label>
              <Input
                id="location_lat"
                type="number"
                step="any"
                placeholder="e.g. 12.9716"
                {...register("location_lat", { setValueAs: (v: string) => v === "" ? undefined : parseFloat(v) })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="location_lng">Longitude</Label>
              <Input
                id="location_lng"
                type="number"
                step="any"
                placeholder="e.g. 77.5946"
                {...register("location_lng", { setValueAs: (v: string) => v === "" ? undefined : parseFloat(v) })}
              />
            </div>
          </div>

          {attributeSchema && attributeSchema.length > 0 && (
            <div className="space-y-4 rounded-lg border p-5">
              <p className="text-sm font-medium">
                Custom Attributes
              </p>
              {attributeSchema.map((attr) => (
                <div key={attr.name} className="space-y-1">
                  <Label className="text-xs capitalize">
                    {attr.name.replace(/_/g, " ")}
                    {attr.required && (
                      <span className="text-destructive"> *</span>
                    )}
                  </Label>
                  {attr.type === "enum" && attr.options ? (
                    <select
                      className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      value={(getAttributeValue(attr) as string) ?? ""}
                      onChange={(e) =>
                        handleAttributeChange(attr.name, e.target.value)
                      }
                    >
                      <option value="">Select...</option>
                      {attr.options.map((opt) => (
                        <option key={opt} value={opt}>
                          {opt.replace(/_/g, " ")}
                        </option>
                      ))}
                    </select>
                  ) : attr.type === "boolean" ? (
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-input"
                      checked={(getAttributeValue(attr) as boolean) ?? false}
                      onChange={(e) =>
                        handleAttributeChange(attr.name, e.target.checked)
                      }
                    />
                  ) : attr.type === "number" ? (
                    <Input
                      type="number"
                      placeholder="0"
                      min="0"
                      max="1000000"
                      onKeyDown={(e) => { if (e.key === "-") e.preventDefault(); }}
                      value={(getAttributeValue(attr) as number) ?? ""}
                      onChange={(e) => {
                        const v = e.target.value ? Math.max(0, Math.min(1_000_000, parseFloat(e.target.value))) : undefined;
                        handleAttributeChange(attr.name, v);
                      }}
                    />
                  ) : attr.type === "tags" ? (
                    <Input
                      placeholder="tag1, tag2, tag3"
                      value={
                        Array.isArray(getAttributeValue(attr))
                          ? (getAttributeValue(attr) as string[]).join(", ")
                          : (getAttributeValue(attr) as string) ?? ""
                      }
                      onChange={(e) =>
                        handleAttributeChange(
                          attr.name,
                          e.target.value
                            .split(",")
                            .map((s) => s.trim())
                            .filter(Boolean)
                        )
                      }
                    />
                  ) : (
                    <Input
                      placeholder={attr.name.replace(/_/g, " ")}
                      value={(getAttributeValue(attr) as string) ?? ""}
                      onChange={(e) =>
                        handleAttributeChange(attr.name, e.target.value)
                      }
                    />
                  )}
                  {attrErrors[attr.name] && (
                    <p className="text-sm text-destructive">{attrErrors[attr.name]}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {availabilityModel === "time_slot" && (
            <div className="space-y-4 rounded-lg border p-5">
              <p className="text-sm font-medium">Time Slot Configuration</p>

              <div className="space-y-2">
                <Label className="text-xs">Fixed Slots</Label>
                <div className="flex gap-2 items-end">
                  <div className="space-y-1">
                    <span className="text-[10px] text-muted-foreground">Start</span>
                    <Input type="time" value={newSlotStart} onChange={(e) => setNewSlotStart(e.target.value)} className="w-28" />
                  </div>
                  <div className="space-y-1">
                    <span className="text-[10px] text-muted-foreground">End</span>
                    <Input type="time" value={newSlotEnd} onChange={(e) => setNewSlotEnd(e.target.value)} className="w-28" />
                  </div>
                  <Button type="button" variant="outline" size="sm" onClick={() => {
                    if (newSlotStart && newSlotEnd && newSlotStart < newSlotEnd) {
                      if (!fixedSlots.some((s) => s.start === newSlotStart && s.end === newSlotEnd)) {
                        setFixedSlots((prev) => [...prev, { start: newSlotStart, end: newSlotEnd }]);
                      }
                    }
                  }}>Add</Button>
                </div>
                {fixedSlots.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {fixedSlots.map((s, i) => (
                      <span key={i} className="inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-xs">
                        {s.start}–{s.end}
                        <button type="button" onClick={() => setFixedSlots((prev) => prev.filter((_, j) => j !== i))} className="hover:text-destructive">
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {fixedSlots.length === 0 && (
                <div className="space-y-2">
                  <Label className="text-xs">Duration Options (fallback)</Label>
                  <div className="flex gap-2">
                    <Input placeholder="e.g. 30m, 1h, 2h" value={newDuration} onChange={(e) => setNewDuration(e.target.value)} className="w-32" />
                    <Button type="button" variant="outline" size="sm" onClick={() => {
                      const d = newDuration.trim();
                      if (d && !durationOptions.includes(d)) {
                        setDurationOptions((prev) => [...prev, d]);
                        setNewDuration("");
                      }
                    }}>Add</Button>
                  </div>
                  {durationOptions.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {durationOptions.map((d, i) => (
                        <span key={i} className="inline-flex items-center gap-1 rounded-full bg-secondary px-2 py-0.5 text-xs">
                          {d}
                          <button type="button" onClick={() => setDurationOptions((prev) => prev.filter((_, j) => j !== i))} className="hover:text-destructive">
                            <X className="h-3 w-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="space-y-2">
            <Label>Images</Label>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={handleImageSelect}
            />

            <div className="flex flex-wrap gap-2">
              {isEditing &&
                existingAttachments?.filter((a) => a.download_url).map((att) => (
                  <div
                    key={att.id}
                    className="relative h-20 w-20 overflow-hidden rounded-md border"
                  >
                    <img
                      src={att.download_url!}
                      alt={att.file_name}
                      className="h-full w-full object-cover"
                    />
                    <button
                      type="button"
                      disabled={isDeleting}
                      onClick={() => {
                        if (window.confirm(`Remove "${att.file_name}"?`)) {
                          deleteAttachment(att.id);
                        }
                      }}
                      className="absolute right-0.5 top-0.5 rounded-full bg-background/80 p-0.5 hover:bg-destructive hover:text-destructive-foreground disabled:opacity-50"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}

              {imagePreviews.map((src, i) => (
                <div
                  key={i}
                  className="relative h-20 w-20 overflow-hidden rounded-md border"
                >
                  <img
                    src={src}
                    alt={`Preview ${i + 1}`}
                    className="h-full w-full object-cover"
                  />
                  <button
                    type="button"
                    onClick={() => removeImage(i)}
                    className="absolute right-0.5 top-0.5 rounded-full bg-background/80 p-0.5 hover:bg-destructive hover:text-destructive-foreground"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="flex h-20 w-20 flex-col items-center justify-center gap-1 rounded-md border border-dashed text-muted-foreground hover:border-primary hover:text-primary"
              >
                <ImagePlus className="h-5 w-5" />
                <span className="text-[10px]">Add</span>
              </button>
            </div>
          </div>

          <div className="flex gap-3 border-t pt-5">
            <Button type="submit" disabled={isSubmitting} className="flex-1">
              {isEditing ? "Preview Changes" : "Preview & Save"}
            </Button>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>

    <ResourcePreviewModal
      open={showPreview}
      onClose={() => setShowPreview(false)}
      onConfirm={() => {
        if (pendingFormData) {
          createMutation.mutate(pendingFormData);
          setShowPreview(false);
        }
      }}
      isSaving={createMutation.isPending}
      data={{
        name: pendingFormData?.name ?? "",
        description: pendingFormData?.description,
        base_price: pendingFormData?.base_price ?? 0,
        currency: pendingFormData?.currency ?? defaultCurrency,
        location_address: pendingFormData?.location_address,
        attributes,
        typeName,
        imagePreviews,
        existingImages: existingAttachments?.map((a) => a.download_url).filter((u): u is string => u !== null) ?? [],
      }}
    />
    </>
  );
}
