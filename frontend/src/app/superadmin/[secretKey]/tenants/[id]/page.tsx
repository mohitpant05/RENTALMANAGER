"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  useTenant,
  useToggleTenant,
  useTenantDomains,
  useAddTenantDomain,
  useDeleteTenantDomain,
  useUpdateTenantConfig,
  type DomainResponse,
} from "@/hooks/use-platform";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

function isIPAddress(value: string): boolean {
  const ipv4 = /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/;
  if (ipv4.test(value)) {
    return value.split(".").every((n) => {
      const num = parseInt(n, 10);
      return num >= 0 && num <= 255;
    });
  }
  const ipv6 = /^[0-9a-fA-F:]+$/;
  return ipv6.test(value) && value.includes(":");
}

export default function TenantDetailPage() {
  const params = useParams<{ secretKey: string; id: string }>();
  const { data: tenant, isLoading } = useTenant(params.id);
  const toggle = useToggleTenant();
  const updateConfig = useUpdateTenantConfig(params.id);

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
            <CardTitle className="text-sm">Tenant Settings</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Default Landing Page</label>
              <select
                className="mt-1 block w-full rounded-md border px-3 py-2 text-sm"
                value={(tenant.config?.landing_page as string) ?? "browse"}
                onChange={(e) => {
                  updateConfig.mutate({ landing_page: e.target.value });
                }}
              >
                <option value="browse">Browse — resource listings</option>
                <option value="marketing">Marketing — landing page</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Raw Config</label>
              <pre className="mt-1 max-h-48 overflow-auto rounded bg-muted p-3 text-xs">
                {JSON.stringify(tenant.config, null, 2) || "null"}
              </pre>
            </div>
          </CardContent>
        </Card>
      </div>

      <DomainsAndIPs tenantId={tenant.id} />

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

function DomainsAndIPs({ tenantId }: { tenantId: string }) {
  const { data: entries = [], isLoading } = useTenantDomains(tenantId);
  const addDomain = useAddTenantDomain(tenantId);
  const deleteDomain = useDeleteTenantDomain(tenantId);
  const [newValue, setNewValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  const domains = entries.filter((e) => !isIPAddress(e.domain));
  const ips = entries.filter((e) => isIPAddress(e.domain));

  function handleAdd() {
    const value = newValue.trim();
    if (!value) return;

    setError(null);
    addDomain.mutate(
      { domain: value, is_primary: false },
      {
        onSuccess: () => setNewValue(""),
        onError: (err: unknown) => {
          const msg =
            (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
            "Failed to add entry";
          setError(msg);
        },
      }
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Domains & IP Addresses</CardTitle>
        <p className="text-xs text-muted-foreground">
          Add domains or IP addresses that resolve to this tenant. Requests from these will auto-identify the tenant.
        </p>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex gap-2">
          <Input
            placeholder="e.g. rentals.acme.com or 192.168.1.100"
            value={newValue}
            onChange={(e) => {
              setNewValue(e.target.value);
              setError(null);
            }}
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            className="max-w-md"
          />
          <Button onClick={handleAdd} disabled={addDomain.isPending || !newValue.trim()}>
            {addDomain.isPending ? "Adding..." : "Add"}
          </Button>
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}

        {isLoading ? (
          <div className="flex h-20 items-center justify-center">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">No domains or IPs configured. Add one above.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            <EntryTable
              title="Domains"
              entries={domains}
              onDelete={(id) => deleteDomain.mutate(id)}
              isDeleting={deleteDomain.isPending}
            />
            <EntryTable
              title="IP Addresses"
              entries={ips}
              onDelete={(id) => deleteDomain.mutate(id)}
              isDeleting={deleteDomain.isPending}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function EntryTable({
  title,
  entries,
  onDelete,
  isDeleting,
}: {
  title: string;
  entries: DomainResponse[];
  onDelete: (id: string) => void;
  isDeleting: boolean;
}) {
  if (entries.length === 0) return null;

  return (
    <div>
      <h4 className="mb-2 text-xs font-medium text-muted-foreground">{title}</h4>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Value</TableHead>
            <TableHead className="w-16">Primary</TableHead>
            <TableHead className="w-20" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map((entry) => (
            <TableRow key={entry.id}>
              <TableCell className="font-mono text-sm">{entry.domain}</TableCell>
              <TableCell>
                {entry.is_primary && (
                  <Badge variant="secondary" className="text-xs">
                    Primary
                  </Badge>
                )}
              </TableCell>
              <TableCell>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs text-destructive hover:text-destructive"
                  onClick={() => onDelete(entry.id)}
                  disabled={isDeleting}
                >
                  Remove
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
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
