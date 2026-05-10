"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  Box,
  CalendarDays,
  Star,
  Users,
  Bell,
  ArrowUpRight,
} from "lucide-react";
import api from "@/lib/api";
import type {
  BookingResponse,
  ResourceResponse,
  ReviewResponse,
  NotificationResponse,
  ResourceTypeResponse,
} from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function DashboardPage() {
  const { data: types } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types");
      return data;
    },
    staleTime: 30_000,
  });

  const { data: resources } = useQuery({
    queryKey: ["resources"],
    queryFn: async () => {
      const { data } = await api.get<ResourceResponse[]>("/resources?limit=100");
      return data;
    },
    staleTime: 30_000,
  });

  const { data: bookings } = useQuery({
    queryKey: ["bookings"],
    queryFn: async () => {
      const { data } = await api.get<BookingResponse[]>("/bookings");
      return data;
    },
    staleTime: 30_000,
  });

  const { data: reviews } = useQuery({
    queryKey: ["reviews"],
    queryFn: async () => {
      const { data } = await api.get<ReviewResponse[]>("/reviews");
      return data;
    },
    staleTime: 30_000,
  });

  const { data: notifications } = useQuery({
    queryKey: ["notifications", { limit: 10 }],
    queryFn: async () => {
      const { data } = await api.get<NotificationResponse[]>("/notifications?limit=10");
      return data;
    },
    staleTime: 30_000,
  });

  const pendingBookings = bookings?.filter((b) => b.status === "pending") ?? [];
  const activeBookings = bookings?.filter((b) => b.status === "active" || b.status === "confirmed") ?? [];
  const pendingReviews = reviews?.filter((r) => r.status === "pending") ?? [];

  const quickLinks = [
    { href: "/admin/resources", icon: Box, label: "Resources", color: "text-blue-500" },
    { href: "/admin/bookings", icon: CalendarDays, label: "Bookings", color: "text-green-500" },
    { href: "/admin/reviews", icon: Star, label: "Reviews", color: "text-yellow-500" },
    { href: "/admin/staff", icon: Users, label: "Staff", color: "text-purple-500" },
    { href: "/admin/notifications", icon: Bell, label: "Notifications", color: "text-orange-500" },
  ];

  return (
    <div className="flex-1 space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">Overview of your rental management system</p>
      </div>

      {/* Quick Links */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {quickLinks.map(({ href, icon: Icon, label, color }) => (
          <Link key={href} href={href} className="group">
            <Card className="transition-colors hover:bg-muted/50">
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex items-center gap-3">
                  <Icon className={`h-5 w-5 ${color}`} />
                  <span className="text-sm font-medium">{label}</span>
                </div>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Resources</CardTitle>
            <Box className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{resources?.length ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              {types?.length ?? 0} type{(types?.length ?? 0) !== 1 ? "s" : ""}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Bookings</CardTitle>
            <CalendarDays className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{bookings?.length ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              {pendingBookings.length} pending
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Reviews</CardTitle>
            <Star className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{reviews?.length ?? 0}</div>
            <p className="text-xs text-muted-foreground">
              {pendingReviews.length} awaiting moderation
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Active Bookings</CardTitle>
            <CalendarDays className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeBookings.length}</div>
            <p className="text-xs text-muted-foreground">
              confirmed or in progress
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Bookings</CardTitle>
            <Link href="/admin/bookings" className="text-xs text-muted-foreground hover:text-foreground">
              View all →
            </Link>
          </CardHeader>
          <CardContent>
            {(!bookings || bookings.length === 0) && (
              <p className="text-sm text-muted-foreground">No bookings yet</p>
            )}
            {bookings && bookings.length > 0 && (
              <div className="space-y-3">
                {bookings.slice(0, 5).map((b) => (
                  <div key={b.id} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <CalendarDays className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="font-medium">{b.resource_id.slice(0, 8)}</span>
                    </div>
                    <Badge variant={b.status === "pending" ? "warning" : b.status === "confirmed" ? "default" : "muted"}>
                      {b.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Notifications</CardTitle>
            <Link href="/admin/notifications" className="text-xs text-muted-foreground hover:text-foreground">
              View all →
            </Link>
          </CardHeader>
          <CardContent>
            {(!notifications || notifications.length === 0) && (
              <p className="text-sm text-muted-foreground">No notifications</p>
            )}
            {notifications && notifications.length > 0 && (
              <div className="space-y-3">
                {notifications.slice(0, 5).map((n) => (
                  <div key={n.id} className="text-sm">
                    <p className={n.is_read ? "text-muted-foreground" : "font-medium"}>
                      {n.message}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {new Date(n.created_at).toLocaleDateString()}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
