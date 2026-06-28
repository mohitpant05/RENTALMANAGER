"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Banknote,
  Bell,
  Box,
  CalendarDays,
  Clock,
  LayoutDashboard,
  Palette,
  RotateCcw,
  Settings,
  Star,
  Users,
  Sun,
  Moon,
  LogOut,
} from "lucide-react";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/use-auth";
import { usePermissions } from "@/hooks/use-permissions";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface NavItem {
  href: string;
  icon: typeof LayoutDashboard;
  label: string;
  adminOnly?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/admin", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/admin/resources", icon: Box, label: "Resources" },
  { href: "/admin/bookings", icon: CalendarDays, label: "Bookings" },
  { href: "/admin/booking-slots", icon: Clock, label: "Slots" },
  { href: "/admin/payouts", icon: Banknote, label: "Payouts" },
  { href: "/admin/refunds", icon: RotateCcw, label: "Refunds" },
  { href: "/admin/reviews", icon: Star, label: "Reviews" },
  { href: "/admin/staff", icon: Users, label: "Staff" },
  { href: "/admin/notifications", icon: Bell, label: "Notifications" },
  { href: "/admin/theming", icon: Palette, label: "Theming", adminOnly: true },
  { href: "/admin/settings", icon: Settings, label: "Settings" },
];

export function IconRail() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const { logout, user } = useAuth();
  const { canAccessNav } = usePermissions();

  const initials = user?.full_name
    ?.split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase() || "?";

  return (
    <TooltipProvider delayDuration={150}>
      <div className="flex h-full w-[60px] flex-col items-center border-r bg-background py-4">
        <div className="mb-8">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground text-sm font-bold">
            RM
          </div>
        </div>

        <nav className="flex flex-1 flex-col items-center gap-2">
          {NAV_ITEMS.filter(({ href, adminOnly }) => {
            if (adminOnly && user?.user_type !== "admin") return false;
            return canAccessNav(href);
          }).map(({ href, icon: Icon, label }) => {
            const isActive = pathname.startsWith(href);
            return (
              <Tooltip key={href}>
                <TooltipTrigger asChild>
                  <Link
                    href={href}
                    className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-lg transition-colors",
                      isActive
                        ? "bg-accent text-accent-foreground"
                        : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground"
                    )}
                  >
                    <Icon className="h-5 w-5" />
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right">{label}</TooltipContent>
              </Tooltip>
            );
          })}
        </nav>

        <div className="flex flex-col items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                className="relative flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground transition-colors"
              >
                <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="right">Toggle theme</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                onClick={logout}
                className="flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="right">Logout</TooltipContent>
          </Tooltip>
          <Avatar className="h-8 w-8">
            <AvatarFallback className="text-xs">{initials}</AvatarFallback>
          </Avatar>
        </div>
      </div>
    </TooltipProvider>
  );
}
