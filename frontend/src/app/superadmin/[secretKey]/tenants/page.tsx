"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTenants, useToggleTenant } from "@/hooks/use-platform";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function TenantsPage() {
  const params = useParams<{ secretKey: string }>();
  const router = useRouter();
  const { data: tenants, isLoading } = useTenants();
  const toggle = useToggleTenant();
  const [search, setSearch] = useState("");

  const filtered = tenants?.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.slug.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tenants</h1>
        <Button onClick={() => router.push(`/superadmin/${params.secretKey}/tenants/new`)}>
          Create Tenant
        </Button>
      </div>

      <Input
        placeholder="Search by name or slug..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-sm"
      />

      {isLoading ? (
        <div className="flex h-32 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Slug</TableHead>
              <TableHead>Currency</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered?.map((tenant) => (
              <TableRow
                key={tenant.id}
                className="cursor-pointer"
                onClick={() => router.push(`/superadmin/${params.secretKey}/tenants/${tenant.id}`)}
              >
                <TableCell className="font-medium">{tenant.name}</TableCell>
                <TableCell>{tenant.slug}</TableCell>
                <TableCell>{tenant.base_currency}</TableCell>
                <TableCell>
                  <Badge variant={tenant.is_active ? "default" : "destructive"}>
                    {tenant.is_active ? "Active" : "Inactive"}
                  </Badge>
                </TableCell>
                <TableCell>{new Date(tenant.created_at).toLocaleDateString()}</TableCell>
                <TableCell>
                  <Button
                    size="sm"
                    variant={tenant.is_active ? "destructive" : "default"}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggle.mutate({ id: tenant.id, activate: !tenant.is_active });
                    }}
                    disabled={toggle.isPending}
                  >
                    {tenant.is_active ? "Deactivate" : "Activate"}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
