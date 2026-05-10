"use client";

import { useRatingSummary } from "@/hooks/use-reviews";
import { StarRating } from "./star-rating";

interface RatingSummaryProps {
  resourceId: string;
}

export function RatingSummary({ resourceId }: RatingSummaryProps) {
  const { data, isLoading } = useRatingSummary(resourceId);

  if (isLoading) {
    return (
      <div className="h-32 animate-pulse rounded-lg bg-muted" />
    );
  }

  if (!data || data.count === 0) {
    return (
      <p className="text-sm text-muted-foreground">No reviews yet</p>
    );
  }

  const maxCount = Math.max(...Object.values(data.distribution), 1);

  return (
    <div className="flex gap-6">
      <div className="flex flex-col items-center justify-center">
        <span className="text-4xl font-bold">{data.average.toFixed(1)}</span>
        <StarRating rating={data.average} size="md" />
        <span className="mt-1 text-sm text-muted-foreground">
          {data.count} {data.count === 1 ? "review" : "reviews"}
        </span>
      </div>

      <div className="flex-1 space-y-1.5">
        {[5, 4, 3, 2, 1].map((star) => {
          const count = data.distribution[String(star)] ?? 0;
          const pct = (count / maxCount) * 100;

          return (
            <div key={star} className="flex items-center gap-2 text-sm">
              <span className="w-3 text-right text-muted-foreground">{star}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-yellow-400"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="w-6 text-right text-xs text-muted-foreground">{count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
