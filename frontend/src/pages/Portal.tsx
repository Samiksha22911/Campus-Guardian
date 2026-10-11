import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge2, statusTone } from "@/components/app/shared";
import { ShieldCheck, LogOut } from "lucide-react";
import { ThemeToggleButton } from "@/components/app/ThemeToggleButton";
import { api, getStudentToken, setStudentToken } from "@/lib/api-client";

const STATUS_LABEL = {
  active: "Approved — you can enter through the AI gate",
  pending: "Pending approval — a staff member hasn't reviewed this yet",
  inactive: "Inactive — contact campus admin/security",
  rejected: "Registration rejected — contact campus admin/security",
};

function StudentPortalPage() {
  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [studentId, setStudentId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function loadMe() {
    if (!getStudentToken()) {
      setLoading(false);
      return;
    }
    try {
      const me = await api.studentMe();
      setStudent(me);
    } catch {
      setStudentToken(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMe();
  }, []);

  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const res = await api.studentLogin(studentId, password);
      setStudentToken(res.access_token);
      setStudent(res.student);
    } catch (err) {
      setError(err.message || "Sign-in failed");
    } finally {
      setSubmitting(false);
    }
  }

  function handleLogout() {
    setStudentToken(null);
    setStudent(null);
  }

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">Loading…</div>;
  }

  if (!student) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4 py-10">
        <div className="panel w-full max-w-sm p-6">
          <div className="flex items-center gap-2">
            <span className="grid size-9 place-items-center rounded bg-primary/15 text-primary">
              <ShieldCheck className="size-5" />
            </span>
            <div>
              <h1 className="text-lg font-semibold tracking-tight">Student portal</h1>
              <p className="font-mono text-[0.65rem] uppercase tracking-[0.18em] text-muted-foreground">
                Check your registration status
              </p>
            </div>
            <ThemeToggleButton className="ml-auto" />
          </div>

          <form className="mt-6 space-y-4" onSubmit={handleLogin}>
            <div className="space-y-1.5">
              <Label htmlFor="student_id">Student ID</Label>
              <Input id="student_id" value={studentId} onChange={(e) => setStudentId(e.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
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

          <div className="mt-6 flex items-center justify-between border-t border-border pt-4 text-xs text-muted-foreground">
            <Link to="/register" className="underline underline-offset-2">
              Not registered yet?
            </Link>
            <Link to="/login" className="underline underline-offset-2">
              Staff login
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const vehicle = student.vehicles?.[0];

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="panel w-full max-w-md p-6">
        <div className="flex items-center gap-2">
          <span className="grid size-9 place-items-center rounded bg-primary/15 text-primary">
            <ShieldCheck className="size-5" />
          </span>
          <div>
            <h1 className="text-lg font-semibold tracking-tight">{student.name}</h1>
            <p className="font-mono text-[0.65rem] uppercase tracking-[0.18em] text-muted-foreground">
              {student.student_id} · {student.department}
            </p>
          </div>
          <Button variant="ghost" size="icon" className="ml-auto" onClick={handleLogout} title="Sign out">
            <LogOut className="size-4" />
          </Button>
        </div>

        <div className="mt-6 space-y-3">
          <div className="rounded-md border border-border bg-surface-2 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Profile status</p>
            <div className="mt-1 flex items-center gap-2">
              <Badge2 tone={student.status === "rejected" ? "danger" : statusTone(student.status)}>
                {student.status}
              </Badge2>
              <span className="text-sm">{STATUS_LABEL[student.status] ?? ""}</span>
            </div>
          </div>

          {vehicle ? (
            <div className="rounded-md border border-border bg-surface-2 p-3">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">Vehicle</p>
              <p className="mt-1 font-mono text-sm">{vehicle.registration_number}</p>
              <p className="text-xs text-muted-foreground">
                {vehicle.vehicle_type} {vehicle.make ? `· ${vehicle.make}` : ""} {vehicle.model ?? ""}
              </p>
              <div className="mt-2 flex items-center gap-2">
                <Badge2 tone={vehicle.is_blocklisted ? "danger" : statusTone(vehicle.status)}>
                  {vehicle.is_blocklisted ? "blocklisted" : vehicle.status}
                </Badge2>
              </div>
            </div>
          ) : null}

          <div className="rounded-md border border-border bg-surface-2 p-3 text-xs text-muted-foreground">
            {student.face_enrolled
              ? "A face photo is on file for gate verification."
              : "No face photo on file yet — gate entry may require manual verification until one is added."}
          </div>
        </div>
      </div>
    </div>
  );
}

export default StudentPortalPage;
