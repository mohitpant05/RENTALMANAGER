"use client";

import { useEffect } from "react";
import { useTenantStore } from "@/lib/tenant-store";
import { useThemeStore } from "@/lib/theme-store";

const STYLE_ID = "tenant-theme-vars";

function hexToOklch(hex: string): string | null {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex);
  if (!m) return null;
  let r = parseInt(m[1], 16) / 255;
  let g = parseInt(m[2], 16) / 255;
  let b = parseInt(m[3], 16) / 255;
  r = r > 0.04045 ? Math.pow((r + 0.055) / 1.055, 2.4) : r / 12.92;
  g = g > 0.04045 ? Math.pow((g + 0.055) / 1.055, 2.4) : g / 12.92;
  b = b > 0.04045 ? Math.pow((b + 0.055) / 1.055, 2.4) : b / 12.92;
  const l_ = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b;
  const m_ = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b;
  const s_ = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b;
  const l3 = Math.cbrt(l_);
  const m3 = Math.cbrt(m_);
  const s3 = Math.cbrt(s_);
  const L = 0.2104542553 * l3 + 0.7936177850 * m3 - 0.0040720468 * s3;
  const a = 1.9779984951 * l3 - 2.4285922050 * m3 + 0.4505937099 * s3;
  const bOk = 0.0259040371 * l3 + 0.7827717662 * m3 - 0.8086757660 * s3;
  const C = Math.sqrt(a * a + bOk * bOk);
  const h = (Math.atan2(bOk, a) * 180) / Math.PI;
  return `oklch(${L.toFixed(3)} ${C.toFixed(3)} ${h < 0 ? h + 360 : h > 360 ? h - 360 : h})`;
}

function contrastForeground(hex: string): string {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex);
  if (!m) return "oklch(0.985 0 0)";
  const r = parseInt(m[1], 16) / 255;
  const g = parseInt(m[2], 16) / 255;
  const b = parseInt(m[3], 16) / 255;
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return lum > 0.5 ? "oklch(0.145 0 0)" : "oklch(0.985 0 0)";
}

function darkenOklch(oklch: string, amount: number): string {
  const m = /oklch\(([\d.]+)\s+([\d.]+)\s+([\d.-]+)\)/.exec(oklch);
  if (!m) return oklch;
  const L = Math.max(0, parseFloat(m[1]) - amount);
  return `oklch(${L.toFixed(3)} ${m[2]} ${m[3]})`;
}

function lightenOklch(oklch: string, amount: number): string {
  const m = /oklch\(([\d.]+)\s+([\d.]+)\s+([\d.-]+)\)/.exec(oklch);
  if (!m) return oklch;
  const L = Math.min(1, parseFloat(m[1]) + amount);
  return `oklch(${L.toFixed(3)} ${m[2]} ${m[3]})`;
}

const COLOR_MAP: Record<string, string[]> = {
  primary: ["--primary"],
  secondary: ["--secondary"],
  accent: ["--accent"],
  background: ["--background"],
  surface: ["--card", "--popover"],
  text_primary: ["--foreground", "--card-foreground", "--popover-foreground"],
  text_secondary: ["--muted-foreground"],
  error: ["--destructive"],
  success: ["--chart-1"],
};

const FOREGROUND_PAIRS: Record<string, string> = {
  "--primary": "--primary-foreground",
  "--secondary": "--secondary-foreground",
  "--accent": "--accent-foreground",
  "--destructive": "--destructive-foreground",
};

function buildThemeCSS(theme: {
  colors: Record<string, string>;
  typography: Record<string, string | number>;
}): string {
  const lightVars: string[] = [];
  const darkVars: string[] = [];

  for (const [key, vars] of Object.entries(COLOR_MAP)) {
    const hex = theme.colors[key];
    if (!hex) continue;
    const oklch = hexToOklch(hex);
    if (!oklch) continue;
    const fg = contrastForeground(hex);

    for (const v of vars) {
      lightVars.push(`${v}: ${oklch};`);
      if (v === "--background") {
        darkVars.push(`${v}: ${darkenOklch(oklch, 0.7)};`);
      } else if (v === "--foreground" || v === "--card-foreground" || v === "--popover-foreground") {
        darkVars.push(`${v}: ${lightenOklch(oklch, 0.7)};`);
      } else if (v === "--card" || v === "--popover") {
        darkVars.push(`${v}: ${darkenOklch(oklch, 0.6)};`);
      } else if (v === "--muted-foreground") {
        darkVars.push(`${v}: ${lightenOklch(oklch, 0.3)};`);
      } else {
        darkVars.push(`${v}: ${oklch};`);
      }

      const fgPair = FOREGROUND_PAIRS[v];
      if (fgPair) {
        lightVars.push(`${fgPair}: ${fg};`);
        darkVars.push(`${fgPair}: ${fg};`);
      }
    }
  }

  if (theme.typography.border_radius != null) {
    const rv = `${theme.typography.border_radius}px`;
    lightVars.push(`--radius: ${rv};`);
    darkVars.push(`--radius: ${rv};`);
  }

  if (lightVars.length === 0) return "";

  return `:root {\n  ${lightVars.join("\n  ")}\n}\n.dark {\n  ${darkVars.join("\n  ")}\n}`;
}

function applyThemeToDOM(theme: {
  colors: Record<string, string>;
  typography: Record<string, string | number>;
}) {
  let el = document.getElementById(STYLE_ID);
  const css = buildThemeCSS(theme);
  if (!css) {
    el?.remove();
    return;
  }
  if (!el) {
    el = document.createElement("style");
    el.id = STYLE_ID;
    document.head.appendChild(el);
  }
  el.textContent = css;
}

function clearThemeFromDOM() {
  document.getElementById(STYLE_ID)?.remove();
}

export function TenantThemeProvider() {
  const resolved = useTenantStore((s) => s.resolved);
  const slug = useTenantStore((s) => s.slug);
  const setTheme = useThemeStore((s) => s.setTheme);

  useEffect(() => {
    if (!resolved || !slug) return;

    let cancelled = false;

    async function load() {
      try {
        const res = await fetch("/api/tenancy/theme", {
          headers: { "X-Tenant-ID": slug! },
        });
        if (!res.ok || cancelled) return;
        const data = await res.json();
        if (cancelled) return;
        setTheme({
          brand: data.brand ?? {},
          colors: data.colors ?? {},
          typography: data.typography ?? {},
          components: data.components ?? {},
        });
        applyThemeToDOM({
          colors: data.colors ?? {},
          typography: data.typography ?? {},
        });
      } catch {
        // theme fetch failed — keep defaults
      }
    }

    load();

    return () => {
      cancelled = true;
      clearThemeFromDOM();
    };
  }, [resolved, slug, setTheme]);

  return null;
}
