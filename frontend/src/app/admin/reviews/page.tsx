"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, X, Loader2 } from "lucide-react";
import api from "@/lib/api";
import type { ReviewResponse, ReviewModerateRequest } from "@/types/api";
import { useReviews } from "@/hooks/use-reviews";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

const STATUS_VARIANT: Record<string, "muted" | "success" | "destructive" | "warning"> = {
  pending: "warning",
  approved: "success",
  rejected: "destructive",
};

export default function ReviewsPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [rejectionReason, setRejectionReason] = useState<Record<string, string>>({});
  const [editingId, setEditingId] = useState<string | null>(null);

  const { data: reviews, isLoading } = useReviews({
    status: statusFilter === "all" ? undefined : statusFilter,
    limit: 50,
  });

  const moderateMutation = useMutation({
    mutationFn: async ({ reviewId, body }: { reviewId: string; body: ReviewModerateRequest }) => {
      const { data } = await api.post<ReviewResponse>(`/reviews/${reviewId}/moderate`, body);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews"] });
      toast.success("Review updated");
      setEditingId(null);
    },
    onError: () => {
      toast.error("Failed to update review");
    },
  });

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Reviews</h1>
          <p className="mt-1 text-sm text-muted-foreground">Moderate customer reviews</p>
        </div>
      </div>

      <Select value={statusFilter} onValueChange={setStatusFilter}>
        <SelectTrigger className="w-[200px]">
          <SelectValue placeholder="Filter by status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Reviews</SelectItem>
          <SelectItem value="pending">Pending</SelectItem>
          <SelectItem value="approved">Approved</SelectItem>
          <SelectItem value="rejected">Rejected</SelectItem>
        </SelectContent>
      </Select>

      <div className="space-y-3">
        {reviews?.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
            <p className="text-muted-foreground">No reviews found</p>
          </div>
        )}

        {reviews?.map((review) => (
          <Card key={review.id}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-semibold">{"★".repeat(review.rating)}{"☆".repeat(5 - review.rating)}</span>
                    <Badge variant={STATUS_VARIANT[review.status] ?? "muted"}>
                      {review.status}
                    </Badge>
                    {review.direction && (
                      <Badge variant="muted" className="text-xs">{review.direction}</Badge>
                    )}
                  </div>

                  {review.comment && (
                    <p className="text-sm text-muted-foreground">{review.comment}</p>
                  )}

                  <p className="text-xs text-muted-foreground">
                    {new Date(review.created_at).toLocaleDateString()} · Resource: {review.resource_id?.slice(0, 8)}
                  </p>
                </div>

                {review.status === "pending" && editingId === review.id && (
                  <div className="space-y-2 min-w-[200px]">
                    <Textarea
                      placeholder="Rejection reason (optional)"
                      value={rejectionReason[review.id] || ""}
                      onChange={(e) => setRejectionReason((prev) => ({ ...prev, [review.id]: e.target.value }))}
                      rows={2}
                      className="text-sm"
                    />
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => moderateMutation.mutate({
                          reviewId: review.id,
                          body: { status: "approved" },
                        })}
                        disabled={moderateMutation.isPending}
                      >
                        <Check className="mr-1 h-3 w-3" />
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => moderateMutation.mutate({
                          reviewId: review.id,
                          body: { status: "rejected", rejection_reason: rejectionReason[review.id] || undefined },
                        })}
                        disabled={moderateMutation.isPending}
                      >
                        {moderateMutation.isPending ? (
                          <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                        ) : (
                          <X className="mr-1 h-3 w-3" />
                        )}
                        Reject
                      </Button>
                    </div>
                  </div>
                )}

                {review.status === "pending" && editingId !== review.id && (
                  <Button size="sm" variant="outline" onClick={() => setEditingId(review.id)}>
                    Moderate
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
