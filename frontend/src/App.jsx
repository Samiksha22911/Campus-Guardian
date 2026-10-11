import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import AppLayout from "@/layouts/AppLayout";
import NotFound from "@/pages/NotFound";

// Each page is its own chunk, so the first load only downloads what it needs.
const Login = lazy(() => import("@/pages/Login"));
const Register = lazy(() => import("@/pages/Register"));
const Portal = lazy(() => import("@/pages/Portal"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Live = lazy(() => import("@/pages/Live"));
const Students = lazy(() => import("@/pages/Students"));
const Vehicles = lazy(() => import("@/pages/Vehicles"));
const Enrollment = lazy(() => import("@/pages/Enrollment"));
const Logs = lazy(() => import("@/pages/Logs"));
const Alerts = lazy(() => import("@/pages/Alerts"));
const Analytics = lazy(() => import("@/pages/Analytics"));
const Settings = lazy(() => import("@/pages/Settings"));
const Profile = lazy(() => import("@/pages/Profile"));
const Audit = lazy(() => import("@/pages/Audit"));

/** Sets the browser tab title for a page (replaces TanStack's per-route `head`). */
function Page({ title, children }) {
  useEffect(() => {
    document.title = title;
  }, [title]);
  return children;
}

function Loading() {
  return (
    <div className="grid min-h-screen place-items-center font-mono text-sm text-muted-foreground">
      Loading…
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* Public pages */}
        <Route path="/login" element={<Page title="Sign in — Campus Gate AI Security Console"><Login /></Page>} />
        <Route path="/register" element={<Page title="Register your vehicle — Campus Gate AI"><Register /></Page>} />
        <Route path="/portal" element={<Page title="Student portal — Campus Gate AI"><Portal /></Page>} />

        {/* Staff console - AppLayout handles the login guard + role check */}
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<Page title="Security Dashboard — Campus Guardian AI"><Dashboard /></Page>} />
          <Route path="/live" element={<Page title="Live Gate Monitoring — Campus Gate AI"><Live /></Page>} />
          <Route path="/students" element={<Page title="Student Management — Campus Gate AI"><Students /></Page>} />
          <Route path="/vehicles" element={<Page title="Vehicle Management — Campus Gate AI"><Vehicles /></Page>} />
          <Route path="/enrollment" element={<Page title="Enrollment Wizard — Campus Guardian AI"><Enrollment /></Page>} />
          <Route path="/logs" element={<Page title="Entry Logs — Campus Gate AI"><Logs /></Page>} />
          <Route path="/alerts" element={<Page title="Alerts — Campus Guardian AI"><Alerts /></Page>} />
          <Route path="/analytics" element={<Page title="Analytics — Campus Guardian AI"><Analytics /></Page>} />
          <Route path="/settings" element={<Page title="System Settings — Campus Gate AI"><Settings /></Page>} />
          <Route path="/profile" element={<Page title="My Profile — Campus Gate AI"><Profile /></Page>} />
          <Route path="/audit" element={<Page title="Audit Logs — Campus Gate AI"><Audit /></Page>} />
        </Route>

        <Route path="*" element={<Page title="Page not found — Campus Guardian AI"><NotFound /></Page>} />
      </Routes>
    </Suspense>
  );
}
