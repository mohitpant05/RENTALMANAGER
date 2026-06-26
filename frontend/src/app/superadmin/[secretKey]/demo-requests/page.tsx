"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useDemoRequests,
  useUpdateDemoStatus,
  type DemoRequest,
} from "@/hooks/use-demo-requests";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  confirmed: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
};

const STATUS_TRANSITIONS: Record<string, string[]> = {
  pending: ["confirmed", "cancelled"],
  confirmed: ["completed", "cancelled"],
  completed: [],
  cancelled: [],
};

function formatSlot(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function DemoRequestsPage() {
  const { data: requests, isLoading } = useDemoRequests();
  const updateStatus = useUpdateDemoStatus();
  const [filter, setFilter] = useState<string>("all");

  const filtered =
    filter === "all"
      ? requests
      : requests?.filter((r) => r.status === filter);

  const counts = requests?.reduce(
    (acc, r) => {
      acc[r.status] = (acc[r.status] || 0) + 1;
      acc.all = (acc.all || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Demo Requests</h1>
        <p className="text-muted-foreground">
          Manage incoming demo booking requests
        </p>
      </div>

      <div className="flex gap-2">
        {["all", "pending", "confirmed", "completed", "cancelled"].map(
          (s) => (
            <Button
              key={s}
              variant={filter === s ? "default" : "outline"}
              size="sm"
              onClick={() => setFilter(s)}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}{" "}
              {counts?.[s] ? `(${counts[s]})` : ""}
            </Button>
          )
        )}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : !filtered?.length ? (
        <div className="rounded-md border py-12 text-center text-muted-foreground">
          No demo requests found
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Slot</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Requested</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered?.map((req) => (
                <TableRow key={req.id}>
                  <TableCell className="font-medium">{req.name}</TableCell>
                  <TableCell>{req.email}</TableCell>
                  <TableCell>{req.company || "—"}</TableCell>
                  <TableCell className="whitespace-nowrap">
                    {formatSlot(req.slot_start)}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={STATUS_COLORS[req.status] || ""}
                    >
                      {req.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    {formatDate(req.created_at)}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {STATUS_TRANSITIONS[req.status]?.map((next) => (
                        <Button
                          key={next}
                          size="sm"
                          variant={
                            next === "cancelled" ? "destructive" : "outline"
                          }
                          disabled={updateStatus.isPending}
                          onClick={() =>
                            updateStatus.mutate({
                              id: req.id,
                              status: next,
                            })
                          }
                        >
                          {next.charAt(0).toUpperCase() + next.slice(1)}
                        </Button>
                      ))}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {filtered?.some((r) => r.message) && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Messages</h2>
          {filtered
            .filter((r) => r.message)
            .map((r) => (
              <div
                key={r.id}
                className="rounded-md border p-4"
              >
                <div className="mb-1 flex items-center gap-2">
                  <span className="font-medium">{r.name}</span>
                  <Badge
                    variant="outline"
                    className={STATUS_COLORS[r.status] || ""}
                  >
                    {r.status}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">{r.message}</p>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
