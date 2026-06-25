"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, RotateCcw } from "lucide-react";
import api from "@/lib/api";
import type { RefundPendingItem, BulkRefundSettleResponse } from "@/types/payment";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";

export default function RefundsPage() {
  const searchParams = useSearchParams();
  const tab = searchParams.get("tab") || "pending";

  return (
    <div className="flex-1 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Refund Settlements</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Review and settle refunds for cancelled bookings
        </p>
      </div>
      {tab === "pending" && <PendingRefundsTab />}
      {tab === "settled" && <SettledRefundsTab />}
    </div>
  );
}

function PendingRefundsTab() {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [overrides, setOverrides] = useState<Record<string, number>>({});

  const { data: items, isLoading } = useQuery({
    queryKey: ["refund-pending"],
    queryFn: async () => {
      const { data } = await api.get<RefundPendingItem[]>("/admin/refunds/pending");
      return data;
    },
  });

  const settleMutation = useMutation({
    mutationFn: async (paymentIds: string[]) => {
      const settleItems = paymentIds.map((pid) => ({
        payment_id: pid,
        override_percent: overrides[pid] ?? null,
      }));
      const { data } = await api.post<BulkRefundSettleResponse>("/admin/refunds/settle", {
        items: settleItems,
      });
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["refund-pending"] });
      setSelected(new Set());
      setOverrides({});
      if (data.failed_count > 0) {
        toast.warning(`Settled ${data.settled_count}, failed ${data.failed_count}`);
      } else {
        toast.success(`Settled ${data.settled_count} refund(s)`);
      }
    },
    onError: () => {
      toast.error("Failed to process refunds");
    },
  });

  const allSelected = items != null && items.length > 0 && selected.size === items.length;

  function toggleAll() {
    if (!items) return;
    if (allSelected) {
      setSelected(new Set());
    } else {
      setSelected(new Set(items.map((i) => i.payment_id)));
    }
  }

  function toggleOne(paymentId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(paymentId)) next.delete(paymentId);
      else next.add(paymentId);
      return next;
    });
  }

  function handleSettle() {
    if (selected.size === 0) return;
    settleMutation.mutate(Array.from(selected));
  }

  function getRefundAmount(item: RefundPendingItem): number {
    const pct = overrides[item.payment_id] ?? item.refund_percent;
    return Math.round(item.booking_amount * pct / 100 * 100) / 100;
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <RotateCcw className="h-10 w-10 text-muted-foreground mb-3" />
          <p className="text-muted-foreground">No pending refunds</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {items.length} pending refund{items.length !== 1 ? "s" : ""}
          {selected.size > 0 && ` · ${selected.size} selected`}
        </p>
        <Button
          onClick={handleSettle}
          disabled={selected.size === 0 || settleMutation.isPending}
        >
          {settleMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Settle Selected ({selected.size})
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                </TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Resource</TableHead>
                <TableHead>Cancelled</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead className="text-right w-28">Refund %</TableHead>
                <TableHead className="text-right">Refund</TableHead>
                <TableHead>Provider</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.payment_id}>
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={selected.has(item.payment_id)}
                      onChange={() => toggleOne(item.payment_id)}
                      className="h-4 w-4 rounded border-gray-300"
                    />
                  </TableCell>
                  <TableCell>
                    <div className="font-medium">{item.customer_name}</div>
                    <div className="text-xs text-muted-foreground">{item.customer_email}</div>
                  </TableCell>
                  <TableCell>{item.resource_name}</TableCell>
                  <TableCell>
                    {item.cancelled_at
                      ? new Date(item.cancelled_at).toLocaleDateString()
                      : "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    {item.currency} {item.booking_amount.toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right">
                    <Input
                      type="number"
                      min={0}
                      max={100}
                      value={overrides[item.payment_id] ?? item.refund_percent}
                      onChange={(e) =>
                        setOverrides((prev) => ({
                          ...prev,
                          [item.payment_id]: parseFloat(e.target.value) || 0,
                        }))
                      }
                      className="w-20 text-right ml-auto h-8"
                    />
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {item.currency} {getRefundAmount(item).toFixed(2)}
                  </TableCell>
                  <TableCell>
                    <Badge variant={item.provider === "manual" ? "secondary" : "default"}>
                      {item.provider}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function SettledRefundsTab() {
  const { data: items, isLoading } = useQuery({
    queryKey: ["refund-settled"],
    queryFn: async () => {
      const { data } = await api.get<RefundPendingItem[]>("/admin/refunds/settled");
      return data;
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <p className="text-muted-foreground">No settled refunds yet</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Customer</TableHead>
              <TableHead>Resource</TableHead>
              <TableHead>Cancelled</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead className="text-right">Refunded</TableHead>
              <TableHead>Provider</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.payment_id}>
                <TableCell>
                  <div className="font-medium">{item.customer_name}</div>
                  <div className="text-xs text-muted-foreground">{item.customer_email}</div>
                </TableCell>
                <TableCell>{item.resource_name}</TableCell>
                <TableCell>
                  {item.cancelled_at
                    ? new Date(item.cancelled_at).toLocaleDateString()
                    : "—"}
                </TableCell>
                <TableCell className="text-right">
                  {item.currency} {item.booking_amount.toFixed(2)}
                </TableCell>
                <TableCell className="text-right font-medium">
                  {item.currency} {item.refund_amount.toFixed(2)}
                </TableCell>
                <TableCell>
                  <Badge variant={item.provider === "manual" ? "secondary" : "default"}>
                    {item.provider}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-green-600 border-green-600">
                    Settled
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
