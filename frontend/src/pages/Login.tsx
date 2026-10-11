import { useNavigate, Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { useApp } from "@/lib/app-store";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { ShieldCheck } from "lucide-react";
import { ThemeToggleButton } from "@/components/app/ThemeToggleButton";

function LoginPage() {
  const { login, user, hydrated } = useApp();
  const navigate = useNavigate();
  const [email, setEmail] = useState("guard1@campus.edu");
  const [password, setPassword] = useState("Guard@123");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (hydrated && user) navigate("/dashboard", { replace: true });
  }, [hydrated, user, navigate]);

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="panel w-full max-w-sm p-6">
        <div className="flex items-center gap-2">
          <span className="grid size-9 place-items-center rounded bg-primary/15 text-primary">
            <ShieldCheck className="size-5" />
          </span>
          <div>
            <h1 className="text-lg font-semibold tracking-tight">Campus Gate AI</h1>
            <p className="font-mono text-[0.65rem] uppercase tracking-[0.18em] text-muted-foreground">
              Entry verification console
            </p>
          </div>
          <ThemeToggleButton className="ml-auto" />
        </div>

        <form
          className="mt-6 space-y-4"
          onSubmit={async (e) => {
            e.preventDefault();
            setError("");
            setSubmitting(true);
            const res = await login(email, password);
            setSubmitting(false);
            if (!res.ok) setError(res.error ?? "Sign-in failed");
            else navigate("/dashboard");
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="email">Email or staff ID</Label>
            <Input id="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          <div className="flex items-center justify-between">
            <Label htmlFor="remember" className="text-sm text-muted-foreground">
              Remember this device
            </Label>
            <Switch id="remember" checked={remember} onCheckedChange={setRemember} />
          </div>
          {error ? (
            <p className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          ) : null}
          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </Button>
        </form>

        <div className="mt-6 space-y-1 border-t border-border pt-4 font-mono text-[0.65rem] text-muted-foreground">
          <p>Demo accounts (seeded by backend/app/seed.py):</p>
          <p>admin@campus.edu / Admin@123</p>
          <p>guard1@campus.edu / Guard@123</p>
        </div>

        <div className="mt-4 flex items-center justify-between border-t border-border pt-4 text-xs text-muted-foreground">
          <Link to="/register" className="underline underline-offset-2">
            Student? Register your vehicle
          </Link>
          <Link to="/portal" className="underline underline-offset-2">
            Check registration status
          </Link>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
