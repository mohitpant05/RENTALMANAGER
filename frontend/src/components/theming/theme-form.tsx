"use client";

import { useState, useEffect, useRef } from "react";
import { ChevronDown, Image as ImageIcon, Upload, X, Loader2, Check, Palette } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useUpload } from "@/hooks/use-storage";
import { toast } from "sonner";
import { ColorInput } from "./color-input";

interface SectionProps {
  id: string;
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

function Section({ id, title, defaultOpen = false, children }: SectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleHash() {
      if (window.location.hash === `#${id}`) {
        setOpen(true);
        ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
    handleHash();
    window.addEventListener("hashchange", handleHash);
    return () => window.removeEventListener("hashchange", handleHash);
  }, [id]);

  return (
    <div id={id} ref={ref} className="rounded-lg border">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium hover:bg-muted/50"
      >
        {title}
        <ChevronDown
          className={cn("h-4 w-4 transition-transform", open && "rotate-180")}
        />
      </button>
      {open && <div className="border-t px-4 py-4 space-y-4">{children}</div>}
    </div>
  );
}

// ─── Color Presets ───────────────────────────────────────────────────

interface ColorPreset {
  name: string;
  description: string;
  colors: Record<string, string>;
}

const COLOR_PRESETS: ColorPreset[] = [
  {
    name: "Ocean",
    description: "Clean & professional",
    colors: {
      primary: "#2563eb",
      secondary: "#e2e8f0",
      accent: "#f59e0b",
      background: "#f8fafc",
      surface: "#ffffff",
      text_primary: "#0f172a",
      text_secondary: "#64748b",
      error: "#ef4444",
      success: "#22c55e",
    },
  },
  {
    name: "Emerald",
    description: "Natural & organic",
    colors: {
      primary: "#059669",
      secondary: "#ecfdf5",
      accent: "#d97706",
      background: "#fafaf9",
      surface: "#ffffff",
      text_primary: "#1c1917",
      text_secondary: "#78716c",
      error: "#dc2626",
      success: "#0891b2",
    },
  },
  {
    name: "Sunset",
    description: "Warm & inviting",
    colors: {
      primary: "#ea580c",
      secondary: "#fff7ed",
      accent: "#7c3aed",
      background: "#fffbeb",
      surface: "#ffffff",
      text_primary: "#1c1917",
      text_secondary: "#78716c",
      error: "#dc2626",
      success: "#16a34a",
    },
  },
  {
    name: "Slate",
    description: "Modern & minimal",
    colors: {
      primary: "#18181b",
      secondary: "#f4f4f5",
      accent: "#8b5cf6",
      background: "#fafafa",
      surface: "#ffffff",
      text_primary: "#18181b",
      text_secondary: "#71717a",
      error: "#ef4444",
      success: "#22c55e",
    },
  },
  {
    name: "Royal",
    description: "Bold & premium",
    colors: {
      primary: "#7c3aed",
      secondary: "#ede9fe",
      accent: "#f59e0b",
      background: "#faf5ff",
      surface: "#ffffff",
      text_primary: "#1e1b4b",
      text_secondary: "#6b7280",
      error: "#ef4444",
      success: "#22c55e",
    },
  },
];

function getActivePreset(colors: Record<string, string>): string | null {
  for (const preset of COLOR_PRESETS) {
    const match = Object.entries(preset.colors).every(
      ([k, v]) => (colors[k] ?? "").toLowerCase() === v.toLowerCase()
    );
    if (match) return preset.name;
  }
  return null;
}

const COLOR_FIELDS = [
  { key: "primary", label: "Primary" },
  { key: "secondary", label: "Secondary" },
  { key: "accent", label: "Accent" },
  { key: "background", label: "Background" },
  { key: "surface", label: "Surface" },
  { key: "text_primary", label: "Text Primary" },
  { key: "text_secondary", label: "Text Secondary" },
  { key: "error", label: "Error" },
  { key: "success", label: "Success" },
];

const FONT_OPTIONS = [
  "Inter",
  "Poppins",
  "Roboto",
  "Open Sans",
  "Lato",
  "Montserrat",
  "DM Sans",
  "Plus Jakarta Sans",
];

const BUTTON_STYLES = [
  { value: "rounded", label: "Rounded" },
  { value: "square", label: "Square" },
  { value: "pill", label: "Pill" },
];

const FOOTER_LAYOUTS = [
  { value: "standard", label: "Standard" },
  { value: "minimal", label: "Minimal" },
  { value: "expanded", label: "Expanded" },
];

interface ThemeFormProps {
  brand: Record<string, string>;
  colors: Record<string, string>;
  typography: Record<string, string | number>;
  components: Record<string, string | boolean>;
  themeId?: string;
  onBrandChange: (brand: Record<string, string>) => void;
  onColorsChange: (colors: Record<string, string>) => void;
  onTypographyChange: (typography: Record<string, string | number>) => void;
  onComponentsChange: (components: Record<string, string | boolean>) => void;
}

export function ThemeForm({
  brand,
  colors,
  typography,
  components,
  themeId,
  onBrandChange,
  onColorsChange,
  onTypographyChange,
  onComponentsChange,
}: ThemeFormProps) {
  const { upload, isUploading } = useUpload("theme", themeId ?? "");
  const activePreset = getActivePreset(colors);
  const [customOpen, setCustomOpen] = useState(false);

  async function handleLogoUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const attachment = await upload(file);
      if (attachment?.download_url) {
        onBrandChange({ ...brand, logo_url: attachment.download_url });
        toast.success("Logo uploaded");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      toast.error(msg);
    }
    e.target.value = "";
  }

