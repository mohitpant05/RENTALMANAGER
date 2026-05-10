"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { useCreateReview } from "@/hooks/use-reviews";
import { StarSelector } from "./star-selector";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import type { AxiosError } from "axios";

interface ReviewFormProps {
  resourceId: string;
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function ReviewForm({ resourceId, open, onClose, onSuccess }: ReviewFormProps) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const createReview = useCreateReview();

  async function handleSubmit() {
    if (rating === 0) {
      toast.error("Please select a rating");
      return;
    }

    try {
      await createReview.mutateAsync({
        resource_id: resourceId,
        rating,
        comment: comment || undefined,
        direction: "guest_to_resource",
      });
      toast.success("Review submitted!");
      setRating(0);
      setComment("");
      onSuccess();
    } catch (err) {
      const axiosErr = err as AxiosError;
      if (axiosErr.response?.status === 403) {
        toast.error("You need a completed booking to leave a review");
      } else {
        toast.error("Failed to submit review");
      }
    }
  }

  function handleOpenChange(isOpen: boolean) {
    if (!isOpen) {
      setRating(0);
      setComment("");
      onClose();
    }
  }

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Write a Review</SheetTitle>
          <SheetDescription>
            Share your experience with this resource.
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-4 px-4">
          <div className="space-y-2">
            <Label>Rating</Label>
            <StarSelector value={rating} onChange={setRating} />
          </div>

          <div className="space-y-2">
            <Label htmlFor="review-comment">Comment (optional)</Label>
            <Textarea
              id="review-comment"
              placeholder="Tell others about your experience..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={4}
            />
          </div>
        </div>

        <SheetFooter>
          <Button
            onClick={handleSubmit}
            disabled={createReview.isPending || rating === 0}
          >
            {createReview.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Submit Review
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
