# Resource Management Frontend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the resource management CRUD UI — fix attribute bugs, add missing pages, wire up edit flows.

**Architecture:** Five focused tasks that fix existing bugs then add missing features. Each task produces a working commit. All components follow established patterns: react-hook-form + zod for forms, react-query for data, shadcn/ui Sheet for modals, sonner for toasts.

**Tech Stack:** Next.js 15, TypeScript, React Query v5, react-hook-form, Zod, shadcn/ui, Zustand, Tailwind CSS

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `frontend/src/components/resources/create-resource-sheet.tsx` | Fix attribute binding: tags input, required validation |
| Modify | `frontend/src/types/api.ts` | Add `ResourceTypeUpdate` interface |
| Modify | `frontend/src/components/resources/create-type-sheet.tsx` | Support edit mode with `editingType` prop |
| Create | `frontend/src/lib/create-type-sheet-store.ts` | Tiny zustand store for sheet open state |
| Modify | `frontend/src/components/shell/sub-nav.tsx` | Use store for "+ Add Type" button |
| Create | `frontend/src/app/(admin)/resources/[typeSlug]/[resourceId]/page.tsx` | Resource detail page |
| Modify | `frontend/src/app/(admin)/resources/[typeSlug]/page.tsx` | Add edit-type button, render CreateTypeSheet from store |
| Modify | `frontend/src/app/(admin)/resources/page.tsx` | Render CreateTypeSheet from store |

---

### Task 1: Fix Custom Attribute Handling in Resource Form

**Files:**
- Modify: `frontend/src/components/resources/create-resource-sheet.tsx`

The attributes use `useState` and get merged into the mutation payload — they DO submit. But two bugs: (1) `tags` type falls through to text input producing a string instead of `string[]`, (2) required attributes aren't validated before submit.

- [ ] **Step 1: Add tags input rendering**

In `create-resource-sheet.tsx`, add a case for `tags` type between the `number` and fallback `text` cases. Tags use comma-separated input that gets split into an array.

Replace the attribute rendering block (lines 200-261) with this updated version that adds tags handling:

```tsx
{attributeSchema && attributeSchema.length > 0 && (
  <div className="space-y-3 rounded-lg border p-4">
    <p className="text-sm font-medium text-muted-foreground">
      Custom Attributes
    </p>
    {attributeSchema.map((attr) => (
      <div key={attr.name} className="space-y-1">
        <Label className="text-xs capitalize">
          {attr.name.replace(/_/g, " ")}
          {attr.required && (
            <span className="text-destructive"> *</span>
          )}
        </Label>
        {attr.type === "enum" && attr.options ? (
          <select
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            value={(getAttributeValue(attr) as string) ?? ""}
            onChange={(e) =>
              handleAttributeChange(attr.name, e.target.value)
            }
          >
            <option value="">Select...</option>
            {attr.options.map((opt) => (
              <option key={opt} value={opt}>
                {opt.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        ) : attr.type === "boolean" ? (
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-input"
            checked={(getAttributeValue(attr) as boolean) ?? false}
            onChange={(e) =>
              handleAttributeChange(attr.name, e.target.checked)
            }
          />
        ) : attr.type === "number" ? (
          <Input
            type="number"
            placeholder="0"
            value={(getAttributeValue(attr) as number) ?? ""}
            onChange={(e) =>
              handleAttributeChange(
                attr.name,
                e.target.value ? parseFloat(e.target.value) : undefined
              )
            }
          />
        ) : attr.type === "tags" ? (
          <Input
            placeholder="tag1, tag2, tag3"
            value={
              Array.isArray(getAttributeValue(attr))
                ? (getAttributeValue(attr) as string[]).join(", ")
                : (getAttributeValue(attr) as string) ?? ""
            }
            onChange={(e) =>
              handleAttributeChange(
                attr.name,
                e.target.value
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean)
              )
            }
          />
        ) : (
          <Input
            placeholder={attr.name.replace(/_/g, " ")}
            value={(getAttributeValue(attr) as string) ?? ""}
            onChange={(e) =>
              handleAttributeChange(attr.name, e.target.value)
            }
          />
        )}
        {attrErrors[attr.name] && (
          <p className="text-sm text-destructive">{attrErrors[attr.name]}</p>
        )}
      </div>
    ))}
  </div>
)}
```

- [ ] **Step 2: Add required attribute validation**

Add `attrErrors` state and a validation function that runs before form submit. Add this state and function near the existing state declarations:

