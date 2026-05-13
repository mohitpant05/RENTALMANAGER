"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useTenant, useToggleTenant } from "@/hooks/use-platform";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function TenantDetailPage() {
  const params = useParams<{ secretKey: string; id: string }>();
  const { data: tenant, isLoading } = useTenant(params.id);
  const toggle = useToggleTenant();

  if (isLoading || !tenant) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{tenant.name}</h1>
          <p className="text-muted-foreground">{tenant.slug}.rentmanager.com</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant={tenant.is_active ? "default" : "destructive"}>
            {tenant.is_active ? "Active" : "Inactive"}
          </Badge>
          <Button
            variant={tenant.is_active ? "destructive" : "default"}
            onClick={() => toggle.mutate({ id: tenant.id, activate: !tenant.is_active })}
            disabled={toggle.isPending}
          >
            {tenant.is_active ? "Deactivate" : "Activate"}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Configuration</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-sm">
            <Row label="Schema" value={tenant.schema_name} />
            <Row label="Currency" value={tenant.base_currency} />
            <Row label="Timezone" value={tenant.timezone} />
            <Row label="Created" value={new Date(tenant.created_at).toLocaleString()} />
            <Row label="Updated" value={new Date(tenant.updated_at).toLocaleString()} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Config (JSON)</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-48 overflow-auto rounded bg-muted p-3 text-xs">
              {JSON.stringify(tenant.config, null, 2) || "null"}
            </pre>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Quick Links</CardTitle>
        </CardHeader>
        <CardContent className="flex gap-3">
          <Link
            href={`/superadmin/${params.secretKey}/tenants/${tenant.id}/theme`}
            className="inline-flex h-7 items-center gap-1 rounded-[min(var(--radius-md),12px)] border border-input bg-background px-2.5 text-[0.8rem] text-foreground shadow-xs hover:bg-accent hover:text-accent-foreground"
          >
            Edit Theme
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono">{value}</span>
    </div>
  );
}
