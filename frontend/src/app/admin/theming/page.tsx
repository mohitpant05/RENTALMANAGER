"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Palette, RotateCcw } from "lucide-react";
import api from "@/lib/api";
import type { ThemeResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import { ThemeForm } from "@/components/theming/theme-form";
import { ThemePreview } from "@/components/theming/theme-preview";
import { toast } from "sonner";

const DEFAULT_COLORS: Record<string, string> = {
  primary: "#3b82f6",
  secondary: "#e5e7eb",
  accent: "#f59e0b",
  background: "#f9fafb",
  surface: "#ffffff",
  text_primary: "#111827",
  text_secondary: "#6b7280",
  error: "#ef4444",
  success: "#22c55e",
};

const DEFAULT_TYPOGRAPHY: Record<string, string | number> = {
  font_family: "Inter",
  heading_font: "Inter",
  base_size: 16,
  border_radius: 8,
};

const DEFAULT_COMPONENTS: Record<string, string | boolean> = {
  button_style: "rounded",
  card_shadow: true,
  navbar_position: "top",
  footer_layout: "standard",
};

export default function ThemingPage() {
  const queryClient = useQueryClient();

  const { data: theme, isLoading } = useQuery({
    queryKey: ["admin-theme"],
    queryFn: async () => {
      const { data } = await api.get<ThemeResponse>("/admin/theme");
      return data;
    },
  });

  const [colors, setColors] = useState<Record<string, string>>(DEFAULT_COLORS);
  const [typography, setTypography] = useState<Record<string, string | number>>(DEFAULT_TYPOGRAPHY);
  const [components, setComponents] = useState<Record<string, string | boolean>>(DEFAULT_COMPONENTS);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    if (theme && !initialized) {
      setColors({ ...DEFAULT_COLORS, ...(theme.colors as Record<string, string>) });
      setTypography({ ...DEFAULT_TYPOGRAPHY, ...(theme.typography as Record<string, string | number>) });
      setComponents({ ...DEFAULT_COMPONENTS, ...(theme.components as Record<string, string | boolean>) });
      setInitialized(true);
    }
  }, [theme, initialized]);

  const isDirty =
    initialized &&
    theme &&
    (JSON.stringify(colors) !== JSON.stringify({ ...DEFAULT_COLORS, ...(theme.colors as Record<string, string>) }) ||
      JSON.stringify(typography) !== JSON.stringify({ ...DEFAULT_TYPOGRAPHY, ...(theme.typography as Record<string, string | number>) }) ||
      JSON.stringify(components) !== JSON.stringify({ ...DEFAULT_COMPONENTS, ...(theme.components as Record<string, string | boolean>) }));

  const saveMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.put<ThemeResponse>("/admin/theme", {
        colors,
        typography,
        components,
      });
      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(["admin-theme"], data);
      setInitialized(false);
      toast.success("Theme saved");
    },
    onError: () => {
      toast.error("Failed to save theme");
    },
  });

  function handleReset() {
    if (theme) {
      setColors({ ...DEFAULT_COLORS, ...(theme.colors as Record<string, string>) });
      setTypography({ ...DEFAULT_TYPOGRAPHY, ...(theme.typography as Record<string, string | number>) });
      setComponents({ ...DEFAULT_COMPONENTS, ...(theme.components as Record<string, string | boolean>) });
    }
  }

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Palette className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Theme Editor</h1>
            <p className="text-sm text-muted-foreground">
              Customize your marketplace appearance
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          {isDirty && (
            <Button variant="ghost" size="sm" onClick={handleReset}>
              <RotateCcw className="mr-1.5 h-4 w-4" />
              Reset
            </Button>
          )}
          <Button
            size="sm"
            disabled={!isDirty || saveMutation.isPending}
            onClick={() => saveMutation.mutate()}
          >
            {saveMutation.isPending && (
              <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
            )}
            Save Theme
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Form panel */}
        <ThemeForm
          colors={colors}
          typography={typography}
          components={components}
          onColorsChange={setColors}
          onTypographyChange={setTypography}
          onComponentsChange={setComponents}
        />

        {/* Preview panel — sticky on desktop */}
        <div className="hidden lg:block">
          <div className="sticky top-24 space-y-3">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Live Preview
            </p>
            <ThemePreview
              colors={colors}
              typography={typography}
              components={components}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
