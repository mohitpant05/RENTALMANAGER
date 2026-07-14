"use client";

import { useThemeStore } from "@/lib/theme-store";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const brand = useThemeStore((s) => s.theme?.brand);
  const businessName = brand?.business_name || "RentManager";

  return (
    <div className="flex min-h-screen">
      <div className="hidden lg:flex lg:w-1/2 items-center justify-center bg-primary/5 p-12">
        <div className="max-w-md text-center">
          <div className="mb-6 flex justify-center">
            {brand?.logo_url ? (
              <img
                src={brand.logo_url}
                alt={businessName}
                className="h-16 w-auto max-w-[200px] object-contain"
              />
            ) : (
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary text-primary-foreground text-2xl font-bold">
                {businessName.slice(0, 2).toUpperCase()}
              </div>
            )}
          </div>
          <h1 className="text-3xl font-bold tracking-tight">{businessName}</h1>
          <p className="mt-3 text-muted-foreground text-lg">
            {brand?.tagline || "Multi-tenant rental management platform"}
          </p>
        </div>
      </div>
      <div className="flex w-full lg:w-1/2 items-center justify-center p-4">
        {children}
      </div>
    </div>
  );
}
