"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff, Loader2, Send } from "lucide-react";
import api from "@/lib/api";
import type { TenantResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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

type SmtpProvider = "none" | "smtp" | "mandrill";

function maskKey(key: string): string {
  if (!key || key.length < 8) return "••••••••";
  return "••••••••" + key.slice(-4);
}

export default function EmailSettingsPage() {
  const queryClient = useQueryClient();

  const { data: tenant } = useQuery({
    queryKey: ["admin-tenant"],
    queryFn: async () => {
      const { data } = await api.get<TenantResponse>("/admin/tenant");
      return data;
    },
  });

  const config = tenant?.config || {};
  const currentProvider = (config.smtp_provider as SmtpProvider) || "none";

  const [provider, setProvider] = useState<SmtpProvider>(currentProvider);
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("587");
  const [smtpUser, setSmtpUser] = useState("");
  const [smtpPassword, setSmtpPassword] = useState("");
  const [emailFrom, setEmailFrom] = useState("");
  const [mandrillApiKey, setMandrillApiKey] = useState("");
  const [testEmail, setTestEmail] = useState("");
  const [showKeys, setShowKeys] = useState(false);

  useEffect(() => {
    if (tenant) {
      const c = tenant.config || {};
      setProvider((c.smtp_provider as SmtpProvider) || "none");
      setSmtpHost((c.smtp_host as string) || "");
      setSmtpPort(String(c.smtp_port || 587));
      setEmailFrom((c.email_from as string) || "");
    }
  }, [tenant]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const updatedConfig: Record<string, unknown> = {
        smtp_provider: provider,
        email_from: emailFrom,
      };
      if (provider === "smtp") {
        updatedConfig.smtp_host = smtpHost;
        updatedConfig.smtp_port = parseInt(smtpPort, 10) || 587;
        if (smtpUser) updatedConfig.smtp_user = smtpUser;
        if (smtpPassword) updatedConfig.smtp_password = smtpPassword;
      }
      if (provider === "mandrill") {
        if (mandrillApiKey) updatedConfig.mandrill_api_key = mandrillApiKey;
      }
      await api.patch("/admin/tenant", { config: updatedConfig });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-tenant"] });
      toast.success("Email settings saved");
      setSmtpPassword("");
      setMandrillApiKey("");
    },
    onError: () => {
      toast.error("Failed to save settings");
    },
  });

  const testMutation = useMutation({
    mutationFn: async () => {
      await api.post("/admin/email/test", { to: testEmail });
    },
    onSuccess: () => {
      toast.success("Test email sent successfully");
    },
    onError: (err: unknown) => {
      let msg = "Failed to send test email";
      if (
        err &&
        typeof err === "object" &&
        "response" in err
      ) {
        const detail = (err as { response?: { data?: { detail?: string } } })
          .response?.data?.detail;
        if (typeof detail === "string") msg = detail;
      }
      toast.error(msg);
    },
  });

  return (
    <div className="flex-1 space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Email Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Configure SMTP so the platform can send transactional emails — signup
          confirmations, booking notifications, staff invitations, etc.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Email Provider</CardTitle>
          <CardDescription>
            Select how outbound emails are delivered
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Select
            value={provider}
            onValueChange={(v) => setProvider(v as SmtpProvider)}
          >
            <SelectTrigger className="w-[280px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">None (emails disabled)</SelectItem>
              <SelectItem value="smtp">SMTP (Gmail, SES, etc.)</SelectItem>
              <SelectItem value="mandrill">Mandrill (Mailchimp)</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {provider !== "none" && (
        <Card>
          <CardHeader>
            <CardTitle>Sender Address</CardTitle>
            <CardDescription>
              The &quot;From&quot; address on all outbound emails
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label>From Email</Label>
              <Input
                type="email"
                placeholder="noreply@yourdomain.com"
                value={emailFrom}
                onChange={(e) => setEmailFrom(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {provider === "smtp" && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>SMTP Configuration</CardTitle>
              <CardDescription>
                Enter your SMTP server credentials
              </CardDescription>
            </div>
            {!!config.smtp_host && config.smtp_provider === "smtp" && (
              <Badge variant="secondary">Configured</Badge>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>SMTP Host</Label>
                <Input
                  placeholder={
                    (config.smtp_host as string) || "smtp.gmail.com"
                  }
                  value={smtpHost}
                  onChange={(e) => setSmtpHost(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>SMTP Port</Label>
                <Input
                  type="number"
                  placeholder="587"
                  value={smtpPort}
                  onChange={(e) => setSmtpPort(e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Username</Label>
              <Input
                placeholder={
                  (config.smtp_user as string) || "you@gmail.com"
                }
                value={smtpUser}
                onChange={(e) => setSmtpUser(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Password / App Password</Label>
              <div className="flex gap-2">
                <Input
                  type={showKeys ? "text" : "password"}
                  placeholder={
                    config.smtp_password
                      ? maskKey(config.smtp_password as string)
                      : "••••••••"
                  }
                  value={smtpPassword}
                  onChange={(e) => setSmtpPassword(e.target.value)}
                />
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => setShowKeys(!showKeys)}
                >
                  {showKeys ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                For Gmail, use an App Password (not your account password).
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {provider === "mandrill" && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Mandrill Configuration</CardTitle>
              <CardDescription>Enter your Mandrill API key</CardDescription>
            </div>
            {!!config.mandrill_api_key &&
              config.smtp_provider === "mandrill" && (
                <Badge variant="secondary">Configured</Badge>
              )}
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>API Key</Label>
              <div className="flex gap-2">
                <Input
                  type={showKeys ? "text" : "password"}
                  placeholder={
                    config.mandrill_api_key
                      ? maskKey(config.mandrill_api_key as string)
                      : "your-mandrill-api-key"
                  }
                  value={mandrillApiKey}
                  onChange={(e) => setMandrillApiKey(e.target.value)}
                />
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => setShowKeys(!showKeys)}
                >
                  {showKeys ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
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
          {saveMutation.isPending && (
            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
          )}
          Save Settings
        </Button>
      </div>

      {provider !== "none" && !!config.smtp_provider && (
        <Card>
          <CardHeader>
            <CardTitle>Send Test Email</CardTitle>
            <CardDescription>
              Verify your configuration by sending a test email
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Input
                type="email"
                placeholder="recipient@example.com"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
                className="max-w-sm"
              />
              <Button
                variant="outline"
                onClick={() => testMutation.mutate()}
                disabled={testMutation.isPending || !testEmail}
              >
                {testMutation.isPending ? (
                  <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                ) : (
                  <Send className="mr-1 h-3 w-3" />
                )}
                Send Test
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
