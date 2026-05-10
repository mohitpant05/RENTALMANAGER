import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  ReviewResponse,
  ReviewCreate,
  ReviewModerateRequest,
  RatingSummaryResponse,
} from "@/types/api";

export function useReviews(params?: {
  resource_id?: string;
  direction?: string;
  status?: string;
  offset?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["reviews", params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.resource_id) searchParams.set("resource_id", params.resource_id);
      if (params?.direction) searchParams.set("direction", params.direction);
      if (params?.status) searchParams.set("status", params.status);
      if (params?.offset) searchParams.set("offset", String(params.offset));
      searchParams.set("limit", String(params?.limit ?? 20));
      const { data } = await api.get<ReviewResponse[]>(`/reviews?${searchParams.toString()}`);
      return data;
    },
  });
}

export function useMyReviews(params?: { offset?: number; limit?: number }) {
  return useQuery({
    queryKey: ["reviews", "my", params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.offset) searchParams.set("offset", String(params.offset));
      searchParams.set("limit", String(params?.limit ?? 20));
      const { data } = await api.get<ReviewResponse[]>(`/reviews/my?${searchParams.toString()}`);
      return data;
    },
  });
}

export function useRatingSummary(resourceId: string) {
  return useQuery({
    queryKey: ["reviews", "summary", resourceId],
    queryFn: async () => {
      const { data } = await api.get<RatingSummaryResponse>(`/reviews/resource/${resourceId}/summary`);
      return data;
    },
    enabled: !!resourceId,
  });
}

export function useCreateReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (review: ReviewCreate) => {
      const { data } = await api.post<ReviewResponse>("/reviews", review);
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["reviews"] });
      if (data.resource_id) {
        queryClient.invalidateQueries({ queryKey: ["reviews", "summary", data.resource_id] });
      }
    },
  });
}

export function useModerateReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ reviewId, body }: { reviewId: string; body: ReviewModerateRequest }) => {
      const { data } = await api.post<ReviewResponse>(`/reviews/${reviewId}/moderate`, body);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reviews"] });
    },
  });
}
