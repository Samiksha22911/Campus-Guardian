import { useState } from "react";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import {
  Activity,
  BarChart3,
  Bell,
  Car,
  ChevronLeft,
  ClipboardList,
  History,
  LayoutDashboard,
  LogOut,
  Menu,
  ShieldAlert,
  Settings,
  UserCircle,
  UserPlus,
  Users,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { ROLE_LABEL, can, useApp } from "@/lib/app-store";
import { ThemeToggleButton } from "@/components/app/ThemeToggleButton";
import { GATES, fmtTime } from "@/lib/campus-data";
import { Badge2 } from "./shared";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import { Button } from "@/components/ui/button";

const NAV = [
  {
    to: "/dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    perm: "dashboard",
  },
  {
    to: "/live",
    label: "Live Gate",
    icon: Activity,
    perm: "live",
  },
  {
    to: "/students",
    label: "Students",
    icon: Users,
    perm: "students",
  },
  {
    to: "/vehicles",
    label: "Vehicles",
    icon: Car,
    perm: "vehicles",
  },
  {
    to: "/enrollment",
    label: "Enrollment",
    icon: UserPlus,
    perm: "enrollment",
  },
  {
    to: "/logs",
    label: "Entry Logs",
    icon: ClipboardList,
    perm: "logs",
  },
  {
    to: "/alerts",
    label: "Alerts",
    icon: ShieldAlert,
    perm: "alerts",
  },
  {
    to: "/analytics",
    label: "Analytics",
    icon: BarChart3,
    perm: "analytics",
  },
  {
    to: "/audit",
    label: "Audit Logs",
    icon: History,
    perm: "audit",
  },
  {
    to: "/settings",
    label: "Settings",
    icon: Settings,
    perm: "settings",
  },
];

export function AppShell({ children }) {
  const {
    user,
    logout,
    aiOnline,
    gate,
    setGate,
    alerts,
  } = useApp();

  const navigate = useNavigate();

  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });

  const [collapsed, setCollapsed] = useState(false);
  const [drawer, setDrawer] = useState(false);

  const openAlerts = alerts.filter(
    (alert) => alert.status === "open"
  );

  const navigationItems = NAV.filter((item) =>
    can(user?.role, item.perm)
  );

  const renderNavigation = (compact) => {
    return (
      <nav className="flex flex-col gap-0.5 p-2">
        {navigationItems.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.to;

          return (
            <Link
              key={item.to}
              to={item.to}
              onClick={() => setDrawer(false)}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-primary/12 text-primary"
                  : "text-muted-foreground hover:bg-surface-2 hover:text-foreground"
              )}
            >
              <Icon className="size-4 shrink-0" />

              {!compact && (
                <span>{item.label}</span>
              )}

              {!compact &&
              item.perm === "alerts" &&
              openAlerts.length > 0 ? (
                <span className="ml-auto rounded-full bg-destructive px-1.5 font-mono text-[0.6rem] text-destructive-foreground">
                  {openAlerts.length}
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>
    );
  };

  const handleLogout = () => {
    logout();
    navigate({ to: "/login" });
  };

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">

      {/* Header */}
      <header className="sticky top-0 z-40 flex flex-wrap items-center gap-3 border-b border-border bg-surface/95 px-3 py-2 backdrop-blur">

        {/* Mobile menu */}
        <button
          className="rounded-md p-1.5 text-muted-foreground hover:bg-surface-2 lg:hidden"
          onClick={() => setDrawer((value) => !value)}
          aria-label="Toggle navigation"
        >
          <Menu className="size-4" />
        </button>

        {/* Logo */}
        <Link
          to="/dashboard"
          className="flex items-center gap-2"
        >
          <span className="grid size-7 place-items-center rounded bg-primary/15 font-mono text-xs font-bold text-primary">
            CG
          </span>

          <span className="font-semibold tracking-tight">
            Campus Gate AI
          </span>
        </Link>

        {/* AI Status */}
        <Badge2 tone={aiOnline ? "success" : "danger"}>
          <span
            className={cn(
              "size-1.5 rounded-full",
              aiOnline
                ? "bg-success"
                : "bg-destructive live-dot"
            )}
          />

          {aiOnline
            ? "AI Online"
            : "AI Offline — Manual Mode"}
        </Badge2>

        {/* Gate Selector */}
        <select
          value={gate}
          onChange={(event) =>
            setGate(event.target.value)
          }
          className="hidden rounded-md border border-border bg-surface-2 px-2 py-1 font-mono text-xs text-foreground sm:block"
          aria-label="Gate selector"
        >
          {GATES.map((item) => (
            <option
              key={item.id}
              value={item.label}
            >
              {item.label}
            </option>
          ))}
        </select>

        <div className="ml-auto flex items-center gap-2">

          {/* Theme toggle */}
          <ThemeToggleButton />

          {/* Notifications */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className="relative rounded-md p-2 text-muted-foreground hover:bg-surface-2"
                aria-label="Notifications"
              >
                <Bell className="size-4" />

                {openAlerts.length > 0 ? (
                  <span className="absolute -right-0.5 -top-0.5 grid min-w-4 place-items-center rounded-full bg-destructive px-1 font-mono text-[0.6rem] text-destructive-foreground">
                    {openAlerts.length}
                  </span>
                ) : null}
              </button>
            </DropdownMenuTrigger>

            <DropdownMenuContent
              align="end"
              className="w-80"
            >
              <DropdownMenuLabel>
                Open alerts ({openAlerts.length})
              </DropdownMenuLabel>

              <DropdownMenuSeparator />

              {openAlerts.slice(0, 5).map((alert) => (
                <DropdownMenuItem
                  key={alert.id}
                  onClick={() =>
                    navigate({ to: "/alerts" })
                  }
                >
                  <div className="flex w-full flex-col gap-0.5">
                    <span className="flex items-center justify-between gap-2 text-xs">
                      <span className="font-medium">
                        {alert.type}
                      </span>

                      <span className="font-mono text-[0.6rem] text-muted-foreground">
                        {fmtTime(alert.ts)}
                      </span>
                    </span>

                    <span className="text-[0.7rem] text-muted-foreground">
                      {alert.plate ?? alert.gate}
                    </span>
                  </div>
                </DropdownMenuItem>
              ))}

              {openAlerts.length === 0 ? (
                <div className="px-2 py-3 text-xs text-muted-foreground">
                  No open alerts.
                </div>
              ) : null}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-2 rounded-md border border-border bg-surface-2 px-2 py-1.5 text-left">
                <span className="text-xs font-medium">
                  {user?.name}
                </span>

                <Badge2 tone="primary">
                  {user
                    ? ROLE_LABEL[user.role]
                    : ""}
                </Badge2>
              </button>
            </DropdownMenuTrigger>

            <DropdownMenuContent align="end">
              <DropdownMenuLabel>
                {user?.email}
              </DropdownMenuLabel>

              <DropdownMenuSeparator />

              <DropdownMenuItem onClick={() => navigate({ to: "/profile" })}>
                <UserCircle className="mr-2 size-4" />
                My profile
              </DropdownMenuItem>

              <DropdownMenuSeparator />

              <DropdownMenuItem onClick={handleLogout}>
                <LogOut className="mr-2 size-4" />
                Log out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      {/* Main Layout */}
      <div className="flex flex-1">

        {/* Desktop Sidebar */}
        <aside
          className={cn(
            "hidden shrink-0 border-r border-border bg-surface/60 lg:block",
            collapsed
              ? "w-[60px]"
              : "w-56"
          )}
        >
          <div className="sticky top-[53px]">

            {renderNavigation(collapsed)}

            <Button
              variant="ghost"
              size="sm"
              className="m-2 w-[calc(100%-1rem)] justify-start text-muted-foreground"
              onClick={() =>
                setCollapsed(
                  (value) => !value
                )
              }
            >
              <ChevronLeft
                className={cn(
                  "size-4 transition-transform",
                  collapsed && "rotate-180"
                )}
              />

              {!collapsed && (
                <span className="ml-2">
                  Collapse
                </span>
              )}
            </Button>
          </div>
        </aside>

        {/* Mobile Drawer */}
        {drawer ? (
          <div
            className="fixed inset-0 z-30 lg:hidden"
            onClick={() => setDrawer(false)}
          >
            <div className="absolute inset-0 bg-background/70" />

            <div
              className="absolute inset-y-0 left-0 top-[49px] w-60 border-r border-border bg-surface"
              onClick={(event) =>
                event.stopPropagation()
              }
            >
              {renderNavigation(false)}
            </div>
          </div>
        ) : null}

        {/* Page Content */}
        <main className="min-w-0 flex-1 pb-16 lg:pb-0">
          {children}
        </main>
      </div>

      {/* Mobile Bottom Navigation */}
      <nav className="fixed inset-x-0 bottom-0 z-30 flex justify-around border-t border-border bg-surface/95 py-1 backdrop-blur lg:hidden">
        {navigationItems.slice(0, 5).map((item) => {
          const Icon = item.icon;
          const active = pathname === item.to;

          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "flex flex-col items-center gap-0.5 px-2 py-1 text-[0.6rem]",
                active
                  ? "text-primary"
                  : "text-muted-foreground"
              )}
            >
              <Icon className="size-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

export function PageHeader({
  title,
  subtitle,
  action,
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3 border-b border-border px-4 py-3">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">
          {title}
        </h1>

        {subtitle ? (
          <p className="text-sm text-muted-foreground">
            {subtitle}
          </p>
        ) : null}
      </div>

      {action}
    </div>
  );
}
