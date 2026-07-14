"use client";

import Link from "next/link";
import { useAuthStore } from "@/lib/auth-store";
import { useThemeStore } from "@/lib/theme-store";
import { Button } from "@/components/ui/button";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated } = useAuthStore();
  const brand = useThemeStore((s) => s.theme?.brand);
  const businessName = brand?.business_name || "RentManager";

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-3 py-3 sm:px-4 sm:py-4">
          <Link href="/browse" className="flex items-center gap-2 text-lg font-bold sm:text-xl">
            {brand?.logo_url ? (
              <img
                src={brand.logo_url}
                alt={businessName}
                className="h-7 w-auto max-w-[120px] object-contain sm:h-8"
              />
            ) : null}
            <span>{businessName}</span>
          </Link>
          <nav className="flex items-center gap-2 sm:gap-4">
            {isAuthenticated ? (
              <>
                {user?.user_type === "admin" || user?.user_type === "staff" ? (
                  <Link
                    href="/admin"
                    className="text-xs sm:text-sm font-medium text-primary hover:underline"
                  >
                    Dashboard
                  </Link>
                ) : (
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
                  </>
                )}
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
      {children}
    </div>
  );
}
