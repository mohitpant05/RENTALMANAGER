"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { MapPin, Search, Star } from "lucide-react";
import api from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useTenantStore } from "@/lib/tenant-store";
import type { ResourceResponse, ResourceTypeResponse } from "@/types/api";
import { useAttachments } from "@/hooks/use-storage";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function PublicHomePage() {
  const { user, isAuthenticated } = useAuthStore();
  const tenantResolved = useTenantStore((s) => s.resolved);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const { data: resources } = useQuery({
    queryKey: ["resources"],
    queryFn: async () => {
      const { data } = await api.get<ResourceResponse[]>("/resources/");
      return data;
    },
    enabled: tenantResolved,
  });

  const { data: resourceTypes } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types/");
      return data;
    },
    enabled: tenantResolved,
  });

  const filtered = resources?.filter((r) => {
    if (selectedType !== "all" && r.type_id !== selectedType) return false;
    if (debouncedQuery) {
      const q = debouncedQuery.toLowerCase();
      return (
        r.name.toLowerCase().includes(q) ||
        r.description?.toLowerCase().includes(q) ||
        r.location_address?.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <Link href="/" className="text-xl font-bold">
            RentManager
          </Link>
          <nav className="flex items-center gap-4">
            {isAuthenticated ? (
              <>
                <Link
                  href="/bookings"
                  className="text-sm text-muted-foreground hover:text-foreground"
                >
                  My Bookings
                </Link>
                <Link
                  href="/profile"
                  className="text-sm text-muted-foreground hover:text-foreground"
                >
                  Profile
                </Link>
                <span className="text-sm text-muted-foreground">
                  {user?.full_name}
                </span>
              </>
            ) : (
              <>
                <Link href="/login" className="text-sm font-medium hover:underline">
                  Sign in
                </Link>
                <Link href="/register">
                  <Button size="sm">Sign up</Button>
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      <main>
        <section className="bg-muted/40 py-16">
          <div className="mx-auto max-w-6xl px-4 text-center">
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
              Find your next rental
            </h1>
            <p className="mt-4 text-lg text-muted-foreground">
              Browse available resources and book instantly
            </p>

            <div className="mx-auto mt-8 flex max-w-2xl flex-col gap-3 sm:flex-row">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search by name, description, or location..."
                  className="pl-10"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <Select value={selectedType} onValueChange={setSelectedType}>
                <SelectTrigger className="w-full sm:w-[200px]">
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All types</SelectItem>
                  {resourceTypes?.map((t) => (
                    <SelectItem key={t.id} value={t.id}>
                      {t.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-4 py-8">
          {!tenantResolved && (
            <div className="flex min-h-[40vh] items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          )}

          {tenantResolved && filtered?.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-lg text-muted-foreground">
                No resources found matching your criteria
              </p>
            </div>
          )}

          {tenantResolved && (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {filtered?.map((resource) => (
                <ResourceCard key={resource.id} resource={resource} />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function ResourceCard({ resource }: { resource: ResourceResponse }) {
  const { data: attachments } = useAttachments("resource", resource.id);

  const coverImage = attachments?.[0]?.url ?? null;

  return (
    <Link href={`/resources/${resource.id}`} className="group block overflow-hidden rounded-lg border bg-card transition-shadow hover:shadow-md">
      <div className="aspect-video overflow-hidden bg-muted">
        {coverImage ? (
          <img
            src={coverImage}
            alt={resource.name}
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            <span className="text-4xl">📷</span>
          </div>
        )}
      </div>

      <div className="p-4">
        <h3 className="font-semibold group-hover:text-primary">
          {resource.name}
        </h3>

        {resource.location_address && (
          <div className="mt-1 flex items-center gap-1 text-sm text-muted-foreground">
            <MapPin className="h-3 w-3" />
            <span className="truncate">{resource.location_address}</span>
          </div>
        )}

        {resource.rating_count > 0 && (
          <div className="mt-2 flex items-center gap-1 text-sm">
            <Star className="h-3.5 w-3.5 fill-yellow-400 text-yellow-400" />
            <span className="font-medium">
              {resource.rating_avg.toFixed(1)}
            </span>
            <span className="text-muted-foreground">
              ({resource.rating_count})
            </span>
          </div>
        )}

        <div className="mt-3 flex items-center justify-between">
          <div>
            <span className="text-lg font-bold">
              {resource.currency} {resource.base_price.toFixed(2)}
            </span>
            <span className="ml-1 text-sm text-muted-foreground">/day</span>
          </div>
          <Badge variant={resource.status === "active" ? "default" : "secondary"}>
            {resource.status}
          </Badge>
        </div>
      </div>
    </Link>
  );
}
