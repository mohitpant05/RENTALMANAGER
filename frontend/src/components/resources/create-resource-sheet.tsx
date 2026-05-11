"use client";

import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
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
import { useAttachments } from "@/hooks/use-storage";
import type {
  AttributeField,
  ResourceCreate,
  ResourceResponse,
  ResourceUpdate,
} from "@/types/api";
import { CurrencySelect } from "@/components/ui/currency-select";
import { ResourcePreviewModal } from "@/components/resources/resource-preview-modal";
import { toast } from "sonner";

const resourceSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
  base_price: z.number().min(0, "Price must be non-negative"),
  currency: z.string().min(1),
  location_address: z.string().optional(),
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

interface CreateResourceSheetProps {
  open: boolean;
  onClose: () => void;
  typeId: string;
  typeName: string;
  attributeSchema: AttributeField[] | null;
  editingResource?: ResourceResponse | null;
}

export function CreateResourceSheet({
  open,
  onClose,
  typeId,
  typeName,
  attributeSchema,
  editingResource,
}: CreateResourceSheetProps) {
  const queryClient = useQueryClient();
  const isEditing = !!editingResource;
  const [attributes, setAttributes] = useState<Record<string, unknown>>({});
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [imagePreviews, setImagePreviews] = useState<string[]>([]);
  const [showPreview, setShowPreview] = useState(false);
  const [pendingFormData, setPendingFormData] = useState<ResourceForm | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const ph = getPlaceholders(typeName);

  const resourceId = editingResource?.id ?? "";
  const { data: existingAttachments } = useAttachments("resource", resourceId);

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
      currency: "USD",
      location_address: "",
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
      });
      setAttributes(editingResource.attributes ?? {});
    } else {
      reset({
        name: "",
        description: "",
        base_price: 0,
        currency: "USD",
        location_address: "",
      });
      setAttributes({});
      setImageFiles([]);
      setImagePreviews([]);
    }
  }, [editingResource, reset]);

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

  async function uploadImage(resourceId: string, file: File) {
    const { data: urlData } = await api.post<{ upload_url: string; attachment_id: string }>(
      "/storage/upload-url",
      {
        filename: file.name,
        content_type: file.type,
        entity_type: "resource",
        entity_id: resourceId,
      }
    );
    await fetch(urlData.upload_url, {
      method: "PUT",
      headers: { "Content-Type": file.type },
      body: file,
    });
    await api.post("/storage/confirm", { attachment_id: urlData.attachment_id });
  }

  const createMutation = useMutation({
    mutationFn: async (data: ResourceForm) => {
      const payload: Record<string, unknown> = {
        ...data,
        attributes: Object.keys(attributes).length > 0 ? attributes : undefined,
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
                      value={(getAttributeValue(attr) as number) ?? ""}
                      onChange={(e) =>
                        handleAttributeChange(
                          attr.name,
                          e.target.value ? parseFloat(e.target.value) : undefined
                        )
                      }
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

          <div className="space-y-2">
            <Label>Vehicle Images</Label>
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
                existingAttachments?.map((att) => (
                  <div
                    key={att.id}
                    className="relative h-20 w-20 overflow-hidden rounded-md border"
                  >
                    <img
                      src={att.url}
                      alt={att.filename}
                      className="h-full w-full object-cover"
                    />
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
        currency: pendingFormData?.currency ?? "USD",
        location_address: pendingFormData?.location_address,
        attributes,
        typeName,
        imagePreviews,
        existingImages: existingAttachments?.map((a) => a.url) ?? [],
      }}
    />
    </>
  );
}
