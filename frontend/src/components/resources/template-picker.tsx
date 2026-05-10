"use client";

import { useState } from "react";
import { Building, Car, ChefHat, Plus } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import type { ResourceTypeResponse } from "@/types/api";
import { toast } from "sonner";

const TEMPLATE_ICONS: Record<string, React.ReactNode> = {
  venues: <Building className="h-8 w-8" />,
  vehicles: <Car className="h-8 w-8" />,
  cooks: <ChefHat className="h-8 w-8" />,
};

const TEMPLATES = [
  {
    slug: "venues",
    name: "Venues",
    description: "Apartments, houses, event spaces, and other rentable venues",
  },
  {
    slug: "vehicles",
    name: "Vehicles",
    description: "Cars, bikes, scooters, vans, and other vehicles for rent",
  },
  {
    slug: "cooks",
    name: "Cooks",
    description: "Private cooks and chefs available for hire by time slot",
  },
];

interface TemplatePickerProps {
  onCreateCustom: () => void;
}

export function TemplatePicker({ onCreateCustom }: TemplatePickerProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState<string | null>(null);

  const createFromTemplate = useMutation({
    mutationFn: async (slug: string) => {
      const { data } = await api.post<ResourceTypeResponse>(
        `/resource-types/from-template/${slug}`
      );
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["resource-types"] });
      toast.success(`${data.name} created`);
      router.push(`/admin/resources/${data.slug}`);
    },
    onError: () => {
      toast.error("Failed to create resource type");
    },
    onSettled: () => {
      setCreating(null);
    },
  });

  function handleCreate(slug: string) {
    setCreating(slug);
    createFromTemplate.mutate(slug);
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-8">
      <div className="max-w-2xl text-center">
        <h1 className="text-3xl font-bold tracking-tight">
          What do you rent out?
        </h1>
        <p className="mt-2 text-muted-foreground">
          Pick a template to get started quickly, or create a custom type.
        </p>
      </div>

      <div className="mt-10 grid w-full max-w-3xl gap-4 sm:grid-cols-3">
        {TEMPLATES.map((t) => (
          <button
            key={t.slug}
            onClick={() => handleCreate(t.slug)}
            disabled={creating !== null}
            className="group relative flex flex-col items-center rounded-xl border-2 border-dashed border-muted-foreground/25 p-8 text-center transition-all hover:border-primary hover:bg-primary/5 disabled:opacity-50"
          >
            <div className="mb-4 rounded-lg bg-muted p-3 text-muted-foreground transition-colors group-hover:bg-primary/10 group-hover:text-primary">
              {TEMPLATE_ICONS[t.slug]}
            </div>
            <h3 className="font-semibold">{t.name}</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {t.description}
            </p>
            {creating === t.slug && (
              <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-background/80">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              </div>
            )}
          </button>
        ))}
      </div>

      <button
        onClick={onCreateCustom}
        className="mt-6 flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
      >
        <Plus className="h-4 w-4" />
        Create custom type
      </button>
    </div>
  );
}
