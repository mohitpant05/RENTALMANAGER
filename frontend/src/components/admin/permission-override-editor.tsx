"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import type {
  EffectivePermissionsResponse,
  PermissionGroup,
  PermissionResponse,
} from "@/types/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface PermissionOverrideEditorProps {
  userId: string;
}

export function PermissionOverrideEditor({ userId }: PermissionOverrideEditorProps) {
  const qc = useQueryClient();
  const [addingPermId, setAddingPermId] = useState<string | null>(null);
  const [addingGranted, setAddingGranted] = useState(true);

  const { data: effective } = useQuery({
    queryKey: ["staff-permissions", userId],
    queryFn: async () => {
      const { data } = await api.get<EffectivePermissionsResponse>(
        `/admin/staff/${userId}/permissions`
      );
      return data;
    },
  });

  const { data: allGroups = [] } = useQuery({
    queryKey: ["admin-permissions"],
    queryFn: async () => {
      const { data } = await api.get<PermissionGroup[]>("/admin/permissions");
      return data;
    },
  });

  const allPerms: PermissionResponse[] = allGroups.flatMap((g) => g.permissions);
  const overriddenIds = new Set(effective?.overrides.map((o) => o.permission_id) ?? []);
  const availablePerms = allPerms.filter((p) => !overriddenIds.has(p.id));

  const saveMutation = useMutation({
    mutationFn: async (overrides: { permission_id: string; granted: boolean }[]) => {
      await api.put(`/admin/staff/${userId}/permissions/overrides`, { overrides });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["staff-permissions", userId] });
      toast.success("Overrides updated");
    },
    onError: () => {
      toast.error("Failed to update overrides");
    },
  });

  function removeOverride(permissionId: string) {
    const remaining = (effective?.overrides ?? [])
      .filter((o) => o.permission_id !== permissionId)
      .map((o) => ({ permission_id: o.permission_id, granted: o.granted }));
    saveMutation.mutate(remaining);
  }

  function addOverride() {
    if (!addingPermId) return;
    const current = (effective?.overrides ?? []).map((o) => ({
      permission_id: o.permission_id,
      granted: o.granted,
    }));
    current.push({ permission_id: addingPermId, granted: addingGranted });
    saveMutation.mutate(current);
    setAddingPermId(null);
    setAddingGranted(true);
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold">Permission Overrides</h4>
      </div>

      {effective?.overrides.length === 0 && (
        <p className="text-xs text-muted-foreground">No overrides set. Role defaults apply.</p>
      )}

      {effective?.overrides.map((ov) => (
        <div key={ov.permission_id} className="flex items-center justify-between border rounded px-3 py-2">
          <div className="flex items-center gap-2">
            <Badge variant={ov.granted ? "default" : "destructive"} className="text-[10px]">
              {ov.granted ? "Grant" : "Revoke"}
            </Badge>
            <span className="text-sm">{ov.description || ov.codename}</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => removeOverride(ov.permission_id)}
            disabled={saveMutation.isPending}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      ))}

      <div className="flex items-center gap-2 pt-2">
        <Select value={addingPermId ?? ""} onValueChange={setAddingPermId}>
          <SelectTrigger className="flex-1 h-8 text-xs">
            <SelectValue placeholder="Select permission..." />
          </SelectTrigger>
          <SelectContent>
            {availablePerms.map((p) => (
              <SelectItem key={p.id} value={p.id} className="text-xs">
                {p.codename}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={addingGranted ? "grant" : "revoke"}
          onValueChange={(v) => setAddingGranted(v === "grant")}
        >
          <SelectTrigger className="w-24 h-8 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="grant" className="text-xs">Grant</SelectItem>
            <SelectItem value="revoke" className="text-xs">Revoke</SelectItem>
          </SelectContent>
        </Select>
        <Button
          size="sm"
          variant="outline"
          className="h-8"
          onClick={addOverride}
          disabled={!addingPermId || saveMutation.isPending}
        >
          <Plus className="h-3 w-3" />
        </Button>
      </div>
    </div>
  );
}
