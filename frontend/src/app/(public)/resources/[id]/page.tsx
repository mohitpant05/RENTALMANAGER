"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { MapPin } from "lucide-react";
import api from "@/lib/api";
import type { ResourceResponse, ResourceTypeResponse } from "@/types/api";
import { useAttachments } from "@/hooks/use-storage";
import { StarRating } from "@/components/reviews/star-rating";
import { ImageCarousel } from "@/components/public/image-carousel";
import { BookingCard } from "@/components/public/booking-card";
import { AddonDiscoveredSection } from "@/components/public/addon-discovered-section";
import { SupportContactCard } from "@/components/public/support-contact-card";
import { ReviewList } from "@/components/public/review-list";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

export default function ResourceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const { data: resource, isLoading: resourceLoading } = useQuery({
    queryKey: ["resource", id],
    queryFn: async () => {
      const { data } = await api.get<ResourceResponse>(`/resources/${id}`);
      return data;
    },
  });

  const { data: resourceTypes } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types");
      return data;
    },
  });

  const { data: attachments } = useAttachments("resource", id);

  const resourceType = resourceTypes?.find((t) => t.id === resource?.type_id);
  const isPrimaryVenue = resourceType?.role === "primary";
  const images = attachments?.map((a) => a.url) ?? [];
  const attributes = resource?.attributes as Record<string, unknown> | null;

  if (resourceLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!resource) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-2">
        <h1 className="text-2xl font-bold">Resource not found</h1>
        <p className="text-muted-foreground">This resource may have been removed.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-3 sm:px-4 py-4 sm:py-6">
      <ImageCarousel images={images} alt={resource.name} />

      <div className="mt-4 sm:mt-6 grid gap-6 sm:gap-8 lg:grid-cols-[1fr_380px]">
        <div className="space-y-6 sm:space-y-8">
          <div>
            <div className="flex items-start gap-2 sm:gap-3">
              <h1 className="text-xl font-bold sm:text-3xl">{resource.name}</h1>
              {resourceType && (
                <Badge variant="secondary" className="shrink-0 mt-1">
                  {resourceType.name}
                </Badge>
              )}
            </div>

            {(resource.rating_count ?? 0) > 0 && (
              <button
                onClick={() => document.getElementById("reviews")?.scrollIntoView({ behavior: "smooth" })}
                className="mt-1 flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
              >
                <StarRating rating={resource.rating_avg} size="sm" />
                <span>
                  {resource.rating_avg.toFixed(1)} ({resource.rating_count}{" "}
                  {resource.rating_count === 1 ? "review" : "reviews"})
                </span>
              </button>
            )}
          </div>

          {resource.location_address && (
            <div className="flex items-start gap-2 text-sm text-muted-foreground">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{resource.location_address}</span>
            </div>
          )}

          {resource.description && (
            <div>
              <h2 className="mb-2 text-lg font-semibold">About</h2>
              <p className="leading-relaxed text-muted-foreground">
                {resource.description}
              </p>
            </div>
          )}

          {attributes && Object.keys(attributes).length > 0 && (
            <div>
              <h2 className="mb-3 text-lg font-semibold">Details</h2>
              <div className="grid grid-cols-2 gap-2 sm:gap-3 sm:grid-cols-3">
                {Object.entries(attributes).map(([key, val]) => (
                  <div key={key} className="rounded-lg border p-2 sm:p-3">
                    <p className="text-[11px] sm:text-xs text-muted-foreground capitalize">
                      {key.replace(/_/g, " ")}
                    </p>
                    <p className="mt-0.5 text-xs sm:text-sm font-medium">
                      {Array.isArray(val) ? val.join(", ") : String(val)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {isPrimaryVenue && (
            <>
              <Separator />
              <AddonDiscoveredSection resourceId={id} startDate="" endDate="" />
            </>
          )}

          <ReviewList resourceId={id} />
        </div>

        <div className="hidden lg:flex lg:flex-col lg:gap-4">
          <BookingCard
            resource={resource}
            availabilityModel={resourceType?.availability_model ?? "date_range"}
          />
          {resource.support_contact_id && (
            <SupportContactCard userId={resource.support_contact_id} />
          )}
        </div>
      </div>

      <div className="fixed bottom-0 left-0 right-0 border-t bg-background p-3 lg:hidden z-40">
        <BookingCard
          resource={resource}
          availabilityModel={resourceType?.availability_model ?? "date_range"}
        />
      </div>

      <div className="h-24 lg:hidden" />
    </div>
  );
}
