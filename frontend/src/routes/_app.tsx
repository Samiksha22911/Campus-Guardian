import { Outlet, createFileRoute, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect } from "react";
import { AppShell } from "@/components/app/AppShell";
import { can, useApp } from "@/lib/app-store";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/_app")({
  component: AppLayout,
});

const PERM_BY_PATH: Record<string, string> = {
  "/dashboard": "dashboard",
  "/live": "live",
  "/students": "students",
  "/vehicles": "vehicles",
  "/enrollment": "enrollment",
  "/logs": "logs",
  "/alerts": "alerts",
  "/analytics": "analytics",
  "/settings": "settings",
  "/profile": "profile",
  "/audit": "audit",
};

function AppLayout() {
  const { user, hydrated } = useApp();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  useEffect(() => {
    if (hydrated && !user) navigate({ to: "/login", replace: true });
  }, [hydrated, user, navigate]);

  if (!hydrated || !user) {
    return (
      <div className="grid min-h-screen place-items-center font-mono text-sm text-muted-foreground">
        Authenticating…
      </div>
    );
  }

  const perm = PERM_BY_PATH[pathname];
  if (perm && !can(user.role, perm)) {
    return (
      <AppShell>
        <div className="grid min-h-[60vh] place-items-center px-4 text-center">
          <div>
            <p className="font-mono text-5xl font-semibold text-destructive">403</p>
            <h1 className="mt-3 text-lg font-semibold">Not authorised</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Your role does not have access to this page.
            </p>
            <Button className="mt-5" onClick={() => navigate({ to: "/dashboard" })}>
              Back to dashboard
            </Button>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}
