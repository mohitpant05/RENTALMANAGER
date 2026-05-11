"use client";

import { MapPin, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface ResourcePreviewData {
  name: string;
  description?: string;
  base_price: number;
  currency: string;
  location_address?: string;
  attributes: Record<string, unknown>;
  typeName: string;
  imagePreviews: string[];
  existingImages: string[];
}

interface ResourcePreviewModalProps {
  data: ResourcePreviewData;
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isSaving: boolean;
}

export function ResourcePreviewModal({
  data,
  open,
  onClose,
  onConfirm,
  isSaving,
}: ResourcePreviewModalProps) {
  if (!open) return null;

  const allImages = [...data.existingImages, ...data.imagePreviews];

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-background">
      <div className="flex items-center justify-between border-b px-6 py-3">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">Preview — Public View</h2>
          <Badge variant="outline">Draft</Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={onClose} disabled={isSaving}>
            Back to Edit
          </Button>
          <Button onClick={onConfirm} disabled={isSaving}>
            {isSaving ? "Saving..." : "Save Resource"}
          </Button>
          <button
            onClick={onClose}
            className="ml-2 rounded-md p-1 hover:bg-muted"
            disabled={isSaving}
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-4 py-6">
          {allImages.length > 0 ? (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {allImages.map((src, i) => (
                <div
                  key={i}
                  className={`overflow-hidden rounded-lg ${i === 0 ? "sm:col-span-2 sm:row-span-2" : ""}`}
                >
                  <img
                    src={src}
                    alt={`${data.name} ${i + 1}`}
                    className="h-full w-full object-cover"
                    style={{ maxHeight: i === 0 ? 400 : 195 }}
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="flex h-48 items-center justify-center rounded-lg border-2 border-dashed text-muted-foreground">
              No images added
            </div>
          )}

          <div className="mt-6 grid gap-8 lg:grid-cols-[1fr_380px]">
            <div className="space-y-8">
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-bold sm:text-3xl">
                    {data.name || "Untitled Resource"}
                  </h1>
                  <Badge variant="secondary">{data.typeName}</Badge>
                </div>
              </div>

              {data.location_address && (
                <div className="flex items-start gap-2 text-sm text-muted-foreground">
                  <MapPin className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{data.location_address}</span>
                </div>
              )}

              {data.description && (
                <div>
                  <h2 className="mb-2 text-lg font-semibold">About</h2>
                  <p className="leading-relaxed text-muted-foreground">
                    {data.description}
                  </p>
                </div>
              )}

              {Object.keys(data.attributes).length > 0 && (
                <div>
                  <h2 className="mb-3 text-lg font-semibold">Details</h2>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                    {Object.entries(data.attributes).map(([key, val]) => {
                      if (val === undefined || val === null || val === "")
                        return null;
                      return (
                        <div key={key} className="rounded-lg border p-3">
                          <p className="text-xs capitalize text-muted-foreground">
                            {key.replace(/_/g, " ")}
                          </p>
                          <p className="mt-0.5 text-sm font-medium">
                            {Array.isArray(val)
                              ? val.join(", ")
                              : String(val)}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            <div>
              <div className="rounded-xl border p-6">
                <div className="mb-4">
                  <span className="text-2xl font-bold">
                    {data.currency} {data.base_price.toFixed(2)}
                  </span>
                </div>
                <div className="rounded-lg bg-muted/50 p-4 text-center text-sm text-muted-foreground">
                  Booking card will appear here for customers
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
