"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Loader2, Shield, MoreVertical, Trash2, UserCog, Power, KeyRound } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import api from "@/lib/api";
import type { StaffUserResponse, StaffInviteRequest, RoleResponse } from "@/types/api";
import { useAuthStore } from "@/lib/auth-store";
import { usePermissions } from "@/hooks/use-permissions";
import { PermissionOverrideEditor } from "@/components/admin/permission-override-editor";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";

const inviteSchema = z.object({
  email: z.string().email("Invalid email"),
  full_name: z.string().min(1, "Name is required"),
  user_type: z.enum(["staff", "admin"]),
});

type InviteFormData = z.infer<typeof inviteSchema>;

export default function StaffPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const currentUser = useAuthStore((s) => s.user);
  const { hasPermission, isLoading: permsLoading } = usePermissions();
  const isAdmin = currentUser?.user_type === "admin";

  if (permsLoading) return <div className="flex flex-1 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" /></div>;
  if (!hasPermission("staff:*:manage") && !hasPermission("staff:*:invite")) { router.replace("/admin"); return null; }
  const [sheetOpen, setSheetOpen] = useState(false);
  const [selectedRoleSlugs, setSelectedRoleSlugs] = useState<string[]>([]);
  const [editRolesUserId, setEditRolesUserId] = useState<string | null>(null);
  const [editRoleIds, setEditRoleIds] = useState<string[]>([]);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [resetPasswordUserId, setResetPasswordUserId] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<InviteFormData>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { user_type: "staff" },
  });

  const { data: staff, isLoading } = useQuery({
    queryKey: ["admin-staff"],
    queryFn: async () => {
      const { data } = await api.get<StaffUserResponse[]>("/admin/staff");
      return data;
    },
  });

  const { data: roles = [] } = useQuery({
    queryKey: ["admin-roles"],
    queryFn: async () => {
      const { data } = await api.get<RoleResponse[]>("/admin/roles");
      return data;
    },
  });

  const currentUserRoleSlugs = staff?.find((s) => s.id === currentUser?.id)?.roles ?? [];

  const assignableRoles = roles.filter((r) => {
    if (r.slug === "admin" || r.slug === "customer") return false;
    if (!isAdmin && !currentUserRoleSlugs.includes(r.slug)) return false;
    return true;
  });

  const inviteMutation = useMutation({
    mutationFn: async (data: StaffInviteRequest) => {
      const { data: result } = await api.post<
        StaffUserResponse & { email_status?: string; email_warning?: string }
      >("/admin/staff", data);
      return result;
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["admin-staff"] });
      if (result.email_status === "not_configured") {
        toast.warning(
          result.email_warning ||
            "Staff created but invite email was not sent — no email provider configured."
        );
      } else {
        toast.success("Staff invited — invite email queued");
      }
      setSheetOpen(false);
      setSelectedRoleSlugs([]);
      reset();
    },
    onError: () => {
      toast.error("Failed to invite staff");
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: async (userId: string) => {
      const { data } = await api.post<StaffUserResponse>(
        `/admin/staff/${userId}/deactivate`
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-staff"] });
      toast.success("Staff deactivated");
    },
    onError: () => {
      toast.error("Failed to deactivate");
    },
  });

  const activateMutation = useMutation({
    mutationFn: async (userId: string) => {
      await api.post(`/admin/staff/${userId}/activate`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-staff"] });
      toast.success("Staff activated");
    },
    onError: () => {
      toast.error("Failed to activate");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (userId: string) => {
      await api.delete(`/admin/staff/${userId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-staff"] });
      setDeleteConfirmId(null);
      toast.success("Staff deleted");
    },
    onError: () => {
      toast.error("Failed to delete staff");
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: async ({ userId, password }: { userId: string; password: string }) => {
      await api.post(`/admin/staff/${userId}/reset-password`, { new_password: password });
    },
    onSuccess: () => {
      setResetPasswordUserId(null);
      setNewPassword("");
      toast.success("Password reset");
    },
    onError: () => {
      toast.error("Failed to reset password");
    },
  });

  const updateRolesMutation = useMutation({
    mutationFn: async ({
      userId,
      roleIds,
    }: {
      userId: string;
      roleIds: string[];
    }) => {
      await api.patch(`/admin/staff/${userId}/roles`, { role_ids: roleIds });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-staff"] });
      setEditRolesUserId(null);
      toast.success("Roles updated");
    },
    onError: () => {
      toast.error("Failed to update roles");
    },
  });

  function onSubmit(data: InviteFormData) {
    inviteMutation.mutate({
      ...data,
      role_slugs: selectedRoleSlugs.length > 0 ? selectedRoleSlugs : undefined,
    });
  }

  function openEditRoles(staffUser: StaffUserResponse) {
    const currentIds = roles
      .filter((r) => staffUser.roles.includes(r.slug))
      .map((r) => r.id);
    setEditRoleIds(currentIds);
    setEditRolesUserId(staffUser.id);
  }

  function toggleRoleId(id: string) {
    setEditRoleIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }

  function toggleRoleSlug(slug: string) {
    setSelectedRoleSlugs((prev) =>
      prev.includes(slug) ? prev.filter((x) => x !== slug) : [...prev, slug]
    );
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Staff</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage team members and roles
          </p>
        </div>
        <Button onClick={() => setSheetOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Invite Staff
        </Button>
      </div>

      <div className="space-y-3">
        {staff?.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
            <Shield className="h-12 w-12 text-muted-foreground" />
            <p className="mt-3 text-muted-foreground">No staff members yet</p>
          </div>
        )}

        {staff?.map((s) => (
          <Card key={s.id}>
            <CardContent className="flex items-center justify-between p-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{s.full_name}</span>
                  <Badge
                    variant={
                      s.user_type === "admin" ? "default" : "secondary"
                    }
                  >
                    {s.user_type}
                  </Badge>
                  {!s.is_active && (
                    <Badge variant="destructive">Inactive</Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">{s.email}</p>
                {s.roles.length > 0 && (
                  <div className="flex gap-1 flex-wrap">
                    {s.roles.map((role) => (
                      <Badge key={role} variant="outline" className="text-xs">
                        {role}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button size="icon" variant="ghost" className="h-8 w-8">
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {s.user_type !== "admin" && (
                    <DropdownMenuItem onClick={() => openEditRoles(s)}>
                      <UserCog className="mr-2 h-4 w-4" />
                      Manage Roles
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuItem onClick={() => setResetPasswordUserId(s.id)}>
                    <KeyRound className="mr-2 h-4 w-4" />
                    Reset Password
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  {s.is_active ? (
                    <DropdownMenuItem
                      onClick={() => deactivateMutation.mutate(s.id)}
                      className="text-orange-600"
                    >
                      <Power className="mr-2 h-4 w-4" />
                      Deactivate
                    </DropdownMenuItem>
                  ) : (
                    <DropdownMenuItem onClick={() => activateMutation.mutate(s.id)}>
                      <Power className="mr-2 h-4 w-4" />
                      Activate
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuItem
                    onClick={() => setDeleteConfirmId(s.id)}
                    className="text-destructive"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Invite Sheet */}
      <Sheet
        open={sheetOpen}
        onOpenChange={(o) => {
          setSheetOpen(o);
          if (!o) {
            reset();
            setSelectedRoleSlugs([]);
          }
        }}
      >
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Invite Staff</SheetTitle>
            <SheetDescription>
              Send an invitation to join your team
            </SheetDescription>
          </SheetHeader>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 px-4">
            <div className="space-y-2">
              <Label htmlFor="full_name">Full Name</Label>
              <Input id="full_name" {...register("full_name")} />
              {errors.full_name && (
                <p className="text-xs text-destructive">
                  {errors.full_name.message}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" {...register("email")} />
              {errors.email && (
                <p className="text-xs text-destructive">
                  {errors.email.message}
                </p>
              )}
            </div>

            {isAdmin && (
              <div className="space-y-2">
                <Label htmlFor="user_type">Type</Label>
                <Select
                  onValueChange={(v) =>
                    register("user_type").onChange({ target: { value: v } })
                  }
                  defaultValue="staff"
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="staff">Staff</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            {assignableRoles.length > 0 && (
              <div className="space-y-2">
                <Label>Roles</Label>
                <div className="space-y-2 rounded-md border p-3">
                  {assignableRoles.map((role) => (
                    <label
                      key={role.slug}
                      className="flex items-center gap-2 text-sm cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={selectedRoleSlugs.includes(role.slug)}
                        onChange={() => toggleRoleSlug(role.slug)}
                        className="rounded"
                      />
                      <span>{role.name}</span>
                      {role.description && (
                        <span className="text-xs text-muted-foreground">
                          — {role.description}
                        </span>
                      )}
                    </label>
                  ))}
                </div>
              </div>
            )}

            <SheetFooter>
              <Button type="submit" disabled={inviteMutation.isPending}>
                {inviteMutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Send Invite
              </Button>
            </SheetFooter>
          </form>
        </SheetContent>
      </Sheet>

      {/* Edit Roles Sheet */}
      <Sheet
        open={!!editRolesUserId}
        onOpenChange={(o) => {
          if (!o) setEditRolesUserId(null);
        }}
      >
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Edit Roles</SheetTitle>
            <SheetDescription>
              {staff?.find((s) => s.id === editRolesUserId)?.full_name}
            </SheetDescription>
          </SheetHeader>

          <div className="space-y-2 p-4">
            {assignableRoles.map((role) => (
              <label
                key={role.id}
                className="flex items-center gap-2 text-sm cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={editRoleIds.includes(role.id)}
                  onChange={() => toggleRoleId(role.id)}
                  className="rounded"
                />
                <span>{role.name}</span>
                {role.description && (
                  <span className="text-xs text-muted-foreground">
                    — {role.description}
                  </span>
                )}
              </label>
            ))}
          </div>

          {editRolesUserId && (
            <div className="mt-6 border-t pt-4 px-4">
              <PermissionOverrideEditor userId={editRolesUserId} />
            </div>
          )}

          <SheetFooter className="px-4">
            <Button
              onClick={() =>
                editRolesUserId &&
                updateRolesMutation.mutate({
                  userId: editRolesUserId,
                  roleIds: editRoleIds,
                })
              }
              disabled={updateRolesMutation.isPending}
            >
              {updateRolesMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Save Roles
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Reset Password Sheet */}
      <Sheet
        open={!!resetPasswordUserId}
        onOpenChange={(o) => {
          if (!o) {
            setResetPasswordUserId(null);
            setNewPassword("");
          }
        }}
      >
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Reset Password</SheetTitle>
            <SheetDescription>
              {staff?.find((s) => s.id === resetPasswordUserId)?.full_name}
            </SheetDescription>
          </SheetHeader>

          <div className="space-y-4 p-4">
            <div className="space-y-2">
              <Label htmlFor="new_password">New Password</Label>
              <Input
                id="new_password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new password"
              />
            </div>
          </div>

          <SheetFooter className="px-4">
            <Button
              onClick={() =>
                resetPasswordUserId &&
                resetPasswordMutation.mutate({
                  userId: resetPasswordUserId,
                  password: newPassword,
                })
              }
              disabled={resetPasswordMutation.isPending || newPassword.length < 8}
            >
              {resetPasswordMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Reset Password
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Delete Confirmation Sheet */}
      <Sheet
        open={!!deleteConfirmId}
        onOpenChange={(o) => {
          if (!o) setDeleteConfirmId(null);
        }}
      >
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Delete Staff Member</SheetTitle>
            <SheetDescription>
              Are you sure you want to permanently delete{" "}
              <span className="font-semibold">
                {staff?.find((s) => s.id === deleteConfirmId)?.full_name}
              </span>
              ? This will remove their account, roles, and suspend any resources they own.
              This action cannot be undone.
            </SheetDescription>
          </SheetHeader>

          <SheetFooter className="px-4 pt-6">
            <Button
              variant="ghost"
              onClick={() => setDeleteConfirmId(null)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteConfirmId && deleteMutation.mutate(deleteConfirmId)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Delete Permanently
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  );
}
