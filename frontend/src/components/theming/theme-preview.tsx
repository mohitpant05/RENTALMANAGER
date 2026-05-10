"use client";

interface ThemePreviewProps {
  colors: Record<string, string>;
  typography: Record<string, string | number>;
  components: Record<string, string | boolean>;
}

export function ThemePreview({ colors, typography, components }: ThemePreviewProps) {
  const radius = `${typography.border_radius ?? 8}px`;
  const font = (typography.font_family as string) || "Inter";
  const headingFont = (typography.heading_font as string) || font;
  const baseSize = `${typography.base_size ?? 16}px`;

  const btnRadius =
    components.button_style === "pill"
      ? "9999px"
      : components.button_style === "square"
        ? "0px"
        : radius;

  return (
    <div
      className="rounded-xl border overflow-hidden"
      style={{
        fontFamily: font,
        fontSize: baseSize,
        borderRadius: radius,
      }}
    >
      {/* Nav mock */}
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ backgroundColor: colors.surface || "#ffffff" }}
      >
        <span
          className="text-sm font-bold"
          style={{ color: colors.text_primary || "#111", fontFamily: headingFont }}
        >
          Your Brand
        </span>
        <div className="flex gap-2">
          <div
            className="h-2 w-8 rounded-full"
            style={{ backgroundColor: colors.text_secondary || "#666" }}
          />
          <div
            className="h-2 w-8 rounded-full"
            style={{ backgroundColor: colors.text_secondary || "#666" }}
          />
        </div>
      </div>

      {/* Hero mock */}
      <div
        className="px-4 py-8 text-center"
        style={{ backgroundColor: colors.primary || "#3b82f6" }}
      >
        <p
          className="text-lg font-bold"
          style={{ color: "#ffffff", fontFamily: headingFont }}
        >
          Find & Book
        </p>
        <p className="mt-1 text-xs" style={{ color: "rgba(255,255,255,0.8)" }}>
          Your marketplace headline
        </p>
        <div
          className="mx-auto mt-3 h-8 w-32"
          style={{
            backgroundColor: colors.accent || "#f59e0b",
            borderRadius: btnRadius,
          }}
        />
      </div>

      {/* Card mock */}
      <div
        className="p-4"
        style={{ backgroundColor: colors.background || "#f9fafb" }}
      >
        <div
          className="p-3"
          style={{
            backgroundColor: colors.surface || "#ffffff",
            borderRadius: radius,
            boxShadow: components.card_shadow ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
            border: "1px solid rgba(0,0,0,0.06)",
          }}
        >
          <div
            className="mb-2 h-16 rounded"
            style={{
              backgroundColor: colors.secondary || "#e5e7eb",
              borderRadius: `calc(${radius} - 4px)`,
            }}
          />
          <p
            className="text-sm font-semibold"
            style={{ color: colors.text_primary || "#111", fontFamily: headingFont }}
          >
            Resource Name
          </p>
          <p
            className="mt-0.5 text-xs"
            style={{ color: colors.text_secondary || "#666" }}
          >
            $50 / day
          </p>
          <button
            className="mt-2 w-full py-1.5 text-xs font-medium text-white"
            style={{
              backgroundColor: colors.primary || "#3b82f6",
              borderRadius: btnRadius,
            }}
          >
            Book Now
          </button>
        </div>

        {/* Color swatches */}
        <div className="mt-3 flex gap-1.5">
          {["primary", "secondary", "accent", "success", "error"].map((key) => (
            <div key={key} className="flex flex-col items-center gap-0.5">
              <div
                className="h-5 w-5 rounded-full border"
                style={{ backgroundColor: colors[key] || "#ccc" }}
              />
              <span className="text-[9px]" style={{ color: colors.text_secondary || "#666" }}>
                {key.slice(0, 3)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
