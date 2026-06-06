"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CalendarDays,
  ExternalLink,
  MapPin,
  Pencil,
  Star,
  Trash2,
} from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import api from "@/lib/api";
import { useAttachments } from "@/hooks/use-storage";
import type { ResourceResponse } from "@/types/api";
import { toast } from "sonner";

const STATUS_VARIANT: Record<
  string,
  "muted" | "success" | "warning" | "destructive"
> = {
  draft: "muted",
  active: "success",
  inactive: "warning",
  archived: "destructive",
};

interface ResourceDetailSheetProps {
  resource: ResourceResponse;
  typeSlug: string;
  typeName: string;
  open: boolean;
  onClose: () => void;
  onEdit: (resource: ResourceResponse) => void;
  onBook: (resource: ResourceResponse) => void;
}

export function ResourceDetailSheet({
  resource,
  typeSlug,
  typeName,
  open,
  onClose,
  onEdit,
  onBook,
}: ResourceDetailSheetProps) {
  const queryClient = useQueryClient();
  const { data: attachments } = useAttachments("resource", resource?.id ?? "");
  const images = attachments?.map((a) => a.download_url).filter((u): u is string => u !== null) ?? [];

  const statusMutation = useMutation({
    mutationFn: async (status: string) => {
      await api.put(`/resources/${resource.id}`, { status });
    },
    onSuccess: (_, status) => {
      queryClient.invalidateQueries({ queryKey: ["resource", resource.id] });
      queryClient.invalidateQueries({ queryKey: ["resources"] });
      toast.success(`Status changed to ${status}`);
    },
    onError: () => {
      toast.error("Failed to update status");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      await api.delete(`/resources/${resource.id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resources"] });
      toast.success("Resource deleted");
      onClose();
    },
    onError: () => {
      toast.error("Failed to delete resource");
    },
  });

  if (!resource) return null;

  const attributes = resource.attributes as Record<string, unknown> | null;

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="overflow-y-auto sm:max-w-lg">
        <SheetHeader className="px-6 pt-6">
          <SheetTitle>{resource.name}</SheetTitle>
        </SheetHeader>

        <div className="space-y-6 px-6 pb-6">
          {images.length > 0 && (
            <div className="flex gap-2 overflow-x-auto pb-2">
              {images.map((url, i) => (
                <div
                  key={i}
                  className="h-32 w-48 shrink-0 overflow-hidden rounded-lg border"
                >
                  <img
                    src={url}
                    alt={`${resource.name} ${i + 1}`}
                    className="h-full w-full object-cover"
                  />
                </div>
              ))}
            </div>
          )}

          <div className="flex items-center justify-between">
            <Badge variant={STATUS_VARIANT[resource.status] ?? "muted"}>
              {resource.status}
            </Badge>
            <Badge variant="secondary">{typeName}</Badge>
          </div>

          {resource.description && (
            <div>
              <h3 className="mb-1 text-sm font-medium text-muted-foreground">Description</h3>
              <p className="text-sm leading-relaxed">{resource.description}</p>
            </div>
          )}

          <div className="space-y-3 rounded-lg border p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Price</span>
              <span className="font-medium">
                {resource.base_price.toFixed(2)} {resource.currency}
              </span>
            </div>

            {resource.rating_count > 0 && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Rating</span>
                <span className="flex items-center gap-1 text-sm font-medium">
                  <Star className="h-3.5 w-3.5 fill-yellow-400 text-yellow-400" />
                  {resource.rating_avg.toFixed(1)} ({resource.rating_count})
                </span>
              </div>
            )}

            {resource.location_address && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Location</span>
                <span className="flex items-center gap-1 text-sm">
                  <MapPin className="h-3.5 w-3.5" />
                  {resource.location_address}
                </span>
              </div>
            )}

            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Created</span>
              <span className="text-sm">
                {new Date(resource.created_at).toLocaleDateString()}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Version</span>
              <span className="text-sm">{resource.version}</span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Status</span>
            <Select
              value={resource.status}
              onValueChange={(v) => statusMutation.mutate(v)}
            >
              <SelectTrigger className="w-[140px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="archived">Archived</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {attributes && Object.keys(attributes).length > 0 && (
            <>
              <Separator />
              <div>
                <h3 className="mb-3 text-sm font-medium text-muted-foreground">Attributes</h3>
                <div className="space-y-2">
                  {Object.entries(attributes).map(([key, val]) => (
                    <div key={key} className="flex items-center justify-between">
                      <span className="text-sm capitalize text-muted-foreground">
                        {key.replace(/_/g, " ")}
                      </span>
                      <span className="text-sm font-medium">
                        {Array.isArray(val) ? val.join(", ") : String(val)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          <Separator />

          <div className="flex flex-col gap-2">
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => onEdit(resource)}
              >
                <Pencil className="mr-2 h-4 w-4" />
                Edit
              </Button>
              <Button
                variant="outline"
                className="flex-1"
                disabled={resource.status !== "active"}
                onClick={() => onBook(resource)}
              >
                <CalendarDays className="mr-2 h-4 w-4" />
                Book
              </Button>
            </div>
            <div className="flex gap-2">
              <a
                href={`/resources/${resource.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex flex-1 items-center justify-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground shadow-sm hover:bg-accent hover:text-accent-foreground transition-colors"
              >
                <ExternalLink className="h-4 w-4" />
                View Public
              </a>
              <Button
                variant="destructive"
                className="flex-1"
                onClick={() => {
                  if (window.confirm(`Delete "${resource.name}"?`)) {
                    deleteMutation.mutate();
                  }
                }}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Delete
              </Button>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
