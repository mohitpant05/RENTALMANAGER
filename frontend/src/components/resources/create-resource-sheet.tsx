"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
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
import type {
  AttributeField,
  ResourceCreate,
  ResourceResponse,
  ResourceUpdate,
} from "@/types/api";
import { toast } from "sonner";

const resourceSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
  base_price: z.number().min(0, "Price must be non-negative"),
  currency: z.string().min(1),
  location_address: z.string().optional(),
});

type ResourceForm = z.infer<typeof resourceSchema>;

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

  const {
    register,
    handleSubmit,
    reset,
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
    }
  }, [editingResource, reset]);

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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resources", typeId] });
      queryClient.invalidateQueries({ queryKey: ["resource", editingResource?.id] });
      toast.success(isEditing ? "Resource updated" : "Resource created");
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
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
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
            createMutation.mutate(d as ResourceForm);
          })}
          className="mt-6 space-y-4"
        >
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" placeholder="e.g. Beach House" {...register("name")} />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              placeholder="Brief description"
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
              <Label htmlFor="currency">Currency</Label>
              <Input id="currency" {...register("currency")} />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="location_address">Location</Label>
            <Input
              id="location_address"
              placeholder="Address"
              {...register("location_address")}
            />
          </div>

          {attributeSchema && attributeSchema.length > 0 && (
            <div className="space-y-3 rounded-lg border p-4">
              <p className="text-sm font-medium text-muted-foreground">
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

          <div className="flex gap-3 pt-4">
            <Button type="submit" disabled={isSubmitting} className="flex-1">
              {isSubmitting
                ? "Saving..."
                : isEditing
                  ? "Update"
                  : "Create"}
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
