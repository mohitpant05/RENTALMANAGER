"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, UserCheck, UserX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import api from "@/lib/api";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface ListerResponse {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  is_active: boolean;
  user_type: string;
  manager_id: string | null;
  created_at: string;
  roles: string[];
}

export default function ListersPage() {
  const queryClient = useQueryClient();
  const [inviteOpen, setInviteOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");

  const { data: listers, isLoading } = useQuery({
    queryKey: ["listers"],
    queryFn: async () => {
      const { data } = await api.get<ListerResponse[]>("/admin/listers");
      return data;
    },
  });

  const inviteMutation = useMutation({
    mutationFn: async () => {
      await api.post("/admin/listers", { email, full_name: fullName });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["listers"] });
      setInviteOpen(false);
      setEmail("");
      setFullName("");
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail ?? "Failed to invite lister");
    },
  });

  const toggleActiveMutation = useMutation({
    mutationFn: async ({ id, active }: { id: string; active: boolean }) => {
      const action = active ? "activate" : "deactivate";
      await api.post(`/admin/listers/${id}/${action}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["listers"] });
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail ?? "Operation failed");
    },
  });

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
          <h1 className="text-2xl font-bold tracking-tight">Listers</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage resource listers under your account
          </p>
        </div>
        <Sheet open={inviteOpen} onOpenChange={setInviteOpen}>
          <SheetTrigger render={<Button size="sm" />}>
            <Plus className="mr-1.5 h-4 w-4" />
            Invite Lister
          </SheetTrigger>
          <SheetContent>
            <SheetHeader>
              <SheetTitle>Invite Lister</SheetTitle>
            </SheetHeader>
            <div className="mt-6 space-y-4">
              <div>
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="lister@example.com"
                />
              </div>
              <div>
                <Label htmlFor="name">Full Name</Label>
                <Input
                  id="name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="John Doe"
                />
              </div>
              <Button
                className="w-full"
                onClick={() => inviteMutation.mutate()}
                disabled={!email || !fullName || inviteMutation.isPending}
              >
                {inviteMutation.isPending ? "Inviting..." : "Send Invite"}
              </Button>
            </div>
          </SheetContent>
        </Sheet>
      </div>

      <div className="space-y-2">
        {listers && listers.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
            <p className="text-muted-foreground">No listers yet</p>
          </div>
        )}

        {listers?.map((lister) => (
          <Card key={lister.id}>
            <CardContent className="flex items-center justify-between p-4">
              <div>
                <p className="font-medium">{lister.full_name}</p>
                <p className="text-sm text-muted-foreground">{lister.email}</p>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-xs",
                    lister.is_active
                      ? "bg-green-100 text-green-700"
                      : "bg-red-100 text-red-700"
                  )}
                >
                  {lister.is_active ? "Active" : "Inactive"}
                </span>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() =>
                    toggleActiveMutation.mutate({
                      id: lister.id,
                      active: !lister.is_active,
                    })
                  }
                >
                  {lister.is_active ? (
                    <UserX className="h-4 w-4" />
                  ) : (
                    <UserCheck className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
