import { Star } from "lucide-react";
import { cn } from "@/lib/utils";

interface StarRatingProps {
  rating: number;
  max?: number;
  size?: "sm" | "md";
}

export function StarRating({ rating, max = 5, size = "sm" }: StarRatingProps) {
  const sizeClass = size === "sm" ? "h-3.5 w-3.5" : "h-5 w-5";

  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: max }, (_, i) => {
        const filled = i < Math.floor(rating);
        const half = !filled && i < rating;

        return (
          <Star
            key={i}
            className={cn(
              sizeClass,
              filled
                ? "fill-yellow-400 text-yellow-400"
                : half
                  ? "fill-yellow-400/50 text-yellow-400"
                  : "fill-muted text-muted-foreground/30"
            )}
          />
        );
      })}
    </div>
  );
}
