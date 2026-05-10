"use client";

import { useState, useEffect, useMemo } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Plus, Search, Settings } from "lucide-react";
import api from "@/lib/api";
import type { ResourceResponse, ResourceTypeResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ResourceTable } from "@/components/resources/resource-table";
import { CreateResourceSheet } from "@/components/resources/create-resource-sheet";
import { useCreateTypeSheetStore } from "@/lib/create-type-sheet-store";
import { CreateTypeSheet } from "@/components/resources/create-type-sheet";

export default function ResourceTypePage() {
  const { typeSlug } = useParams<{ typeSlug: string }>();
  const { open: typeSheetOpen, setOpen: setTypeSheetOpen } = useCreateTypeSheetStore();
  const [sheetOpen, setSheetOpen] = useState(false);
  const [editingResource, setEditingResource] =
    useState<ResourceResponse | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [editTypeOpen, setEditTypeOpen] = useState(false);

  const { data: types } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types");
      return data;
    },
    staleTime: 30_000,
  });

  const currentType = types?.find((t) => t.slug === typeSlug);

  const { data: resources, isLoading } = useQuery({
    queryKey: ["resources", currentType?.id, statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (currentType!.id) params.set("type_id", currentType!.id);
      if (statusFilter !== "all") params.set("status", statusFilter);
      const { data } = await api.get<ResourceResponse[]>(
        `/resources?${params.toString()}`
      );
      return data;
    },
    enabled: !!currentType,
  });

  // Handle edit parameter from URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const editId = params.get("edit");
    if (editId && resources) {
      const resource = resources.find((r) => r.id === editId);
      if (resource) {
        setEditingResource(resource);
        setSheetOpen(true);
        // Clean up URL
        params.delete("edit");
        const newUrl = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`;
        window.history.replaceState(null, "", newUrl);
      }
    }
  }, [resources]);

  const filteredResources = useMemo(() => {
    if (!resources) return [];
    if (!search) return resources;
    const q = search.toLowerCase();
    return resources.filter(
      (r) =>
        r.name.toLowerCase().includes(q) ||
        r.description?.toLowerCase().includes(q)
    );
  }, [resources, search]);

  if (!currentType) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  function openCreate() {
    setEditingResource(null);
    setSheetOpen(true);
  }

  function openEdit(resource: ResourceResponse) {
    setEditingResource(resource);
    setSheetOpen(true);
  }

  return (
    <div className="flex-1 space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {currentType.name}
          </h1>
          {currentType.description && (
            <p className="mt-1 text-sm text-muted-foreground">
              {currentType.description}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setEditTypeOpen(true)}>
            <Settings className="mr-2 h-4 w-4" />
            Type Settings
          </Button>
          <Button onClick={openCreate}>
            <Plus className="mr-2 h-4 w-4" />
            Add {currentType.name.replace(/s$/, "")}
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search resources..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="inactive">Inactive</SelectItem>
            <SelectItem value="archived">Archived</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : (
        <ResourceTable
          resources={filteredResources}
          typeId={currentType.id}
          typeSlug={typeSlug}
          onEdit={openEdit}
        />
      )}

      <CreateResourceSheet
        open={sheetOpen}
        onClose={() => {
          setSheetOpen(false);
          setEditingResource(null);
        }}
        typeId={currentType.id}
        typeName={currentType.name}
        attributeSchema={currentType.attribute_schema}
        editingResource={editingResource}
      />

      <CreateTypeSheet
        open={typeSheetOpen || editTypeOpen}
        onClose={() => {
          setTypeSheetOpen(false);
          setEditTypeOpen(false);
        }}
        editingType={editTypeOpen ? currentType : null}
      />
    </div>
  );
}
