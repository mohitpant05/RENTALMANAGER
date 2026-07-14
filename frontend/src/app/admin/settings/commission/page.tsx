"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Pencil } from "lucide-react";
import { usePermissions } from "@/hooks/use-permissions";
import api from "@/lib/api";
import type { ResourceTypeResponse } from "@/types/api";
import type {
  CommissionConfigResponse,
  CommissionConfigUpdate,
} from "@/types/commission";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { toast } from "sonner";

export default function CommissionSettingsPage() {
  const router = useRouter();
  const { hasPermission, isLoading: permsLoading } = usePermissions();
  const queryClient = useQueryClient();
  const [editingType, setEditingType] = useState<ResourceTypeResponse | null>(null);

  const { data: resourceTypes, isLoading } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types");
      return data;
    },
  });

  const denied = !permsLoading && !hasPermission("settings:*:manage");
  useEffect(() => { if (denied) router.replace("/admin"); }, [denied, router]);

  if (permsLoading || denied) {
    return <div className="flex flex-1 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" /></div>;
  }

  return (
    <div className="flex-1 space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Commission Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Configure platform commission per resource type. Per-resource overrides
          can be set via API.
        </p>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      )}

      <div className="grid gap-4">
        {resourceTypes?.map((rt) => (
          <CommissionTypeCard
            key={rt.id}
            resourceType={rt}
            onEdit={() => setEditingType(rt)}
          />
        ))}
      </div>

      {editingType && (
        <CommissionEditSheet
          resourceType={editingType}
          open={!!editingType}
          onClose={() => {
            setEditingType(null);
            queryClient.invalidateQueries({ queryKey: ["commission"] });
          }}
        />
      )}
    </div>
  );
}

function CommissionTypeCard({
  resourceType,
  onEdit,
}: {
  resourceType: ResourceTypeResponse;
  onEdit: () => void;
}) {
  const { data: commission } = useQuery({
    queryKey: ["commission", "resource-type", resourceType.id],
    queryFn: async () => {
      const { data } = await api.get<CommissionConfigResponse>(
        `/commission/resource-type/${resourceType.id}`
      );
      return data;
    },
  });

  const config = commission?.config;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle className="text-base">{resourceType.name}</CardTitle>
          <CardDescription>
            {config
              ? `Owner: ${config.owner_percent}% + ${config.currency} ${config.owner_fixed} | Customer: ${config.customer_percent}% + ${config.currency} ${config.customer_fixed}`
              : "No commission configured"}
          </CardDescription>
        </div>
        <Button size="sm" variant="outline" onClick={onEdit}>
          <Pencil className="mr-1 h-3 w-3" />
          Edit
        </Button>
      </CardHeader>
    </Card>
  );
}

function CommissionEditSheet({
  resourceType,
  open,
  onClose,
}: {
  resourceType: ResourceTypeResponse;
  open: boolean;
  onClose: () => void;
}) {
  const [ownerPercent, setOwnerPercent] = useState(0);
  const [ownerFixed, setOwnerFixed] = useState(0);
  const [customerPercent, setCustomerPercent] = useState(0);
  const [customerFixed, setCustomerFixed] = useState(0);
  const [loaded, setLoaded] = useState(false);

  const { data: commission } = useQuery({
    queryKey: ["commission", "resource-type", resourceType.id],
    queryFn: async () => {
      const { data } = await api.get<CommissionConfigResponse>(
        `/commission/resource-type/${resourceType.id}`
      );
      return data;
    },
  });

  if (commission && !loaded) {
    const c = commission.config;
    if (c) {
      setOwnerPercent(c.owner_percent);
      setOwnerFixed(c.owner_fixed);
      setCustomerPercent(c.customer_percent);
      setCustomerFixed(c.customer_fixed);
    }
    setLoaded(true);
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload: CommissionConfigUpdate = {
        owner_percent: ownerPercent,
        owner_fixed: ownerFixed,
        customer_percent: customerPercent,
        customer_fixed: customerFixed,
      };
      await api.patch(`/commission/resource-type/${resourceType.id}`, payload);
    },
    onSuccess: () => {
      toast.success("Commission updated");
      onClose();
    },
    onError: () => {
      toast.error("Failed to update commission");
    },
  });

  const sampleTotal = 1000;
  const ownerComm = Math.round((sampleTotal * ownerPercent) / 100 + ownerFixed);
  const serviceFee = Math.round((sampleTotal * customerPercent) / 100 + customerFixed);

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="overflow-y-auto sm:max-w-md">
        <SheetHeader className="px-6 pt-6">
          <SheetTitle>Edit Commission — {resourceType.name}</SheetTitle>
          <SheetDescription>
            Set platform commission for all {resourceType.name.toLowerCase()} resources
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-5 px-6 pb-6">
          <div className="space-y-4 rounded-lg border p-4">
            <p className="text-sm font-medium">Owner Deduction</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Percentage (%)</Label>
                <Input
                  type="number"
                  step="0.1"
                  min="0"
                  max="100"
                  value={ownerPercent}
                  onKeyDown={(e) => { if (e.key === "-") e.preventDefault(); }}
                  onChange={(e) => {
                    const v = parseFloat(e.target.value) || 0;
                    setOwnerPercent(Math.min(100, Math.max(0, v)));
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Fixed Amount</Label>
                <Input
                  type="number"
                  step="1"
                  min="0"
                  max="1000000"
                  value={ownerFixed}
                  onKeyDown={(e) => { if (e.key === "-") e.preventDefault(); }}
                  onChange={(e) => {
                    const v = parseFloat(e.target.value) || 0;
                    setOwnerFixed(Math.min(1_000_000, Math.max(0, v)));
                  }}
                />
              </div>
            </div>
          </div>

          <div className="space-y-4 rounded-lg border p-4">
            <p className="text-sm font-medium">Customer Service Fee</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Percentage (%)</Label>
                <Input
                  type="number"
                  step="0.1"
                  min="0"
                  max="100"
                  value={customerPercent}
                  onKeyDown={(e) => { if (e.key === "-") e.preventDefault(); }}
                  onChange={(e) => {
                    const v = parseFloat(e.target.value) || 0;
                    setCustomerPercent(Math.min(100, Math.max(0, v)));
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Fixed Amount</Label>
                <Input
                  type="number"
                  step="1"
                  min="0"
                  max="1000000"
                  value={customerFixed}
                  onKeyDown={(e) => { if (e.key === "-") e.preventDefault(); }}
                  onChange={(e) => {
                    const v = parseFloat(e.target.value) || 0;
                    setCustomerFixed(Math.min(1_000_000, Math.max(0, v)));
                  }}
                />
              </div>
            </div>
          </div>

          <div className="rounded-lg bg-muted/50 p-4 text-sm space-y-2">
            <p className="font-medium">Preview (on a {sampleTotal} booking)</p>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Owner gets</span>
              <span className="font-medium">{sampleTotal - ownerComm}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Customer pays</span>
              <span className="font-medium">{sampleTotal + serviceFee}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Platform earns</span>
              <span className="font-medium text-primary">{ownerComm + serviceFee}</span>
            </div>
          </div>

          <div className="flex gap-3 border-t pt-5">
            <Button
              className="flex-1"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
            >
              {saveMutation.isPending && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
              Save
            </Button>
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
