"use client";

import { useState } from "react";
import { useReviews } from "@/hooks/use-reviews";
import { useAuthStore } from "@/lib/auth-store";
import { StarRating } from "@/components/reviews/star-rating";
import { RatingSummary } from "@/components/reviews/rating-summary";
import { ReviewForm } from "./review-form";
import { Button } from "@/components/ui/button";

interface ReviewListProps {
  resourceId: string;
}

const PAGE_SIZE = 10;

export function ReviewList({ resourceId }: ReviewListProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [limit, setLimit] = useState(PAGE_SIZE);
  const [formOpen, setFormOpen] = useState(false);

  const { data: reviews, isLoading, refetch } = useReviews({
    resource_id: resourceId,
    direction: "guest_to_resource",
    limit,
  });

  return (
    <section id="reviews" className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Reviews</h2>
        {isAuthenticated && (
          <Button variant="outline" size="sm" onClick={() => setFormOpen(true)}>
            Write a Review
          </Button>
        )}
      </div>

      <RatingSummary resourceId={resourceId} />

      {isLoading && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      )}

      {reviews && reviews.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No reviews yet. Be the first to leave a review!
        </p>
      )}

      {reviews && reviews.length > 0 && (
        <div className="space-y-4">
          {reviews.map((review) => (
            <div key={review.id} className="space-y-1.5 border-b pb-4 last:border-0">
              <div className="flex items-center gap-3">
                <StarRating rating={review.rating} size="sm" />
                <span className="text-xs text-muted-foreground">
                  {new Date(review.created_at).toLocaleDateString()}
                </span>
              </div>
              {review.comment && (
                <p className="text-sm leading-relaxed">{review.comment}</p>
              )}
            </div>
          ))}

          {reviews.length >= limit && (
            <Button
              variant="ghost"
              className="w-full"
              onClick={() => setLimit((l) => l + PAGE_SIZE)}
            >
              Show more reviews
            </Button>
          )}
        </div>
      )}

      <ReviewForm
        resourceId={resourceId}
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSuccess={() => {
          setFormOpen(false);
          refetch();
        }}
      />
    </section>
  );
}
