"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Loader2, Shield, Trash2, X } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import api from "@/lib/api";
import type { StaffUserResponse, StaffInviteRequest } from "@/types/api";
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
import { toast } from "sonner";

const inviteSchema = z.object({
  email: z.string().email("Invalid email"),
  full_name: z.string().min(1, "Name is required"),
  user_type: z.enum(["staff", "admin"]),
});

type InviteFormData = z.infer<typeof inviteSchema>;

export default function StaffPage() {
  const queryClient = useQueryClient();
  const [sheetOpen, setSheetOpen] = useState(false);

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

  const inviteMutation = useMutation({
    mutationFn: async (data: StaffInviteRequest) => {
      const { data: result } = await api.post<StaffUserResponse>("/admin/staff", data);
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-staff"] });
      toast.success("Staff invited successfully");
      setSheetOpen(false);
      reset();
    },
    onError: () => {
      toast.error("Failed to invite staff");
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: async (userId: string) => {
      const { data } = await api.post<StaffUserResponse>(`/admin/staff/${userId}/deactivate`);
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

  function onSubmit(data: InviteFormData) {
    inviteMutation.mutate(data);
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
          <p className="mt-1 text-sm text-muted-foreground">Manage team members and roles</p>
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
                  <Badge variant={s.user_type === "admin" ? "default" : "secondary"}>
                    {s.user_type}
                  </Badge>
                  {!s.is_active && (
                    <Badge variant="destructive">Inactive</Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">{s.email}</p>
                {s.roles.length > 0 && (
                  <div className="flex gap-1">
                    {s.roles.map((role) => (
                      <Badge key={role} variant="muted" className="text-xs">{role}</Badge>
                    ))}
                  </div>
                )}
              </div>

              {s.is_active && (
                <Button
                  size="sm"
                  variant="outline"
                  className="text-destructive"
                  onClick={() => deactivateMutation.mutate(s.id)}
                  disabled={deactivateMutation.isPending}
                >
                  <Trash2 className="mr-1 h-3 w-3" />
                  Deactivate
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <Sheet open={sheetOpen} onOpenChange={(o) => { setSheetOpen(o); if (!o) reset(); }}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Invite Staff</SheetTitle>
            <SheetDescription>Send an invitation to join your team</SheetDescription>
          </SheetHeader>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 px-4">
            <div className="space-y-2">
              <Label htmlFor="full_name">Full Name</Label>
              <Input id="full_name" {...register("full_name")} />
              {errors.full_name && (
                <p className="text-xs text-destructive">{errors.full_name.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" {...register("email")} />
              {errors.email && (
                <p className="text-xs text-destructive">{errors.email.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="user_type">Role</Label>
              <Select onValueChange={(v) => register("user_type").onChange({ target: { value: v } })} defaultValue="staff">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="staff">Staff</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>

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
    </div>
  );
}