```tsx
const [attrErrors, setAttrErrors] = useState<Record<string, string>>({});

function validateAttributes(): boolean {
  if (!attributeSchema) return true;
  const errors: Record<string, string> = {};
  for (const attr of attributeSchema) {
    if (!attr.required) continue;
    const val = attributes[attr.name];
    if (val === undefined || val === null || val === "") {
      errors[attr.name] = `${attr.name.replace(/_/g, " ")} is required`;
    } else if (Array.isArray(val) && val.length === 0) {
      errors[attr.name] = `${attr.name.replace(/_/g, " ")} is required`;
    }
  }
  setAttrErrors(errors);
  return Object.keys(errors).length === 0;
}
```

Update the form's `onSubmit` to call validation:

```tsx
onSubmit={handleSubmit((d) => {
  if (!validateAttributes()) return;
  createMutation.mutate(d as ResourceForm);
})}
```

- [ ] **Step 3: Fix number attribute empty value**

Already handled in Step 1 — changed `""` to `undefined` in the number onChange handler so empty number fields don't send empty string to backend.

- [ ] **Step 4: Verify manually**

Run: `npm run dev` (frontend)
Test: Create a resource type from "Venues" template → Create a resource → fill custom attributes including tags (amenities) and required fields (property_type, bedrooms) → submit → verify attributes appear in the table/API response. Also verify submitting without required attributes shows error messages.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/resources/create-resource-sheet.tsx
git commit -m "fix(resources): bind tags attribute type and add required validation"
```

---

### Task 2: Add ResourceTypeUpdate Type + Edit Mode for Type Sheet

**Files:**
- Modify: `frontend/src/types/api.ts`
- Modify: `frontend/src/components/resources/create-type-sheet.tsx`

- [ ] **Step 1: Add ResourceTypeUpdate interface**

Add to `frontend/src/types/api.ts` after the `ResourceTypeCreate` interface:

```typescript
export interface ResourceTypeUpdate {
  name?: string;
  slug?: string;
  icon?: string;
  description?: string;
  attribute_schema?: AttributeField[];
  slot_config?: Record<string, unknown>;
  pricing_config?: Record<string, unknown>;
  cancellation_defaults?: Record<string, unknown>;
  requires_verification?: boolean;
  is_active?: boolean;
}
```

- [ ] **Step 2: Convert CreateTypeSheet to support edit mode**

Update `create-type-sheet.tsx` to accept an optional `editingType` prop and handle both create and update flows.

Change the props interface:

```tsx
interface CreateTypeSheetProps {
  open: boolean;
  onClose: () => void;
  editingType?: ResourceTypeResponse | null;
}
```

Update the component to accept `editingType`:

```tsx
export function CreateTypeSheet({ open, onClose, editingType }: CreateTypeSheetProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const isEditing = !!editingType;
```

Add `useEffect` to populate form when editing (after the `useForm` call):

```tsx
useEffect(() => {
  if (editingType) {
    reset({
      name: editingType.name,
      slug: editingType.slug,
      description: editingType.description ?? "",
      availability_model: editingType.availability_model as "date_range" | "time_slot" | "hourly",
      pricing_model: editingType.pricing_model as "fixed_per_day" | "fixed_per_slot" | "per_hour" | "tiered",
    });
  } else {
    reset({
      name: "",
      slug: "",
      description: "",
      availability_model: "date_range",
      pricing_model: "fixed_per_day",
    });
  }
}, [editingType, reset]);
```

Add `reset` to the `useForm` destructuring.

Update the mutation to handle both create and update:

```tsx
const mutation = useMutation({
  mutationFn: async (data: TypeForm) => {
    if (isEditing) {
      const { data: res } = await api.put<ResourceTypeResponse>(
        `/resource-types/${editingType.id}`,
        data as ResourceTypeUpdate
      );
      return res;
    }
    const { data: res } = await api.post<ResourceTypeResponse>(
      "/resource-types",
      data as ResourceTypeCreate
    );
    return res;
  },
  onSuccess: (data) => {
    queryClient.invalidateQueries({ queryKey: ["resource-types"] });
    toast.success(isEditing ? `${data.name} updated` : `${data.name} created`);
    onClose();
    router.push(`/resources/${data.slug}`);
  },
  onError: () => {
    toast.error(isEditing ? "Failed to update" : "Failed to create resource type");
  },
});
```

Update SheetTitle/SheetDescription and submit button text to reflect edit vs create:

```tsx
<SheetTitle>{isEditing ? "Edit Type" : "Create Custom Type"}</SheetTitle>
<SheetDescription>
  {isEditing
    ? "Update this resource type's configuration"
    : "Define a new resource category for your business"}
</SheetDescription>
```

```tsx
{isSubmitting ? "Saving..." : isEditing ? "Update Type" : "Create Type"}
```

Disable availability_model and pricing_model selects when editing (changing these would break existing resources):

```tsx
<select
  id="availability_model"
  {...register("availability_model")}
  disabled={isEditing}
  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
>
```

Same `disabled={isEditing}` for pricing_model select.

- [ ] **Step 3: Add import for ResourceTypeUpdate**

In `create-type-sheet.tsx`, update the import:

```tsx
import type { ResourceTypeCreate, ResourceTypeResponse, ResourceTypeUpdate } from "@/types/api";
```

- [ ] **Step 4: Verify manually**

Test: Open edit sheet for an existing type → verify fields pre-populate → change name/description → submit → verify toast + type updates in sub-nav.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/components/resources/create-type-sheet.tsx
git commit -m "feat(resources): add edit mode to resource type sheet"
```

---

### Task 3: Fix SubNav "+ Add Type" Button

**Files:**
- Create: `frontend/src/lib/create-type-sheet-store.ts`
- Modify: `frontend/src/components/shell/sub-nav.tsx`
- Modify: `frontend/src/app/(admin)/resources/page.tsx`
- Modify: `frontend/src/app/(admin)/resources/[typeSlug]/page.tsx`

The current `+ Add Type` is a `<Link>` to `/resources/new-type` which doesn't exist. Solution: tiny Zustand store that SubNav and resource pages share.

- [ ] **Step 1: Create the store**

Create `frontend/src/lib/create-type-sheet-store.ts`:

```typescript
import { create } from "zustand";

interface CreateTypeSheetStore {
  open: boolean;
  setOpen: (open: boolean) => void;
}

export const useCreateTypeSheetStore = create<CreateTypeSheetStore>((set) => ({
  open: false,
  setOpen: (open) => set({ open }),
}));
```

- [ ] **Step 2: Update SubNav to use store**

In `sub-nav.tsx`, replace the action `<Link>` with a `<button>` when the action triggers the store.

Change the `SubNavSection` interface to support onClick:

```tsx
interface SubNavSection {
  title: string;
  items: SubNavItem[];
  action?: { label: string; href?: string; onClick?: () => void };
}
```

Import and use the store in `useResourceTypesNav`:

```tsx
import { useCreateTypeSheetStore } from "@/lib/create-type-sheet-store";
```

Update `useResourceTypesNav` to use onClick:

```tsx
function useResourceTypesNav(): SubNavSection | null {
  const setOpen = useCreateTypeSheetStore((s) => s.setOpen);
  const { data: types } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types");
      return data;
    },
    staleTime: 30_000,
  });

  if (!types) return { title: "Resources", items: [], action: { label: "+ Add Type", onClick: () => setOpen(true) } };

  return {
    title: "Resources",
    items: types.map((t) => ({ href: `/resources/${t.slug}`, label: t.name })),
    action: { label: "+ Add Type", onClick: () => setOpen(true) },
  };
}
```

Update the action rendering at the bottom of SubNav's return:

```tsx
{config.action && (
  config.action.onClick ? (
    <button
      onClick={config.action.onClick}
      className="mt-4 text-sm text-primary hover:underline text-left"
    >
      {config.action.label}
    </button>
  ) : config.action.href ? (
    <Link
      href={config.action.href}
      className="mt-4 text-sm text-primary hover:underline"
    >
      {config.action.label}
    </Link>
  ) : null
)}
```

- [ ] **Step 3: Wire CreateTypeSheet in resource pages**

In `frontend/src/app/(admin)/resources/page.tsx`, import and use the store:

```tsx
import { useCreateTypeSheetStore } from "@/lib/create-type-sheet-store";
import { CreateTypeSheet } from "@/components/resources/create-type-sheet";
```

Inside the component:

```tsx
const { open: typeSheetFromNav, setOpen: setTypeSheetFromNav } = useCreateTypeSheetStore();
```

The page already has `showCustomSheet` state for the template picker's "Create custom" button. Merge both triggers:

```tsx
const typeSheetOpen = showCustomSheet || typeSheetFromNav;

function closeTypeSheet() {
  setShowCustomSheet(false);
  setTypeSheetFromNav(false);
}
```

Update the `CreateTypeSheet` render:

```tsx
<CreateTypeSheet
  open={typeSheetOpen}
  onClose={closeTypeSheet}
/>
```

In `frontend/src/app/(admin)/resources/[typeSlug]/page.tsx`, add the same store + sheet:

```tsx
import { useCreateTypeSheetStore } from "@/lib/create-type-sheet-store";
import { CreateTypeSheet } from "@/components/resources/create-type-sheet";
```

Inside the component:

```tsx
const { open: typeSheetOpen, setOpen: setTypeSheetOpen } = useCreateTypeSheetStore();
```

Add `CreateTypeSheet` at the bottom of the return JSX (after the existing `CreateResourceSheet`):

```tsx
<CreateTypeSheet
  open={typeSheetOpen}
  onClose={() => setTypeSheetOpen(false)}
/>
```

- [ ] **Step 4: Verify manually**

Test: Click "+ Add Type" in sub-nav from any resources page → sheet opens → create a type → sheet closes, nav updates. Test from both the empty state (template picker) page and a type detail page.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/create-type-sheet-store.ts frontend/src/components/shell/sub-nav.tsx frontend/src/app/\(admin\)/resources/page.tsx frontend/src/app/\(admin\)/resources/\[typeSlug\]/page.tsx
git commit -m "fix(resources): wire + Add Type button in sub-nav via zustand store"
```

---

### Task 4: Add Resource Detail Page

**Files:**
- Create: `frontend/src/app/(admin)/resources/[typeSlug]/[resourceId]/page.tsx`

- [ ] **Step 1: Create the detail page**

Create `frontend/src/app/(admin)/resources/[typeSlug]/[resourceId]/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Pencil, Trash2, MapPin, Star } from "lucide-react";
import Link from "next/link";
import api from "@/lib/api";
import type { ResourceResponse, ResourceTypeResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CreateResourceSheet } from "@/components/resources/create-resource-sheet";
import { toast } from "sonner";

