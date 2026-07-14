"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import type { DomainResponse, TenantResponse, DomainCreate } from "@/types/api";
import { useAuthStore } from "@/lib/auth-store";
import { usePermissions } from "@/hooks/use-permissions";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

const domainSchema = z.object({
  domain: z.string().min(1, "Domain is required"),
});

type DomainFormData = z.infer<typeof domainSchema>;

export default function SettingsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const { hasPermission, isLoading: permsLoading } = usePermissions();
  const [domainOpen, setDomainOpen] = useState(false);
  const [newDomain, setNewDomain] = useState("");

  const { data: tenant } = useQuery({
    queryKey: ["admin-tenant"],
    queryFn: async () => {
      const { data } = await api.get<TenantResponse>("/admin/tenant");
      return data;
    },
  });

  const { data: domains, isLoading: domainsLoading } = useQuery({
    queryKey: ["admin-domains"],
    queryFn: async () => {
      const { data } = await api.get<DomainResponse[]>("/admin/domains");
      return data;
    },
  });

  const {
    register: registerDomain,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<DomainFormData>({
    resolver: zodResolver(domainSchema),
  });

  const addDomainMutation = useMutation({
    mutationFn: async (data: DomainCreate) => {
      const { data: result } = await api.post<DomainResponse>("/admin/domains", data);
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-domains"] });
      toast.success("Domain added");
      setDomainOpen(false);
      setNewDomain("");
      reset();
    },
    onError: () => {
      toast.error("Failed to add domain");
    },
  });

  const deleteDomainMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/admin/domains/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-domains"] });
      toast.success("Domain removed");
    },
    onError: () => {
      toast.error("Failed to remove domain");
    },
  });

  const updateTenant = useMutation({
    mutationFn: async (payload: Partial<TenantResponse>) => {
      const { data } = await api.patch<TenantResponse>("/admin/tenant", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-tenant"] });
      toast.success("Settings updated");
    },
    onError: () => {
      toast.error("Failed to update settings");
    },
  });

  function onSubmit(data: DomainFormData) {
    addDomainMutation.mutate({ domain: data.domain });
  }

  const denied = !permsLoading && !hasPermission("settings:*:manage");
  useEffect(() => { if (denied) router.replace("/admin"); }, [denied, router]);

  if (permsLoading || denied) return <div className="flex flex-1 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" /></div>;

  return (
    <div className="flex-1 space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">Configure tenant settings and domains</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Tenant Information</CardTitle>
          <CardDescription>Your organization details</CardDescription>
        </CardHeader>
        <CardContent>
          {tenant && (
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Name</span>
                <span className="font-medium">{tenant.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Slug</span>
                <Badge variant="secondary">{tenant.slug}</Badge>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Currency</span>
                <span className="font-medium">{tenant.base_currency}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Timezone</span>
                <span className="font-medium">{tenant.timezone}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Status</span>
                <Badge variant={tenant.is_active ? "success" : "destructive"}>
                  {tenant.is_active ? "Active" : "Inactive"}
                </Badge>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Domains</CardTitle>
            <CardDescription>Manage custom domains for this tenant</CardDescription>
          </div>
          <Button size="sm" onClick={() => setDomainOpen(true)}>
            <Plus className="mr-1 h-3 w-3" />
            Add Domain
          </Button>
        </CardHeader>
        <CardContent>
          {domainsLoading && (
            <div className="flex items-center justify-center py-8">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          )}

          {domains && domains.length === 0 && (
            <p className="text-sm text-muted-foreground py-4">No custom domains configured</p>
          )}

          {domains && domains.length > 0 && (
            <div className="space-y-2">
              {domains.map((d) => (
                <div key={d.id} className="flex items-center justify-between rounded-lg border p-3">
                  <div>
                    <span className="font-medium">{d.domain}</span>
                    <div className="flex gap-2 mt-1">
                      {d.is_primary && <Badge variant="default" className="text-xs">Primary</Badge>}
                      {d.is_verified && <Badge variant="success" className="text-xs">Verified</Badge>}
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-destructive"
                    onClick={() => deleteDomainMutation.mutate(d.id)}
                    disabled={deleteDomainMutation.isPending}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Staff Isolation */}
      {tenant && user?.user_type === "admin" && (
        <Card>
          <CardContent className="p-6">
            <h3 className="text-lg font-semibold">Staff Data Isolation</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Control whether staff members see each other&apos;s data
            </p>
            <div className="mt-4 flex items-center gap-3">
              <select
                className="rounded-md border px-3 py-2 text-sm"
                value={(tenant.config?.staff_isolation_mode as string) ?? "shared"}
                onChange={(e) => {
                  updateTenant.mutate({
                    config: {
                      ...tenant.config,
                      staff_isolation_mode: e.target.value,
                    },
                  });
                }}
              >
                <option value="shared">Shared — all staff see all data</option>
                <option value="isolated">Isolated — staff see only their own data</option>
              </select>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Landing Page */}
      {tenant && user?.user_type === "admin" && (
        <Card>
          <CardContent className="p-6">
            <h3 className="text-lg font-semibold">Default Landing Page</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Choose what visitors see when they first arrive at your site
            </p>
            <div className="mt-4 flex items-center gap-3">
              <select
                className="rounded-md border px-3 py-2 text-sm"
                value={(tenant.config?.landing_page as string) ?? "browse"}
                onChange={(e) => {
                  updateTenant.mutate({
                    config: {
                      ...tenant.config,
                      landing_page: e.target.value,
                    },
                  });
                }}
              >
                <option value="browse">Browse — show resource listings immediately</option>
                <option value="marketing">Marketing — show landing page with hero & CTA</option>
              </select>
            </div>
          </CardContent>
        </Card>
      )}

      {domainOpen && (
        <Card className="border-primary/20">
          <CardHeader>
            <CardTitle className="text-base">Add New Domain</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="flex gap-2">
              <div className="flex-1 space-y-2">
                <Label htmlFor="domain">Domain</Label>
                <Input id="domain" placeholder="app.example.com" {...registerDomain("domain")} />
                {errors.domain && (
                  <p className="text-xs text-destructive">{errors.domain.message}</p>
                )}
              </div>
              <div className="flex items-end gap-2">
                <Button type="submit" disabled={addDomainMutation.isPending}>
                  {addDomainMutation.isPending && (
                    <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                  )}
                  Add
                </Button>
                <Button type="button" variant="outline" onClick={() => setDomainOpen(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
