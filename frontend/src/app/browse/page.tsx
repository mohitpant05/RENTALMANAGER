"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { MapPin, Search, Star, SlidersHorizontal } from "lucide-react";
import api from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useTenantStore } from "@/lib/tenant-store";
import { useSearch } from "@/hooks/use-search";
import type { ResourceTypeResponse, SearchHit, SearchRequest } from "@/types/api";
import { useAttachments } from "@/hooks/use-storage";
import {
  useCurrencyStore,
  useRates,
  convertPrice,
  formatPrice,
} from "@/hooks/use-currency";
import { CurrencySelect } from "@/components/ui/currency-select";
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

type SortOption = "relevance" | "price_asc" | "price_desc" | "rating";

export default function PublicHomePage() {
  const { user, isAuthenticated } = useAuthStore();
  const tenantResolved = useTenantStore((s) => s.resolved);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [sortBy, setSortBy] = useState<SortOption>("relevance");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const { displayCurrency, setDisplayCurrency } = useCurrencyStore();
  const { data: rates } = useRates();

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const { data: resourceTypes } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types/");
      return data;
    },
    enabled: tenantResolved,
  });

  const visibleTypes = resourceTypes?.filter(
    (t) => t.role === "primary" || t.role === "standalone",
  );

  const selectedSlug =
    selectedType !== "all"
      ? resourceTypes?.find((t) => t.id === selectedType)?.slug
      : undefined;

  const searchParams: SearchRequest = {
    q: debouncedQuery,
    resource_type_slug: selectedSlug,
    sort_by:
      sortBy === "price_asc" || sortBy === "price_desc"
        ? "base_price"
        : sortBy === "rating"
          ? "rating_avg"
          : undefined,
    sort_order:
      sortBy === "price_desc" || sortBy === "rating" ? "desc" : "asc",
    limit: 60,
  };

  const { data: searchResult, isLoading: searchLoading } = useSearch(
    searchParams,
    tenantResolved,
  );

  const hits = searchResult?.hits ?? [];

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-3 py-3 sm:px-4 sm:py-4">
          <Link href="/browse" className="text-lg font-bold sm:text-xl">
            RentManager
          </Link>
          <nav className="flex items-center gap-2 sm:gap-4">
            {isAuthenticated ? (
              <>
                <Link
                  href="/bookings"
                  className="text-xs sm:text-sm text-muted-foreground hover:text-foreground"
                >
                  Bookings
                </Link>
                <Link
                  href="/profile"
                  className="text-xs sm:text-sm text-muted-foreground hover:text-foreground"
                >
                  Profile
                </Link>
                <span className="hidden sm:inline text-sm text-muted-foreground">
                  {user?.full_name}
                </span>
              </>
            ) : (
              <>
                <Link href="/login" className="text-xs sm:text-sm font-medium hover:underline">
                  Sign in
                </Link>
                <Link href="/register">
                  <Button size="sm" className="h-7 text-xs sm:h-9 sm:text-sm">Sign up</Button>
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      <main>
        <section className="bg-muted/40 py-4 sm:py-16">
          <div className="mx-auto max-w-6xl px-3 sm:px-4 sm:text-center">
            <h1 className="hidden sm:block text-4xl font-bold tracking-tight sm:text-5xl">
              Find your next rental
            </h1>
            <p className="hidden sm:block mt-4 text-lg text-muted-foreground">
              Browse available resources and book instantly
            </p>

            <div className="mx-auto sm:mt-8 flex max-w-3xl flex-col gap-2 sm:gap-3 sm:flex-row">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search resources..."
                  className="pl-10 h-9 text-sm sm:h-10 sm:text-base"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <div className="grid grid-cols-3 gap-2 sm:contents">
                <Select value={selectedType} onValueChange={setSelectedType}>
                  <SelectTrigger className="w-full sm:w-[180px] h-9 text-xs sm:h-10 sm:text-sm">
                    <SelectValue placeholder="All types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All types</SelectItem>
                    {visibleTypes?.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortOption)}>
                  <SelectTrigger className="w-full sm:w-[160px] h-9 text-xs sm:h-10 sm:text-sm">
                    <SlidersHorizontal className="mr-1 h-3 w-3 sm:mr-2 sm:h-3.5 sm:w-3.5" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="relevance">Relevance</SelectItem>
                    <SelectItem value="price_asc">Price: Low → High</SelectItem>
                    <SelectItem value="price_desc">Price: High → Low</SelectItem>
                    <SelectItem value="rating">Top Rated</SelectItem>
                  </SelectContent>
                </Select>
                <CurrencySelect
                  value={displayCurrency}
                  onChange={setDisplayCurrency}
                  className="w-full sm:w-[130px] h-9 text-xs sm:h-10 sm:text-sm"
                />
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-3 sm:px-4 py-4 sm:py-8">
          {searchResult && (
            <div className="mb-3 sm:mb-4 flex items-center justify-between">
              <p className="text-xs sm:text-sm text-muted-foreground">
                {searchResult.estimated_total_hits} result{searchResult.estimated_total_hits !== 1 && "s"}
                {debouncedQuery && (
                  <> for &ldquo;{searchResult.query}&rdquo;</>
                )}
                <span className="ml-2 text-xs hidden sm:inline">
                  ({searchResult.processing_time_ms}ms)
                </span>
              </p>
            </div>
          )}

          {!tenantResolved || searchLoading ? (
            <div className="flex min-h-[40vh] items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          ) : hits.length === 0 ? (
            <div className="py-16 text-center">
              <p className="text-lg text-muted-foreground">
                No resources found{debouncedQuery ? ` for "${debouncedQuery}"` : ""}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:gap-6 lg:grid-cols-3">
              {hits.map((hit) => (
                <SearchHitCard
                  key={hit.id}
                  hit={hit}
                  displayCurrency={displayCurrency}
                  rates={rates}
                />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

interface SearchHitCardProps {
  hit: SearchHit;
  displayCurrency: string;
  rates: Record<string, number> | undefined;
}

function SearchHitCard({ hit, displayCurrency, rates }: SearchHitCardProps) {
  const { data: attachments } = useAttachments("resource", hit.id);
  const coverImage = attachments?.find((a) => a.download_url)?.download_url ?? undefined;
  const converted = convertPrice(hit.base_price, hit.currency, displayCurrency, rates);
  const priceLabel = formatPrice(converted, displayCurrency);

  return (
    <Link
      href={`/resources/${hit.id}`}
      className="group block overflow-hidden rounded-lg border bg-card transition-shadow hover:shadow-md"
    >
      <div className="aspect-video overflow-hidden bg-muted">
        {coverImage ? (
          <img
            src={coverImage}
            alt={hit.name}
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            <span className="text-2xl sm:text-4xl">📷</span>
          </div>
        )}
      </div>

      <div className="p-2.5 sm:p-4">
        <div className="flex items-start justify-between gap-1 sm:gap-2">
          <h3 className="text-xs sm:text-base font-semibold group-hover:text-primary line-clamp-2 leading-tight">
            {hit.name}
          </h3>
          <Badge variant="outline" className="hidden sm:inline-flex shrink-0 text-xs">
            {hit.type_slug}
          </Badge>
        </div>

        {hit.location_address && (
          <div className="mt-1 flex items-center gap-1 text-[11px] sm:text-sm text-muted-foreground">
            <MapPin className="h-2.5 w-2.5 sm:h-3 sm:w-3 shrink-0" />
            <span className="truncate">{hit.location_address}</span>
          </div>
        )}

        {hit.rating_count > 0 && (
          <div className="mt-1 sm:mt-2 flex items-center gap-1 text-[11px] sm:text-sm">
            <Star className="h-3 w-3 sm:h-3.5 sm:w-3.5 fill-yellow-400 text-yellow-400" />
            <span className="font-medium">{hit.rating_avg.toFixed(1)}</span>
            <span className="text-muted-foreground">
              ({hit.rating_count})
            </span>
          </div>
        )}

        <div className="mt-1.5 sm:mt-3 flex items-center justify-between">
          <div>
            <span className="text-sm sm:text-lg font-bold">{priceLabel}</span>
            <span className="ml-0.5 sm:ml-1 text-[10px] sm:text-sm text-muted-foreground">/day</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
