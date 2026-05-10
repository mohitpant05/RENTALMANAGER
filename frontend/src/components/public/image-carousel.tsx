"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Image as ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ImageCarouselProps {
  images: string[];
  alt: string;
}

export function ImageCarousel({ images, alt }: ImageCarouselProps) {
  const [current, setCurrent] = useState(0);

  if (images.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl bg-gradient-to-br from-muted to-muted/50 sm:h-80 lg:h-96">
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <ImageIcon className="h-12 w-12" />
          <span className="text-sm">No images available</span>
        </div>
      </div>
    );
  }

  if (images.length === 1) {
    return (
      <div className="overflow-hidden rounded-xl">
        <img
          src={images[0]}
          alt={alt}
          className="h-64 w-full object-cover sm:h-80 lg:h-96"
        />
      </div>
    );
  }

  function prev() {
    setCurrent((c) => (c === 0 ? images.length - 1 : c - 1));
  }

  function next() {
    setCurrent((c) => (c === images.length - 1 ? 0 : c + 1));
  }

  return (
    <div className="group relative overflow-hidden rounded-xl">
      <img
        src={images[current]}
        alt={`${alt} — image ${current + 1}`}
        className="h-64 w-full object-cover sm:h-80 lg:h-96"
      />

      <Button
        variant="secondary"
        size="icon"
        className="absolute left-3 top-1/2 h-9 w-9 -translate-y-1/2 opacity-0 transition-opacity group-hover:opacity-100"
        onClick={prev}
      >
        <ChevronLeft className="h-5 w-5" />
      </Button>

      <Button
        variant="secondary"
        size="icon"
        className="absolute right-3 top-1/2 h-9 w-9 -translate-y-1/2 opacity-0 transition-opacity group-hover:opacity-100"
        onClick={next}
      >
        <ChevronRight className="h-5 w-5" />
      </Button>

      <div className="absolute bottom-3 left-1/2 flex -translate-x-1/2 gap-1.5">
        {images.map((_, i) => (
          <button
            key={i}
            onClick={() => setCurrent(i)}
            className={cn(
              "h-2 w-2 rounded-full transition-colors",
              i === current ? "bg-white" : "bg-white/50"
            )}
          />
        ))}
      </div>
    </div>
  );
}
