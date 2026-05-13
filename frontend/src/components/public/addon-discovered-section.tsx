"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Package } from "lucide-react";
import { useAddons } from "@/hooks/use-addons";
import { AddonResourceCard } from "@/components/public/addon-resource-card";
import type { AddonTypeGroup } from "@/types/api";

interface AddonDiscoveredSectionProps {
  resourceId: string;
  startDate: string;
  endDate: string;
  onSelectionChange?: (selectedIds: string[]) => void;
}

export function AddonDiscoveredSection({
  resourceId,
  startDate,
  endDate,
  onSelectionChange,
}: AddonDiscoveredSectionProps) {
  const { discoverAddons, loading } = useAddons();
  const [addonGroups, setAddonGroups] = useState<Record<string, AddonTypeGroup>>({});
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!startDate || !endDate) return;
    const fullStart = new Date(startDate).toISOString();
    const fullEnd = new Date(endDate).toISOString();
    discoverAddons(resourceId, fullStart, fullEnd).then(setAddonGroups);
  }, [resourceId, startDate, endDate, discoverAddons]);

  const toggleAddon = useCallback(
    (addonId: string) => {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        if (next.has(addonId)) {
          next.delete(addonId);
        } else {
          next.add(addonId);
        }
        onSelectionChange?.(Array.from(next));
        return next;
      });
    },
    [onSelectionChange],
  );

  const groups = Object.values(addonGroups);

  if (loading && groups.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (groups.length === 0) return null;

  return (
    <div className="space-y-4">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        <Package className="h-5 w-5" />
        Available Addons
      </h2>

      {groups.map((group) => (
        <div key={group.type_slug} className="space-y-2">
          <h3 className="text-sm font-medium text-muted-foreground">{group.type_name}</h3>
          <div className="space-y-2">
            {group.resources.map((addon) => (
              <AddonResourceCard
                key={addon.id}
                addon={addon}
                isSelected={selectedIds.has(addon.id)}
                onToggle={() => toggleAddon(addon.id)}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
