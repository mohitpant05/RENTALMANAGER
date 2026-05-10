"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bell, Check, CheckCheck } from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import {
  useNotifications,
  useMarkRead,
  useMarkAllRead,
} from "@/hooks/use-notifications";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 20;

function getNavigationUrl(notification: { event_type: string; payload: Record<string, unknown> }): string {
  const bookingId = notification.payload.booking_id as string | undefined;
  switch (notification.event_type) {
    case "booking_created":
    case "booking_confirmed":
    case "booking_cancelled":
    case "booking_rejected":
      return bookingId ? `/bookings/${bookingId}` : "/notifications";
    case "review_received":
      return "/profile";
    default:
      return "/notifications";
  }
}

export default function PublicNotificationsPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const authLoading = useAuthStore((s) => s.isLoading);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [limit, setLimit] = useState(PAGE_SIZE);

  if (!authLoading && !isAuthenticated) {
    router.push("/login?returnUrl=/notifications");
    return null;
  }

  const { data: notifications, isLoading } = useNotifications({
    unread_only: unreadOnly || undefined,
    limit,
  });
  const markRead = useMarkRead();
  const markAllRead = useMarkAllRead();

  function handleClick(notification: { id: string; is_read: boolean; event_type: string; payload: Record<string, unknown> }) {
    if (!notification.is_read) {
      markRead.mutate(notification.id);
    }
    const url = getNavigationUrl(notification);
    router.push(url);
  }

  if (authLoading || isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Notifications</h1>
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

      <div className="mt-4 flex gap-2">
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

      <div className="mt-6 space-y-2">
        {notifications && notifications.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
            <Bell className="h-12 w-12 text-muted-foreground" />
            <p className="mt-3 text-muted-foreground">No notifications</p>
          </div>
        )}

        {notifications?.map((n) => (
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
