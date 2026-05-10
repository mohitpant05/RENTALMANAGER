import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { NotificationResponse, UnreadCountResponse } from "@/types/api";

export function useUnreadCount() {
  return useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: async () => {
      const { data } = await api.get<UnreadCountResponse>("/notifications/unread-count");
      return data;
    },
    refetchInterval: 30_000,
  });
}

export function useNotifications(params?: { unread_only?: boolean; offset?: number; limit?: number }) {
  return useQuery({
    queryKey: ["notifications", params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.unread_only) searchParams.set("unread_only", "true");
      if (params?.offset) searchParams.set("offset", String(params.offset));
      if (params?.limit) searchParams.set("limit", String(params.limit));
      const { data } = await api.get<NotificationResponse[]>(`/notifications?${searchParams.toString()}`);
      return data;
    },
  });
}

export function useMarkRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (notificationId: string) => {
      await api.post(`/notifications/${notificationId}/read`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useMarkAllRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.post("/notifications/read-all");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}
