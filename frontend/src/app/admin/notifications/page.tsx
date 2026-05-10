"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, Check, CheckCheck, X } from "lucide-react";
import {
  useNotifications,
  useMarkRead,
  useMarkAllRead,
} from "@/hooks/use-notifications";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import api from "@/lib/api";
import type { NotificationResponse } from "@/types/api";

const PAGE_SIZE = 20;

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [limit, setLimit] = useState(PAGE_SIZE);

  const { data: notifications, isLoading } = useNotifications({
    unread_only: unreadOnly || undefined,
    limit,
  });
  const markRead = useMarkRead();
  const markAllRead = useMarkAllRead();

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/notifications/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  function handleClick(notification: { id: string; is_read: boolean }) {
    if (!notification.is_read) {
      markRead.mutate(notification.id);
    }
  }

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
          <h1 className="text-2xl font-bold tracking-tight">Notifications</h1>
          <p className="mt-1 text-sm text-muted-foreground">Manage system notifications</p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => markAllRead.mutate()}
          disabled={markAllRead.isPending}
        >
          <CheckCheck className="mr-1.5 h-4 w-4" />
          Mark all read
        </Button>
      </div>

      <div className="flex gap-2">
        <Button
          variant={!unreadOnly ? "default" : "outline"}
          size="sm"
          onClick={() => setUnreadOnly(false)}
        >
          All
        </Button>
        <Button
          variant={unreadOnly ? "default" : "outline"}
          size="sm"
          onClick={() => setUnreadOnly(true)}
        >
          Unread
        </Button>
      </div>

      <div className="space-y-2">
        {notifications && notifications.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
            <Bell className="h-12 w-12 text-muted-foreground" />
            <p className="mt-3 text-muted-foreground">No notifications</p>
          </div>
        )}

        {notifications?.map((n: NotificationResponse) => (
          <Card
            key={n.id}
            className={cn(
              "cursor-pointer transition-colors hover:bg-muted/50",
              !n.is_read && "border-primary/20 bg-primary/5"
            )}
            onClick={() => handleClick(n)}
          >
            <CardContent className="flex items-start gap-3 p-4">
              <div className="mt-0.5">
                {!n.is_read ? (
                  <div className="h-2.5 w-2.5 rounded-full bg-primary" />
                ) : (
                  <Check className="h-3 w-3 text-muted-foreground" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className={cn("text-sm", !n.is_read && "font-medium")}>
                  {n.message}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {new Date(n.created_at).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteMutation.mutate(n.id);
                }}
                className="text-muted-foreground hover:text-destructive"
              >
                <X className="h-3 w-3" />
              </button>
            </CardContent>
          </Card>
        ))}

        {notifications && notifications.length >= limit && (
          <Button
            variant="ghost"
            className="w-full"
            onClick={() => setLimit((l) => l + PAGE_SIZE)}
          >
            Load more
          </Button>
        )}
      </div>
    </div>
  );
}
