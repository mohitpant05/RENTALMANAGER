"use client";

import { useState } from "react";
import { ChevronDown, Image as ImageIcon } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { ColorInput } from "./color-input";

interface SectionProps {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

function Section({ title, defaultOpen = false, children }: SectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-lg border">
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
  colors: Record<string, string>;
  typography: Record<string, string | number>;
  components: Record<string, string | boolean>;
  onColorsChange: (colors: Record<string, string>) => void;
  onTypographyChange: (typography: Record<string, string | number>) => void;
  onComponentsChange: (components: Record<string, string | boolean>) => void;
}

export function ThemeForm({
  colors,
  typography,
  components,
  onColorsChange,
  onTypographyChange,
  onComponentsChange,
}: ThemeFormProps) {
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
      <Section title="Brand">
        <div className="flex items-center gap-3 rounded-lg border border-dashed p-4">
          <ImageIcon className="h-8 w-8 text-muted-foreground" />
          <div>
            <p className="text-sm font-medium">Logo & Favicon</p>
            <p className="text-xs text-muted-foreground">
              Upload available after file storage is configured
            </p>
          </div>
        </div>
      </Section>

      {/* Colors */}
      <Section title="Colors" defaultOpen>
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
      </Section>

      {/* Typography */}
      <Section title="Typography">
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
      <Section title="Components">
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
