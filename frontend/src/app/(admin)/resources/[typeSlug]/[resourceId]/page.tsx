"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CalendarDays, Pencil, Trash2, MapPin, Star } from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";
import type { ResourceResponse, ResourceTypeResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CreateResourceSheet } from "@/components/resources/create-resource-sheet";
import { BookResourceSheet } from "@/components/bookings/book-resource-sheet";
import { toast } from "sonner";

export default function ResourceDetailPage() {
  const { typeSlug, resourceId } = useParams<{ typeSlug: string; resourceId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);
  const [bookOpen, setBookOpen] = useState(false);

  const { data: types } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types");
      return data;
    },
    staleTime: 30_000,
  });

  const currentType = types?.find((t) => t.slug === typeSlug);

  const { data: resource, isLoading } = useQuery({
    queryKey: ["resource", resourceId],
    queryFn: async () => {
      const { data } = await api.get<ResourceResponse>(`/resources/${resourceId}`);
      return data;
    },
    enabled: !!resourceId,
  });

  const statusMutation = useMutation({
    mutationFn: async (status: string) => {
      const { data } = await api.put<ResourceResponse>(`/resources/${resourceId}`, { status });
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["resource", resourceId] });
      queryClient.invalidateQueries({ queryKey: ["resources", currentType?.id] });
      toast.success(`Status changed to ${data.status}`);
    },
    onError: () => {
      toast.error("Failed to update status");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      await api.delete(`/resources/${resourceId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resources", currentType?.id] });
      toast.success("Resource deleted");
      router.push(`/resources/${typeSlug}`);
    },
    onError: () => {
      toast.error("Failed to delete resource");
    },
  });

  if (isLoading || !resource || !currentType) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Link
          href={`/resources/${typeSlug}`}
          className="rounded-md p-1 hover:bg-accent"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold tracking-tight">{resource.name}</h1>
          {resource.description && (
            <p className="mt-1 text-sm text-muted-foreground">
              {resource.description}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => setBookOpen(true)} disabled={resource.status !== "active"}>
            <CalendarDays className="mr-2 h-4 w-4" />
            Book
          </Button>
          <Button variant="outline" onClick={() => setEditOpen(true)}>
            <Pencil className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <Button
            variant="destructive"
            onClick={() => deleteMutation.mutate()}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-4 rounded-lg border p-6">
          <h2 className="text-sm font-semibold text-muted-foreground">Details</h2>

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

          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Price</span>
            <span className="font-medium">
              {resource.base_price.toFixed(2)} {resource.currency}
            </span>
          </div>

          {resource.rating_count > 0 && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Rating</span>
              <span className="flex items-center gap-1 font-medium">
                <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                {resource.rating_avg.toFixed(1)} ({resource.rating_count})
              </span>
            </div>
          )}

          {resource.location_address && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Location</span>
              <span className="flex items-center gap-1 text-sm">
                <MapPin className="h-4 w-4" />
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

        {resource.attributes && Object.keys(resource.attributes).length > 0 && (
          <div className="space-y-4 rounded-lg border p-6">
            <h2 className="text-sm font-semibold text-muted-foreground">Attributes</h2>
            {Object.entries(resource.attributes).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-sm capitalize text-muted-foreground">
                  {key.replace(/_/g, " ")}
                </span>
                <span className="text-sm font-medium">
                  {Array.isArray(value) ? (
                    <span className="flex flex-wrap gap-1 justify-end">
                      {value.map((tag) => (
                        <Badge key={tag} variant="muted" className="text-xs">
                          {String(tag)}
                        </Badge>
                      ))}
                    </span>
                  ) : typeof value === "boolean" ? (
                    value ? "Yes" : "No"
                  ) : (
                    String(value)
                  )}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <CreateResourceSheet
        open={editOpen}
        onClose={() => setEditOpen(false)}
        typeId={currentType.id}
        typeName={currentType.name}
        attributeSchema={currentType.attribute_schema}
        editingResource={resource}
      />

      <BookResourceSheet
        open={bookOpen}
        onClose={() => setBookOpen(false)}
        resourceId={resource.id}
        resourceName={resource.name}
        availabilityModel={currentType.availability_model}
      />
    </div>
  );
}
