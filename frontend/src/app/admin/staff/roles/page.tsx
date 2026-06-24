"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import api from "@/lib/api";
import type {
  PermissionGroup,
  RoleCreate,
  RoleResponse,
} from "@/types/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Trash2, Plus, Shield } from "lucide-react";
import { PermissionAccordion } from "@/components/admin/permission-accordion";

const roleSchema = z.object({
  name: z.string().min(1, "Required"),
  slug: z
    .string()
    .min(1, "Required")
    .regex(/^[a-z0-9_-]+$/, "Lowercase letters, numbers, hyphens, underscores"),
  description: z.string().optional(),
});

type RoleFormValues = z.infer<typeof roleSchema>;

export default function RolesPage() {
  const qc = useQueryClient();
  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const { data: roles = [] } = useQuery({
    queryKey: ["admin-roles"],
    queryFn: async () => {
      const { data } = await api.get<RoleResponse[]>("/admin/roles");
      return data;
    },
  });

  const { data: permissionGroups = [] } = useQuery({
    queryKey: ["admin-permissions"],
    queryFn: async () => {
      const { data } = await api.get<PermissionGroup[]>("/admin/permissions");
      return data;
    },
  });

  const selectedRole = roles.find((r) => r.id === selectedRoleId) ?? null;
  const selectedPermIds = new Set(
    selectedRole?.permissions.map((p) => p.id) ?? []
  );

  const form = useForm<RoleFormValues>({
    resolver: zodResolver(roleSchema),
    defaultValues: { name: "", slug: "", description: "" },
  });

  const createMutation = useMutation({
    mutationFn: async (data: RoleCreate) => {
      const { data: role } = await api.post<RoleResponse>("/admin/roles", data);
      return role;
    },
    onSuccess: (role) => {
      qc.invalidateQueries({ queryKey: ["admin-roles"] });
      setSelectedRoleId(role.id);
      setSheetOpen(false);
      form.reset();
      toast.success("Role created");
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Failed to create role";
      toast.error(detail);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (roleId: string) => {
      await api.delete(`/admin/roles/${roleId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-roles"] });
      setSelectedRoleId(null);
      toast.success("Role deleted");
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Failed to delete role";
      toast.error(detail);
    },
  });

  const permMutation = useMutation({
    mutationFn: async ({
      roleId,
      permissionIds,
    }: {
      roleId: string;
      permissionIds: string[];
    }) => {
      const { data } = await api.put<RoleResponse>(
        `/admin/roles/${roleId}/permissions`,
        { permission_ids: permissionIds }
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-roles"] });
      toast.success("Permissions updated");
    },
  });

  function togglePermission(permId: string) {
    if (!selectedRole) return;
    const current = new Set(selectedRole.permissions.map((p) => p.id));
    if (current.has(permId)) {
      current.delete(permId);
    } else {
      current.add(permId);
    }
    permMutation.mutate({
      roleId: selectedRole.id,
      permissionIds: Array.from(current),
    });
  }

  function bulkTogglePermissions(permIds: string[], enabled: boolean) {
    if (!selectedRole) return;
    const current = new Set(selectedRole.permissions.map((p) => p.id));
    for (const id of permIds) {
      if (enabled) {
        current.add(id);
      } else {
        current.delete(id);
      }
    }
    permMutation.mutate({
      roleId: selectedRole.id,
      permissionIds: Array.from(current),
    });
  }

  function onSubmit(values: RoleFormValues) {
    createMutation.mutate(values);
  }

  const nameValue = form.watch("name");
  const autoSlug = nameValue
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

  return (
    <div className="flex h-full">
      {/* Role list */}
      <div className="w-[280px] border-r flex flex-col">
        <div className="p-4 border-b flex items-center justify-between">
          <h2 className="font-semibold text-sm">Roles</h2>
          <Button size="sm" variant="outline" onClick={() => setSheetOpen(true)}>
            <Plus className="h-4 w-4 mr-1" /> New
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {roles.map((role) => (
            <button
              key={role.id}
              onClick={() => setSelectedRoleId(role.id)}
              className={`w-full text-left p-3 border-b hover:bg-accent/50 transition-colors ${
                selectedRoleId === role.id ? "bg-accent" : ""
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{role.name}</span>
                {role.is_system && (
                  <Badge variant="secondary" className="text-[10px] px-1.5">
                    System
                  </Badge>
                )}
              </div>
              {role.description && (
                <p className="text-xs text-muted-foreground mt-0.5 truncate">
                  {role.description}
                </p>
              )}
              <p className="text-xs text-muted-foreground mt-1">
                {role.permissions.length} permissions
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Permission grid */}
      <div className="flex-1 overflow-y-auto">
        {selectedRole ? (
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  {selectedRole.name}
                </h2>
                {selectedRole.description && (
                  <p className="text-sm text-muted-foreground mt-1">
                    {selectedRole.description}
                  </p>
                )}
              </div>
              {!selectedRole.is_system && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => deleteMutation.mutate(selectedRole.id)}
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 className="h-4 w-4 mr-1" /> Delete
                </Button>
              )}
            </div>

            <PermissionAccordion
              groups={permissionGroups}
              selectedPermIds={selectedPermIds}
              onToggle={togglePermission}
              onBulkToggle={bulkTogglePermissions}
              disabled={permMutation.isPending}
            />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            Select a role to manage permissions
          </div>
        )}
      </div>

      {/* Create role sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Create Role</SheetTitle>
          </SheetHeader>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="mt-6 space-y-4"
          >
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                {...form.register("name", {
                  onChange: () => {
                    if (!form.getFieldState("slug").isDirty) {
                      form.setValue("slug", autoSlug);
                    }
                  },
                })}
                placeholder="Resource Manager"
              />
              {form.formState.errors.name && (
                <p className="text-xs text-destructive">
                  {form.formState.errors.name.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="slug">Slug</Label>
              <Input
                id="slug"
                {...form.register("slug")}
                placeholder="resource-manager"
              />
              {form.formState.errors.slug && (
                <p className="text-xs text-destructive">
                  {form.formState.errors.slug.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                {...form.register("description")}
                placeholder="Manages resources and availability"
                rows={3}
              />
            </div>
            <Button
              type="submit"
              className="w-full"
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? "Creating..." : "Create Role"}
            </Button>
          </form>
        </SheetContent>
      </Sheet>
    </div>
  );
}
