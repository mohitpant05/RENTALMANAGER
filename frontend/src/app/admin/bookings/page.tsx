"use client";

import { Suspense, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Search, X, ChevronLeft, ChevronRight } from "lucide-react";
import api from "@/lib/api";
import type { BookingResponse, ResourceResponse, UserResponse } from "@/types/api";
import { BookingTable } from "@/components/bookings/booking-table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const STATUS_TABS = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "confirmed", label: "Confirmed" },
  { value: "active", label: "Active" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "rejected", label: "Rejected" },
];

const PAGE_SIZE = 25;

export default function BookingsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-24">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      }
    >
      <BookingsContent />
    </Suspense>
  );
}

function BookingsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const status = searchParams.get("status") ?? "";
  const search = searchParams.get("search") ?? "";
  const page = parseInt(searchParams.get("page") ?? "1", 10);

  const [searchInput, setSearchInput] = useState(search);

  const offset = (page - 1) * PAGE_SIZE;

  const { data: paged, isLoading: bookingsLoading } = useQuery({
    queryKey: ["bookings", status, search, page],
    queryFn: async () => {
      const params: Record<string, string> = {
        offset: String(offset),
        limit: String(PAGE_SIZE),
      };
      if (status) params.status = status;
      if (search) params.search = search;
      const res = await api.get("/bookings", { params });
      if (Array.isArray(res.data)) {
        const totalCount = parseInt(res.headers?.["x-total-count"] ?? "0", 10);
        return { data: res.data as BookingResponse[], total: totalCount };
      }
      return res.data as { data: BookingResponse[]; total: number };
    },
  });

  const bookings = paged?.data ?? [];
  const total = paged?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const resourceIds = [...new Set(bookings.map((b) => b.resource_id))];

  const { data: resourceNames, isLoading: resourcesLoading } = useQuery({
    queryKey: ["resource-names", ...resourceIds],
    queryFn: async () => {
      const map: Record<string, string> = {};
      await Promise.all(
        resourceIds.map(async (id) => {
          try {
            const { data } = await api.get<ResourceResponse>(`/resources/${id}`);
            map[id] = data.name;
          } catch {}
        }),
      );
      return map;
    },
    enabled: resourceIds.length > 0,
  });

  const userIds = [...new Set(bookings.map((b) => b.user_id))];

  const { data: customerNames } = useQuery({
    queryKey: ["booking-customer-names", ...userIds],
    queryFn: async () => {
      const map: Record<string, string> = {};
      await Promise.all(
        userIds.map(async (id) => {
          try {
            const { data } = await api.get<UserResponse>(`/auth/user/${id}`);
            map[id] = data.full_name;
          } catch {}
        }),
      );
      return map;
    },
    enabled: userIds.length > 0,
  });

  const isLoading = bookingsLoading || (resourceIds.length > 0 && resourcesLoading);

  function setFilter(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    if (key !== "page") params.delete("page");
    router.replace(`/admin/bookings?${params.toString()}`);
  }

  function goToPage(p: number) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", String(p));
    router.replace(`/admin/bookings?${params.toString()}`);
  }

  function handleSearch() {
    setFilter("search", searchInput);
  }

  function clearSearch() {
    setSearchInput("");
    setFilter("search", "");
  }

  const startItem = total === 0 ? 0 : offset + 1;
  const endItem = Math.min(offset + PAGE_SIZE, total);

  return (
    <div className="flex-1 space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Bookings</h1>
        <p className="mt-1 text-muted-foreground">View and manage all bookings</p>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by ID, resource, customer..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSearch(); }}
            className="pl-9 pr-8"
          />
          {searchInput && (
            <button
              onClick={clearSearch}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <Button variant="secondary" onClick={handleSearch} disabled={!searchInput}>
          Search
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {STATUS_TABS.map((t) => (
          <Button
            key={t.value}
            variant={status === t.value ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter("status", t.value)}
          >
            {t.label}
          </Button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-24">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : (
        <>
          <BookingTable
            bookings={bookings}
            resourceNames={resourceNames ?? {}}
            customerNames={customerNames ?? {}}
          />

          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t pt-4">
              <p className="text-sm text-muted-foreground">
                {startItem}–{endItem} of {total}
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="icon"
                  disabled={page <= 1}
                  onClick={() => goToPage(page - 1)}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                  const start = Math.max(1, Math.min(page - 3, totalPages - 6));
                  const p = start + i;
                  if (p > totalPages) return null;
                  return (
                    <Button
                      key={p}
                      variant={p === page ? "default" : "outline"}
                      size="sm"
                      className="w-9"
                      onClick={() => goToPage(p)}
                    >
                      {p}
                    </Button>
                  );
                })}
                <Button
                  variant="outline"
                  size="icon"
                  disabled={page >= totalPages}
                  onClick={() => goToPage(page + 1)}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
