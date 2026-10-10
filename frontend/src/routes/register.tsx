import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ShieldCheck } from "lucide-react";
import { ThemeToggleButton } from "@/components/app/ThemeToggleButton";
import { api, setStudentToken } from "@/lib/api-client";

export const Route = createFileRoute("/register")({
  head: () => ({
    meta: [
      { title: "Register your vehicle — Campus Gate AI" },
      {
        name: "description",
        content: "Self-register your student profile and vehicle for automated campus gate entry.",
      },
    ],
  }),
  component: RegisterPage,
});

const sel = "rounded-md border border-border bg-surface-2 px-2 py-1.5 font-mono text-xs w-full";

const DEPARTMENTS = [
  "Computer Science",
  "Information Technology",
  "Electronics & Communication",
  "Electrical Engineering",
  "Mechanical Engineering",
  "Civil Engineering",
  "Other",
];

const VEHICLE_TYPES = ["Car", "Bike", "Scooty", "Other"];

function RegisterPage() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    student_id: "",
    name: "",
    department: DEPARTMENTS[0],
    course: "",
    year: "1",
    email: "",
    phone: "",
    password: "",
    registration_number: "",
    vehicle_type: VEHICLE_TYPES[0],
    make: "",
    model: "",
    color: "",
  });
  const [consent, setConsent] = useState(false);
  const [photo, setPhoto] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (form.password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    const fd = new FormData();
    Object.entries(form).forEach(([key, value]) => {
      if (value !== "" && value !== null && value !== undefined) fd.append(key, value);
    });
    fd.append("biometric_consent", String(consent));
    if (photo) fd.append("photo", photo);

    setSubmitting(true);
    try {
      const res = await api.registerStudent(fd);
      setStudentToken(res.access_token);
      setDone(true);
    } catch (err) {
      setError(err.message || "Registration failed. Please check your details and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4 py-10">
        <div className="panel w-full max-w-sm p-6 text-center">
          <span className="mx-auto grid size-10 place-items-center rounded-full bg-primary/15 text-primary">
            <ShieldCheck className="size-5" />
          </span>
          <h1 className="mt-3 text-lg font-semibold tracking-tight">Registration submitted</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Your profile and vehicle are now <span className="font-medium text-foreground">pending approval</span>{" "}
            by campus admin/security. You won't be able to enter through the AI gate until it's approved.
          </p>
          <Button className="mt-6 w-full" onClick={() => navigate({ to: "/portal" })}>
            Check my status
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="panel w-full max-w-lg p-6">
        <div className="flex items-center gap-2">
          <span className="grid size-9 place-items-center rounded bg-primary/15 text-primary">
            <ShieldCheck className="size-5" />
          </span>
          <div>
            <h1 className="text-lg font-semibold tracking-tight">Register your vehicle</h1>
            <p className="font-mono text-[0.65rem] uppercase tracking-[0.18em] text-muted-foreground">
              Student self-registration
            </p>
          </div>
          <ThemeToggleButton className="ml-auto" />
        </div>

        <form className="mt-6 grid grid-cols-2 gap-3" onSubmit={handleSubmit}>
          <div className="col-span-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Your details
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="student_id">Student ID</Label>
            <Input id="student_id" value={form.student_id} onChange={set("student_id")} required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="name">Full name</Label>
            <Input id="name" value={form.name} onChange={set("name")} required />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="department">Department</Label>
            <select id="department" className={sel} value={form.department} onChange={set("department")}>
              {DEPARTMENTS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="year">Year</Label>
            <select id="year" className={sel} value={form.year} onChange={set("year")}>
              {[1, 2, 3, 4, 5].map((y) => (
                <option key={y} value={y}>
                  Year {y}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="email">Email (optional)</Label>
            <Input id="email" type="email" value={form.email} onChange={set("email")} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="phone">Phone (optional)</Label>
            <Input id="phone" value={form.phone} onChange={set("phone")} />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="password">Choose a password</Label>
            <Input
              id="password"
              type="password"
              value={form.password}
              onChange={set("password")}
              minLength={6}
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="photo">Face photo (optional, recommended)</Label>
            <Input id="photo" type="file" accept="image/*" onChange={(e) => setPhoto(e.target.files?.[0] ?? null)} />
          </div>

          <div className="col-span-2 mt-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Your vehicle
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="registration_number">Number plate</Label>
            <Input
              id="registration_number"
              value={form.registration_number}
              onChange={set("registration_number")}
              placeholder="MP07AB1234"
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="vehicle_type">Vehicle type</Label>
            <select id="vehicle_type" className={sel} value={form.vehicle_type} onChange={set("vehicle_type")}>
              {VEHICLE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="make">Make (optional)</Label>
            <Input id="make" value={form.make} onChange={set("make")} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="model">Model (optional)</Label>
            <Input id="model" value={form.model} onChange={set("model")} />
          </div>

          <div className="col-span-2 flex items-center gap-2 pt-1">
            <Checkbox id="consent" checked={consent} onCheckedChange={setConsent} />
            <Label htmlFor="consent" className="text-xs font-normal text-muted-foreground">
              I consent to my face photo being used for gate entry verification.
            </Label>
          </div>

          {error ? (
            <p className="col-span-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          ) : null}

          <Button type="submit" className="col-span-2 mt-1 w-full" disabled={submitting}>
            {submitting ? "Submitting…" : "Register"}
          </Button>
        </form>

        <div className="mt-6 flex items-center justify-between border-t border-border pt-4 text-xs text-muted-foreground">
          <Link to="/portal" className="underline underline-offset-2">
            Already registered? Check your status
          </Link>
          <Link to="/login" className="underline underline-offset-2">
            Staff login
          </Link>
        </div>
      </div>
    </div>
  );
}