  async function handleFaviconUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const attachment = await upload(file);
      if (attachment?.download_url) {
        onBrandChange({ ...brand, favicon_url: attachment.download_url });
        toast.success("Favicon uploaded");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      toast.error(msg);
    }
    e.target.value = "";
  }

  function setColor(key: string, value: string) {
    onColorsChange({ ...colors, [key]: value });
  }

  function setTypo(key: string, value: string | number) {
    onTypographyChange({ ...typography, [key]: value });
  }

  function setComp(key: string, value: string | boolean) {
    onComponentsChange({ ...components, [key]: value });
  }

  return (
    <div className="space-y-4">
      {/* Brand */}
      <Section id="brand" title="Brand" defaultOpen>
        <div className="space-y-4">
          <div>
            <Label className="text-xs">Logo</Label>
            <div className="mt-1.5 flex items-center gap-4">
              {brand.logo_url ? (
                <div className="relative h-16 w-32 rounded border bg-muted/50 p-1">
                  <img
                    src={brand.logo_url}
                    alt="Logo"
                    className="h-full w-full object-contain"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      const { logo_url: _, ...rest } = brand;
                      onBrandChange(rest);
                    }}
                    className="absolute -right-2 -top-2 rounded-full bg-destructive p-0.5 text-destructive-foreground"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ) : (
                <div className="flex h-16 w-32 items-center justify-center rounded border border-dashed bg-muted/30">
                  <ImageIcon className="h-6 w-6 text-muted-foreground" />
                </div>
              )}
              <label className="cursor-pointer inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted transition-colors">
                {isUploading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Upload className="h-3.5 w-3.5" />
                )}
                Upload Logo
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif"
                  className="hidden"
                  onChange={handleLogoUpload}
                  disabled={isUploading}
                />
              </label>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">PNG, JPG, WebP. Max 10MB.</p>
          </div>

          <div>
            <Label className="text-xs">Favicon</Label>
            <div className="mt-1.5 flex items-center gap-4">
              {brand.favicon_url ? (
                <div className="relative h-10 w-10 rounded border bg-muted/50 p-1">
                  <img
                    src={brand.favicon_url}
                    alt="Favicon"
                    className="h-full w-full object-contain"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      const { favicon_url: _, ...rest } = brand;
                      onBrandChange(rest);
                    }}
                    className="absolute -right-2 -top-2 rounded-full bg-destructive p-0.5 text-destructive-foreground"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ) : (
                <div className="flex h-10 w-10 items-center justify-center rounded border border-dashed bg-muted/30">
                  <ImageIcon className="h-4 w-4 text-muted-foreground" />
                </div>
              )}
              <label className="cursor-pointer inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted transition-colors">
                {isUploading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Upload className="h-3.5 w-3.5" />
                )}
                Upload Favicon
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif"
                  className="hidden"
                  onChange={handleFaviconUpload}
                  disabled={isUploading}
                />
              </label>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">Square image recommended. PNG, ICO.</p>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">Business Name</Label>
            <Input
              value={brand.business_name ?? ""}
              onChange={(e) => onBrandChange({ ...brand, business_name: e.target.value })}
              placeholder="Your Business Name"
              className="h-9"
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">Headline</Label>
            <Input
              value={brand.headline ?? ""}
              onChange={(e) => onBrandChange({ ...brand, headline: e.target.value })}
              placeholder="Find & Book"
              className="h-9"
            />
            <p className="text-[11px] text-muted-foreground">Main hero heading on your marketplace</p>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">Tagline</Label>
            <Input
              value={brand.tagline ?? ""}
              onChange={(e) => onBrandChange({ ...brand, tagline: e.target.value })}
              placeholder="Your marketplace headline"
              className="h-9"
            />
          </div>
        </div>
      </Section>

      {/* Colors */}
      <Section id="colors" title="Colors" defaultOpen>
        <div className="space-y-4">
          {/* Preset cards */}
          <div>
            <Label className="text-xs mb-2 block">Color Themes</Label>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {COLOR_PRESETS.map((preset) => {
                const isActive = activePreset === preset.name;
                return (
                  <button
                    key={preset.name}
                    type="button"
                    onClick={() => {
                      onColorsChange({ ...preset.colors });
                      setCustomOpen(false);
                    }}
                    className={cn(
                      "relative flex flex-col gap-1.5 rounded-lg border p-3 text-left transition-all hover:border-primary/50",
                      isActive
                        ? "border-primary bg-primary/5 ring-1 ring-primary"
                        : "hover:bg-muted/30"
                    )}
                  >
                    {isActive && (
                      <div className="absolute right-2 top-2 rounded-full bg-primary p-0.5">
                        <Check className="h-2.5 w-2.5 text-primary-foreground" />
                      </div>
                    )}
                    <div className="flex gap-1">
                      {["primary", "secondary", "accent", "background", "success"].map((k) => (
                        <div
                          key={k}
                          className="h-4 w-4 rounded-full border border-black/10"
                          style={{ backgroundColor: preset.colors[k] }}
                        />
                      ))}
                    </div>
                    <div>
                      <p className="text-xs font-medium">{preset.name}</p>
                      <p className="text-[10px] text-muted-foreground">{preset.description}</p>
                    </div>
                  </button>
                );
              })}

              {/* Custom option */}
              <button
                type="button"
                onClick={() => setCustomOpen(true)}
                className={cn(
                  "relative flex flex-col gap-1.5 rounded-lg border p-3 text-left transition-all hover:border-primary/50",
                  !activePreset && !customOpen
                    ? "border-primary bg-primary/5 ring-1 ring-primary"
                    : customOpen
                      ? "border-primary bg-primary/5 ring-1 ring-primary"
                      : "hover:bg-muted/30"
                )}
              >
                {(!activePreset || customOpen) && (
                  <div className="absolute right-2 top-2 rounded-full bg-primary p-0.5">
                    <Check className="h-2.5 w-2.5 text-primary-foreground" />
                  </div>
                )}
                <div className="flex h-4 items-center">
                  <Palette className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-xs font-medium">Custom</p>
                  <p className="text-[10px] text-muted-foreground">Pick your own</p>
                </div>
              </button>
            </div>
          </div>

          {/* Custom color pickers — show when custom selected or colors don't match any preset */}
          {(customOpen || !activePreset) && (
            <div className="space-y-3 rounded-lg border border-dashed p-3">
              <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">
                Custom Colors
              </p>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                {COLOR_FIELDS.map(({ key, label }) => (
                  <ColorInput
                    key={key}
                    label={label}
                    value={colors[key] ?? ""}
                    onChange={(v) => setColor(key, v)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </Section>

      {/* Typography */}
      <Section id="typography" title="Typography">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label className="text-xs">Body Font</Label>
            <select
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={(typography.font_family as string) ?? "Inter"}
              onChange={(e) => setTypo("font_family", e.target.value)}
            >
              {FONT_OPTIONS.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Heading Font</Label>
            <select
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={(typography.heading_font as string) ?? "Inter"}
              onChange={(e) => setTypo("heading_font", e.target.value)}
            >
              {FONT_OPTIONS.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label className="text-xs">
              Base Size: {typography.base_size ?? 16}px
            </Label>
            <input
              type="range"
              min={12}
              max={20}
              step={1}
              value={(typography.base_size as number) ?? 16}
              onChange={(e) => setTypo("base_size", parseInt(e.target.value))}
              className="w-full accent-primary"
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">
              Border Radius: {typography.border_radius ?? 8}px
            </Label>
            <input
              type="range"
              min={0}
              max={20}
              step={1}
              value={(typography.border_radius as number) ?? 8}
              onChange={(e) => setTypo("border_radius", parseInt(e.target.value))}
              className="w-full accent-primary"
            />
          </div>
        </div>
      </Section>

      {/* Components */}
      <Section id="components" title="Components">
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label className="text-xs">Button Style</Label>
            <div className="flex gap-2">
              {BUTTON_STYLES.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setComp("button_style", value)}
                  className={cn(
                    "flex-1 rounded-md border px-3 py-2 text-xs font-medium transition-colors",
                    components.button_style === value
                      ? "border-primary bg-primary/10 text-primary"
                      : "hover:bg-muted"
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <Label className="text-xs">Card Shadow</Label>
            <button
              type="button"
              onClick={() => setComp("card_shadow", !components.card_shadow)}
              className={cn(
                "relative h-6 w-11 rounded-full transition-colors",
                components.card_shadow ? "bg-primary" : "bg-muted-foreground/20"
              )}
            >
              <span
                className={cn(
                  "absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform",
                  components.card_shadow && "translate-x-5"
                )}
              />
            </button>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">Footer Layout</Label>
            <div className="flex gap-2">
              {FOOTER_LAYOUTS.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setComp("footer_layout", value)}
                  className={cn(
                    "flex-1 rounded-md border px-3 py-2 text-xs font-medium transition-colors",
                    components.footer_layout === value
                      ? "border-primary bg-primary/10 text-primary"
                      : "hover:bg-muted"
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Section>
    </div>
  );
}
