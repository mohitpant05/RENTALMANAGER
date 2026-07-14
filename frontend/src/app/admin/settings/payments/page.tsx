"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { usePermissions } from "@/hooks/use-permissions";
import api from "@/lib/api";
import type { TenantResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

type Provider = "manual" | "stripe" | "razorpay";

function maskKey(key: string): string {
  if (!key || key.length < 8) return "••••••••";
  return "••••••••" + key.slice(-4);
}

export default function PaymentSettingsPage() {
  const router = useRouter();
  const { hasPermission, isLoading: permsLoading } = usePermissions();
  const queryClient = useQueryClient();

  const { data: tenant } = useQuery({
    queryKey: ["admin-tenant"],
    queryFn: async () => {
      const { data } = await api.get<TenantResponse>("/admin/tenant");
      return data;
    },
  });

  const config = tenant?.config || {};
  const currentProvider = (config.payment_provider as Provider) || "manual";

  const [provider, setProvider] = useState<Provider>(currentProvider);
  const [stripeSecret, setStripeSecret] = useState("");
  const [stripePub, setStripePub] = useState("");
  const [razorpayId, setRazorpayId] = useState("");
  const [razorpaySecret, setRazorpaySecret] = useState("");
  const [showKeys, setShowKeys] = useState(false);

  useEffect(() => {
    if (tenant) {
      const c = tenant.config || {};
      setProvider((c.payment_provider as Provider) || "manual");
    }
  }, [tenant]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const updatedConfig: Record<string, unknown> = {
        payment_provider: provider,
      };
      if (stripeSecret) updatedConfig.stripe_secret_key = stripeSecret;
      if (stripePub) updatedConfig.stripe_publishable_key = stripePub;
      if (razorpayId) updatedConfig.razorpay_key_id = razorpayId;
      if (razorpaySecret) updatedConfig.razorpay_key_secret = razorpaySecret;

      await api.patch("/admin/tenant", { config: updatedConfig });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-tenant"] });
      toast.success("Payment settings saved");
      setStripeSecret("");
      setStripePub("");
      setRazorpayId("");
      setRazorpaySecret("");
    },
    onError: () => {
      toast.error("Failed to save settings");
    },
  });

  const denied = !permsLoading && !hasPermission("settings:*:manage");
  useEffect(() => { if (denied) router.replace("/admin"); }, [denied, router]);

  if (permsLoading || denied) {
    return <div className="flex flex-1 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" /></div>;
  }

  return (
    <div className="flex-1 space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Payment Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Configure payment gateway. Manual mode requires admin to mark payments as paid.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Active Provider</CardTitle>
          <CardDescription>Select which payment provider to use</CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={provider} onValueChange={(v) => setProvider(v as Provider)}>
            <SelectTrigger className="w-[250px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="manual">Manual (Admin marks paid)</SelectItem>
              <SelectItem value="stripe">Stripe</SelectItem>
              <SelectItem value="razorpay">Razorpay</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {provider === "stripe" && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Stripe Configuration</CardTitle>
              <CardDescription>Enter your Stripe API keys</CardDescription>
            </div>
            {!!config.stripe_secret_key && (
              <Badge variant="secondary">Configured</Badge>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Secret Key</Label>
              <div className="flex gap-2">
                <Input
                  type={showKeys ? "text" : "password"}
                  placeholder={config.stripe_secret_key ? maskKey(config.stripe_secret_key as string) : "sk_..."}
                  value={stripeSecret}
                  onChange={(e) => setStripeSecret(e.target.value)}
                />
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => setShowKeys(!showKeys)}
                >
                  {showKeys ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Publishable Key</Label>
              <Input
                type={showKeys ? "text" : "password"}
                placeholder={config.stripe_publishable_key ? maskKey(config.stripe_publishable_key as string) : "pk_..."}
                value={stripePub}
                onChange={(e) => setStripePub(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {provider === "razorpay" && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Razorpay Configuration</CardTitle>
              <CardDescription>Enter your Razorpay API keys</CardDescription>
            </div>
            {!!config.razorpay_key_id && (
              <Badge variant="secondary">Configured</Badge>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Key ID</Label>
              <Input
                type={showKeys ? "text" : "password"}
                placeholder={config.razorpay_key_id ? maskKey(config.razorpay_key_id as string) : "rzp_..."}
                value={razorpayId}
                onChange={(e) => setRazorpayId(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Key Secret</Label>
              <div className="flex gap-2">
                <Input
                  type={showKeys ? "text" : "password"}
                  placeholder={config.razorpay_key_secret ? maskKey(config.razorpay_key_secret as string) : "secret..."}
                  value={razorpaySecret}
                  onChange={(e) => setRazorpaySecret(e.target.value)}
                />
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => setShowKeys(!showKeys)}
                >
                  {showKeys ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex gap-3">
        <Button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
        >
          {saveMutation.isPending && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
          Save Settings
        </Button>
      </div>
    </div>
  );
}