const STATUS_VARIANT: Record<string, "muted" | "success" | "warning" | "destructive"> = {
  draft: "muted",
  active: "success",
  inactive: "warning",
  archived: "destructive",
};

export default function ResourceDetailPage() {
  const { typeSlug, resourceId } = useParams<{ typeSlug: string; resourceId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);

  const { data: types } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types");
      return data;
    },
    staleTime: 30_000,
  });

  const currentType = types?.find((t) => t.slug === typeSlug);

  const { data: resource, isLoading } = useQuery({
    queryKey: ["resource", resourceId],
    queryFn: async () => {
      const { data } = await api.get<ResourceResponse>(`/resources/${resourceId}`);
      return data;
    },
    enabled: !!resourceId,
  });

  const statusMutation = useMutation({
    mutationFn: async (status: string) => {
      const { data } = await api.put<ResourceResponse>(`/resources/${resourceId}`, { status });
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["resource", resourceId] });
      queryClient.invalidateQueries({ queryKey: ["resources", currentType?.id] });
      toast.success(`Status changed to ${data.status}`);
    },
    onError: () => {
      toast.error("Failed to update status");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      await api.delete(`/resources/${resourceId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resources", currentType?.id] });
      toast.success("Resource deleted");
      router.push(`/resources/${typeSlug}`);
    },
    onError: () => {
      toast.error("Failed to delete resource");
    },
  });

  if (isLoading || !resource || !currentType) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-6 p-6">
      <div className="flex items-center gap-3">
        <Link
          href={`/resources/${typeSlug}`}
          className="rounded-md p-1 hover:bg-accent"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold tracking-tight">{resource.name}</h1>
          {resource.description && (
            <p className="mt-1 text-sm text-muted-foreground">
              {resource.description}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setEditOpen(true)}>
            <Pencil className="mr-2 h-4 w-4" />
            Edit
          </Button>
          <Button
            variant="destructive"
            onClick={() => deleteMutation.mutate()}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-4 rounded-lg border p-6">
          <h2 className="text-sm font-semibold text-muted-foreground">Details</h2>

          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Status</span>
            <Select
              value={resource.status}
              onValueChange={(v) => statusMutation.mutate(v)}
            >
              <SelectTrigger className="w-[140px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="archived">Archived</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Price</span>
            <span className="font-medium">
              {resource.base_price.toFixed(2)} {resource.currency}
            </span>
          </div>

          {resource.rating_count > 0 && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Rating</span>
              <span className="flex items-center gap-1 font-medium">
                <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                {resource.rating_avg.toFixed(1)} ({resource.rating_count})
              </span>
            </div>
          )}

          {resource.location_address && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Location</span>
              <span className="flex items-center gap-1 text-sm">
                <MapPin className="h-4 w-4" />
                {resource.location_address}
              </span>
            </div>
          )}

          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Created</span>
            <span className="text-sm">
              {new Date(resource.created_at).toLocaleDateString()}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Version</span>
            <span className="text-sm">{resource.version}</span>
          </div>
        </div>

        {resource.attributes && Object.keys(resource.attributes).length > 0 && (
          <div className="space-y-4 rounded-lg border p-6">
            <h2 className="text-sm font-semibold text-muted-foreground">Attributes</h2>
            {Object.entries(resource.attributes).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-sm capitalize text-muted-foreground">
                  {key.replace(/_/g, " ")}
                </span>
                <span className="text-sm font-medium">
                  {Array.isArray(value) ? (
                    <span className="flex flex-wrap gap-1 justify-end">
                      {value.map((tag) => (
                        <Badge key={tag} variant="muted" className="text-xs">
                          {String(tag)}
                        </Badge>
                      ))}
                    </span>
                  ) : typeof value === "boolean" ? (
                    value ? "Yes" : "No"
                  ) : (
                    String(value)
                  )}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <CreateResourceSheet
        open={editOpen}
        onClose={() => setEditOpen(false)}
        typeId={currentType.id}
        typeName={currentType.name}
        attributeSchema={currentType.attribute_schema}
        editingResource={resource}
      />
    </div>
  );
}
```

- [ ] **Step 2: Verify manually**

Test: Click a resource name in the table → detail page loads → verify all fields display correctly → change status via dropdown → edit via button → delete navigates back to list.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(admin\)/resources/\[typeSlug\]/\[resourceId\]/page.tsx
git commit -m "feat(resources): add resource detail page with status change and edit"
```

---

### Task 5: Add Edit Type Button on Type Detail Page

**Files:**
- Modify: `frontend/src/app/(admin)/resources/[typeSlug]/page.tsx`

- [ ] **Step 1: Add edit type trigger**

In `[typeSlug]/page.tsx`, add state and UI for editing the resource type.

Add imports:

```tsx
import { Settings } from "lucide-react";
```

Add state:

```tsx
const [editTypeOpen, setEditTypeOpen] = useState(false);
```

Add an edit-type button next to the "Add {type}" button in the header:

```tsx
<div className="flex items-center gap-2">
  <Button variant="outline" onClick={() => setEditTypeOpen(true)}>
    <Settings className="mr-2 h-4 w-4" />
    Type Settings
  </Button>
  <Button onClick={openCreate}>
    <Plus className="mr-2 h-4 w-4" />
    Add {currentType.name.replace(/s$/, "")}
  </Button>
</div>
```

Update the `CreateTypeSheet` render (the one from Task 3) to pass `editingType`:

```tsx
<CreateTypeSheet
  open={typeSheetOpen || editTypeOpen}
  onClose={() => {
    setTypeSheetOpen(false);
    setEditTypeOpen(false);
  }}
  editingType={editTypeOpen ? currentType : null}
/>
```

- [ ] **Step 2: Verify manually**

Test: On a type page, click "Type Settings" → sheet opens with pre-populated fields → availability/pricing selects disabled → change name/description → submit → verify type updates.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(admin\)/resources/\[typeSlug\]/page.tsx
git commit -m "feat(resources): add type settings button with edit sheet"
```

---

## Verification Checklist

After all tasks, verify end-to-end:

- [ ] Create resource type from template → verify sub-nav updates
- [ ] Create resource type custom → verify sub-nav updates  
- [ ] Edit resource type name/description → verify sub-nav + page title update
- [ ] Create resource with required attributes → verify required validation blocks submit
- [ ] Create resource with tags attribute → verify tags save as array
- [ ] Click resource name → detail page shows all fields
- [ ] Change resource status on detail page → verify badge updates
- [ ] Edit resource from detail page → verify changes persist
- [ ] Delete resource from detail page → verify redirect to list
- [ ] Click "+ Add Type" from sub-nav on any resources page → sheet opens
