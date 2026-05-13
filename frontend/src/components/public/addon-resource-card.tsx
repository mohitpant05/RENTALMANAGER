"use client";

import { Check, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AddonResourceItem } from "@/types/api";

interface AddonResourceCardProps {
  addon: AddonResourceItem;
  isSelected: boolean;
  onToggle: () => void;
}

export function AddonResourceCard({ addon, isSelected, onToggle }: AddonResourceCardProps) {
  return (
    <Card size="sm" className="relative">
      <CardContent className="flex items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-medium">{addon.name}</p>
            {addon.is_assigned && (
              <Badge variant="outline" className="text-[10px]">Recommended</Badge>
            )}
          </div>
          <div className="mt-0.5 flex items-center gap-3 text-xs text-muted-foreground">
            <span>₹{addon.base_price.toLocaleString()}</span>
            {addon.distance_km !== null && (
              <span>{addon.distance_km.toFixed(1)} km</span>
            )}
            {addon.rating_count > 0 && (
              <span>★ {addon.rating_avg.toFixed(1)}</span>
            )}
          </div>
          {!addon.available && (
            <p className="mt-0.5 text-xs text-destructive">Not available for selected dates</p>
          )}
        </div>
        <Button
          variant={isSelected ? "default" : "outline"}
          size="sm"
          onClick={onToggle}
          disabled={!addon.available}
          aria-label={isSelected ? "Remove addon" : "Add addon"}
        >
          {isSelected ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
        </Button>
      </CardContent>
    </Card>
  );
}
