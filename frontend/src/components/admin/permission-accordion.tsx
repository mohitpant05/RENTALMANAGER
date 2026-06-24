"use client";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import type { PermissionGroup } from "@/types/api";

const MANAGE_SUPERSETS: Record<string, string[]> = {
  "bookings:*:manage": [
    "bookings:*:confirm",
    "bookings:*:reject",
    "bookings:*:cancel",
    "bookings:*:no_show",
  ],
};

interface PermissionAccordionProps {
  groups: PermissionGroup[];
  selectedPermIds: Set<string>;
  onToggle: (permId: string) => void;
  onBulkToggle?: (permIds: string[], enabled: boolean) => void;
  disabled?: boolean;
}

export function PermissionAccordion({
  groups,
  selectedPermIds,
  onToggle,
  onBulkToggle,
  disabled = false,
}: PermissionAccordionProps) {
  // Build a map of codename → id for selected permissions
  const selectedCodenames = new Map<string, string>();
  for (const g of groups) {
    for (const p of g.permissions) {
      if (selectedPermIds.has(p.id)) {
        selectedCodenames.set(p.codename, p.id);
      }
    }
  }

  function isImpliedBySuperset(codename: string): boolean {
    for (const [superset, subs] of Object.entries(MANAGE_SUPERSETS)) {
      if (subs.includes(codename) && selectedCodenames.has(superset)) {
        return true;
      }
    }
    return false;
  }

  return (
    <Accordion
      multiple
      defaultValue={groups.map((g) => g.domain)}
      className="space-y-2"
    >
      {groups.map((group) => {
        const enabledCount = group.permissions.filter(
          (p) => selectedPermIds.has(p.id) || isImpliedBySuperset(p.codename)
        ).length;
        const allEnabled = enabledCount === group.permissions.length;
        const groupPermIds = group.permissions.map((p) => p.id);

        return (
          <AccordionItem
            key={group.domain}
            value={group.domain}
            className="border rounded-lg"
          >
            <div className="flex items-center px-4 py-3">
              <AccordionTrigger className="hover:no-underline flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm">{group.label}</span>
                  <Badge variant="secondary" className="text-[10px]">
                    {enabledCount}/{group.permissions.length}
                  </Badge>
                </div>
              </AccordionTrigger>
              {onBulkToggle && (
                <Switch
                  checked={allEnabled}
                  onCheckedChange={(checked) =>
                    onBulkToggle(groupPermIds, !!checked)
                  }
                  disabled={disabled}
                />
              )}
            </div>
            <AccordionContent className="px-4 pb-4">
              <div className="space-y-3">
                {group.permissions.map((perm) => {
                  const implied = isImpliedBySuperset(perm.codename);
                  const checked = selectedPermIds.has(perm.id) || implied;
                  return (
                    <div
                      key={perm.id}
                      className="flex items-center justify-between"
                    >
                      <div>
                        <p className="text-sm font-medium">
                          {perm.description || perm.codename}
                        </p>
                        <p className="text-xs text-muted-foreground font-mono">
                          {perm.codename}
                        </p>
                      </div>
                      <Switch
                        checked={checked}
                        onCheckedChange={() => onToggle(perm.id)}
                        disabled={disabled || implied}
                      />
                    </div>
                  );
                })}
              </div>
            </AccordionContent>
          </AccordionItem>
        );
      })}
    </Accordion>
  );
}
