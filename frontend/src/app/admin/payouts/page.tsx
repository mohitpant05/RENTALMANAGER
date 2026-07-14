"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { usePermissions } from "@/hooks/use-permissions";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, CheckCircle } from "lucide-react";
import api from "@/lib/api";
import type { OwnerBalance, PayoutCreate, PayoutResponse } from "@/types/payout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { toast } from "sonner";

export default function PayoutsPage() {
  const router = useRouter();
  const { hasPermission, isLoading: permsLoading } = usePermissions();
  const searchParams = useSearchParams();
  const tab = searchParams.get("tab") || "balances";

  const denied = !permsLoading && !hasPermission("settings:*:manage");
  useEffect(() => { if (denied) router.replace("/admin"); }, [denied, router]);

  if (permsLoading || denied) return <div className="flex flex-1 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" /></div>;

  return (
    <div className="flex-1 space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Payouts</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage resource owner payouts and settlements
        </p>
      </div>

      <div className="flex gap-1 border-b">
        <button
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            tab === "balances"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => router.push("/admin/payouts")}
        >
          Balances
        </button>
        <button
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            tab === "history"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => router.push("/admin/payouts?tab=history")}
        >
          History
        </button>
      </div>

      {tab === "balances" && <BalancesTab />}
      {tab === "history" && <HistoryTab />}
    </div>
  );
}

function BalancesTab() {
  const queryClient = useQueryClient();
  const [selectedOwner, setSelectedOwner] = useState<OwnerBalance | null>(null);

  const { data: balances, isLoading } = useQuery({
    queryKey: ["payout-balances"],
    queryFn: async () => {
      const { data } = await api.get<OwnerBalance[]>("/payouts/balances");
      return data;
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!balances || balances.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No pending payouts
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <div className="grid gap-4">
        {balances.map((b) => (
          <Card key={b.owner_id}>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-base">{b.owner_name}</CardTitle>
                <CardDescription>{b.owner_email}</CardDescription>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold">
                  {b.currency} {b.pending_amount.toFixed(2)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {b.booking_count} booking{b.booking_count !== 1 ? "s" : ""}
                </p>
              </div>
            </CardHeader>
            <CardContent className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {b.last_settled
                  ? `Last settled: ${new Date(b.last_settled).toLocaleDateString()}`
                  : "Never settled"}
              </span>
              <Button size="sm" onClick={() => setSelectedOwner(b)}>
                Create Payout
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {selectedOwner && (
        <CreatePayoutSheet
          owner={selectedOwner}
          open={!!selectedOwner}
          onClose={() => {
            setSelectedOwner(null);
            queryClient.invalidateQueries({ queryKey: ["payout-balances"] });
          }}
        />
      )}
    </>
  );
}

function CreatePayoutSheet({
  owner,
  open,
  onClose,
}: {
  owner: OwnerBalance;
  open: boolean;
  onClose: () => void;
}) {
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState(new Date().toISOString().split("T")[0]);
  const [notes, setNotes] = useState("");

  const createMutation = useMutation({
    mutationFn: async () => {
      const payload: PayoutCreate = {
        owner_id: owner.owner_id,
        period_start: new Date(periodStart).toISOString(),
        period_end: new Date(periodEnd + "T23:59:59").toISOString(),
        currency: owner.currency,
        notes: notes || undefined,
      };
      const { data } = await api.post<PayoutResponse>("/payouts", payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Payout created");
      onClose();
    },
    onError: () => {
      toast.error("Failed to create payout");
    },
  });

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="sm:max-w-md">
        <SheetHeader className="px-6 pt-6">
          <SheetTitle>Create Payout — {owner.owner_name}</SheetTitle>
          <SheetDescription>
            Pending: {owner.currency} {owner.pending_amount.toFixed(2)} from {owner.booking_count} bookings
          </SheetDescription>
        </SheetHeader>
        <div className="space-y-4 px-6 pb-6">
          <div className="space-y-2">
            <Label>Period Start</Label>
            <Input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Period End</Label>
            <Input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Notes (optional)</Label>
            <Input
              placeholder="Settlement notes..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
          <div className="flex gap-3 border-t pt-4">
            <Button
              className="flex-1"
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending || !periodStart}
            >
              {createMutation.isPending && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
              Create Payout
            </Button>
            <Button variant="outline" onClick={onClose}>Cancel</Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function HistoryTab() {
  const { data: payouts, isLoading } = useQuery({
    queryKey: ["payouts"],
    queryFn: async () => {
      const { data } = await api.get<PayoutResponse[]>("/payouts");
      return data;
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!payouts || payouts.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No payouts yet
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {payouts.map((p) => (
        <PayoutCard key={p.id} payout={p} />
      ))}
    </div>
  );
}

function PayoutCard({ payout: p }: { payout: PayoutResponse }) {
  const queryClient = useQueryClient();

  const settleMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<PayoutResponse>(`/payouts/${p.id}/settle`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payouts"] });
      queryClient.invalidateQueries({ queryKey: ["payout-balances"] });
      toast.success("Payout settled");
    },
    onError: () => {
      toast.error("Failed to settle payout");
    },
  });

  return (
    <Card>
      <CardContent className="flex items-center justify-between py-4">
        <div>
          <p className="font-medium">
            {p.currency} {p.amount.toFixed(2)}
          </p>
          <p className="text-xs text-muted-foreground">
            {p.period_start
              ? `${new Date(p.period_start).toLocaleDateString()} — ${new Date(p.period_end!).toLocaleDateString()}`
              : "No period"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant={p.status === "settled" ? "secondary" : "outline"}>
            {p.status}
          </Badge>
          {p.status === "pending" && (
            <Button
              size="sm"
              onClick={() => settleMutation.mutate()}
              disabled={settleMutation.isPending}
            >
              {settleMutation.isPending ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <CheckCircle className="mr-1 h-3 w-3" />
              )}
              Settle
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
