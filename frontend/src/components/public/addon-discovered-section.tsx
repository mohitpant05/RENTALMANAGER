"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Loader2, Package } from "lucide-react";
import { useAddons } from "@/hooks/use-addons";
import { AddonResourceCard } from "@/components/public/addon-resource-card";
import { AddonSchedulePicker } from "@/components/public/addon-schedule-picker";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { AddonSchedule, AddonTypeGroup } from "@/types/api";

export interface ItemSelection {
  schedules: AddonSchedule[];
  availabilityModel: string;
}

export type AddonSelections = Record<string, ItemSelection>;

interface AddonDiscoveredSectionProps {
  resourceId: string;
  startDate: string;
  endDate: string;
  onSelectionChange?: (selections: AddonSelections) => void;
}

export function AddonDiscoveredSection({
  resourceId,
  startDate,
  endDate,
  onSelectionChange,
}: AddonDiscoveredSectionProps) {
  const { discoverAddons, loading } = useAddons();
  const [addonGroups, setAddonGroups] = useState<Record<string, AddonTypeGroup>>({});
  const [activeTypeSlug, setActiveTypeSlug] = useState<string | null>(null);
  const [expandedResources, setExpandedResources] = useState<Set<string>>(new Set());
  const [scheduleMap, setScheduleMap] = useState<AddonSelections>({});
  const resourceModels = useRef<Record<string, string>>({});

  useEffect(() => {
    if (!startDate || !endDate) return;
    const fullStart = new Date(startDate).toISOString();
    const fullEnd = new Date(endDate).toISOString();
    discoverAddons(resourceId, fullStart, fullEnd).then((groups) => {
      setAddonGroups(groups);
      const slugs = Object.keys(groups);
      if (slugs.length > 0 && !activeTypeSlug) {
        setActiveTypeSlug(slugs[0]);
      }
    });
  }, [resourceId, startDate, endDate, discoverAddons]);

  const groupSlugs = useMemo(() => Object.keys(addonGroups), [addonGroups]);
  const showDropdown = groupSlugs.length > 3;
  const activeGroup = activeTypeSlug ? addonGroups[activeTypeSlug] : null;
  const visibleGroups = showDropdown
    ? (activeGroup ? [activeGroup] : [])
    : Object.values(addonGroups);

  const toggleResource = useCallback(
    (addonId: string) => {
      setExpandedResources((prev) => {
        const next = new Set(prev);
        if (next.has(addonId)) {
          next.delete(addonId);
          setScheduleMap((m) => {
            const updated = { ...m };
            delete updated[addonId];
            return updated;
          });
        } else {
          next.add(addonId);
        }
        return next;
      });
    },
    [],
  );

  const handleScheduleChange = useCallback(
    (resourceId: string, schedules: AddonSchedule[], model: string) => {
      resourceModels.current[resourceId] = model;
      setScheduleMap((prev) => {
        const next = { ...prev };
        if (schedules.length > 0) {
          next[resourceId] = { schedules, availabilityModel: model };
        } else {
          delete next[resourceId];
        }
        return next;
      });
    },
    [],
  );

  useEffect(() => {
    onSelectionChange?.(scheduleMap);
  }, [scheduleMap, onSelectionChange]);

  const totalSchedules = useMemo(
    () => Object.values(scheduleMap).reduce((sum, s) => sum + s.schedules.length, 0),
    [scheduleMap],
  );

  if (loading && Object.keys(addonGroups).length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (groupSlugs.length === 0) return null;

  return (
    <div className="space-y-4">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        <Package className="h-5 w-5" />
        Available Addons
      </h2>

      {showDropdown && (
        <Select value={activeTypeSlug ?? ""} onValueChange={setActiveTypeSlug}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Select addon type" />
          </SelectTrigger>
          <SelectContent>
            {groupSlugs.map((slug) => {
              const g = addonGroups[slug];
              return (
                <SelectItem key={slug} value={slug}>
                  {g.type_name} ({g.resources.length})
                </SelectItem>
              );
            })}
          </SelectContent>
        </Select>
      )}

      {visibleGroups.map((group) => (
        <div key={group.type_slug} className="space-y-2">
          {!showDropdown && (
            <h3 className="text-sm font-medium text-muted-foreground">
              {group.type_name} ({group.resources.length})
            </h3>
          )}

          <div className="space-y-2">
            {group.resources.map((addon) => {
              const isExpanded = expandedResources.has(addon.id);
              const schedules = scheduleMap[addon.id]?.schedules ?? [];

              return (
                <div key={addon.id} className="space-y-2">
                  <AddonResourceCard
                    addon={addon}
                    isSelected={isExpanded}
                    onToggle={() => toggleResource(addon.id)}
                  />

                  {isExpanded && (
                    <div className="ml-4 rounded-lg border bg-muted/30 p-3">
                      <AddonSchedulePicker
                        availabilityModel={group.availability_model}
                        slotConfig={addon.slot_config ?? group.slot_config}
                        startDate={startDate}
                        endDate={endDate}
                        basePrice={addon.base_price}
                        pricingModel={group.pricing_model}
                        schedules={schedules}
                        onChange={(s) => handleScheduleChange(addon.id, s, group.availability_model)}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {totalSchedules > 0 && (
        <div className="rounded-lg border bg-primary/5 p-3 text-sm">
          <div className="flex items-center gap-2 font-medium">
            <Package className="h-4 w-4" />
            {totalSchedules} add-on item{totalSchedules > 1 ? "s" : ""} selected
          </div>
        </div>
      )}
    </div>
  );
}
