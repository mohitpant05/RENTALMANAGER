"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useCreateTenant } from "@/hooks/use-platform";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function CreateTenantPage() {
  const params = useParams<{ secretKey: string }>();
  const router = useRouter();
  const create = useCreateTenant();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [timezone, setTimezone] = useState("UTC");
  const [error, setError] = useState("");

  function handleNameChange(val: string) {
    setName(val);
    setSlug(val.toLowerCase().replace(/[^a-z0-9-]/g, "-").replace(/-+/g, "-"));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    create.mutate(
      { name, slug, base_currency: currency, timezone },
      {
        onSuccess: (tenant) =>
          router.push(`/superadmin/${params.secretKey}/tenants/${tenant.id}`),
        onError: (err: any) =>
          setError(err.response?.data?.detail || "Failed to create tenant"),
      }
    );
  }

  return (
    <div className="mx-auto max-w-lg">
      <Card>
        <CardHeader>
          <CardTitle>Create Tenant</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => handleNameChange(e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="slug">Slug</Label>
              <Input
                id="slug"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                required
                pattern="^[a-z0-9-]+$"
              />
              <p className="text-xs text-muted-foreground">
                Used in subdomain: {slug || "..."}.rentmanager.com
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="currency">Currency</Label>
                <Input
                  id="currency"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                  maxLength={3}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="timezone">Timezone</Label>
                <Input
                  id="timezone"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                />
              </div>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Creating..." : "Create Tenant"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
