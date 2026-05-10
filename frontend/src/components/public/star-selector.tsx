"use client";

import { useState } from "react";
import { Star } from "lucide-react";
import { cn } from "@/lib/utils";

interface StarSelectorProps {
  value: number;
  onChange: (rating: number) => void;
  max?: number;
}

export function StarSelector({ value, onChange, max = 5 }: StarSelectorProps) {
  const [hover, setHover] = useState(0);

  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: max }, (_, i) => {
        const starValue = i + 1;
        const active = starValue <= (hover || value);

        return (
          <button
            key={i}
            type="button"
            onMouseEnter={() => setHover(starValue)}
            onMouseLeave={() => setHover(0)}
            onClick={() => onChange(starValue)}
            className="rounded-sm p-0.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Star
              className={cn(
                "h-7 w-7 transition-colors",
                active
                  ? "fill-yellow-400 text-yellow-400"
                  : "fill-muted text-muted-foreground/30"
              )}
            />
          </button>
        );
      })}
    </div>
  );
}
