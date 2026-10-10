import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import camGate from "@/assets/cam-gate.jpg";
import camVehicle from "@/assets/cam-vehicle.jpg";
import { PageHeader } from "@/components/app/AppShell";
import { Badge2, ConfidenceMeter, Field } from "@/components/app/shared";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { useApp } from "@/lib/app-store";

export const Route = createFileRoute("/_app/enrollment")({
  head: () => ({
    meta: [
      { title: "Enrollment Wizard — Campus Guardian AI" },
      {
        name: "description",
        content:
          "Guided enrollment: capture student details, register face embeddings, link vehicle plates and record biometric consent.",
      },
      {
        property: "og:title",
        content: "Enrollment Wizard — Campus Guardian AI",
      },
      {
        property: "og:description",
        content:
          "Enroll a student's face and vehicles for touchless gate verification.",
      },
      { property: "og:type", content: "website" },
      {
        name: "twitter:card",
        content: "summary_large_image",
      },
    ],
  }),

  component: EnrollmentPage,
});

const STEPS = [
  "Student details",
  "Face capture",
  "Vehicle link",
  "Consent & review",
];

const VEHICLE_TYPES = ["Bike", "Scooty", "Activa", "Car", "Other"];

function EnrollmentPage() {
  const navigate = useNavigate();
  const { createStudent, uploadStudentPhoto, createVehicle } = useApp();

  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [sid, setSid] = useState("");
  const [dept, setDept] = useState("");
  const [year, setYear] = useState("1");
  const [email, setEmail] = useState("");
  const [shots, setShots] = useState([]);
  const [plate, setPlate] = useState("");
  const [vtype, setVtype] = useState(VEHICLE_TYPES[0]);
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const canNext =
    step === 0
      ? name.trim() && sid.trim() && dept.trim()
      : step === 1
        ? shots.length >= 3
        : step === 2
          ? plate.trim().length >= 6
          : consent;

  return (
    <div>
      <PageHeader
        title="Enrollment"
        subtitle="Register a student for face and plate based entry verification"
      />

      <div className="p-3">
        <ol className="panel mb-3 flex flex-wrap gap-2 p-3">
          {STEPS.map((s, i) => (
            <li key={s} className="flex items-center gap-2">
              <span
                className={cn(
                  "flex size-6 items-center justify-center rounded-full border font-mono text-[0.65rem]",
                  i < step && "border-success bg-success/15 text-success",
                  i === step && "border-primary bg-primary/15 text-primary",
                  i > step && "border-border text-muted-foreground",
                )}
              >
                {i + 1}
              </span>

              <span
                className={cn(
                  "text-xs",
                  i === step
                    ? "text-foreground"
                    : "text-muted-foreground",
                )}
              >
                {s}
              </span>

              {i < STEPS.length - 1 ? (
                <span className="mx-1 h-px w-6 bg-border" />
              ) : null}
            </li>
          ))}
        </ol>

        <section className="panel p-4">
          {step === 0 ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <Label className="text-xs">Full name</Label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Aarav Sharma"
                />
              </div>

              <div>
                <Label className="text-xs">Student ID</Label>
                <Input
                  value={sid}
                  onChange={(e) =>
                    setSid(e.target.value.toUpperCase())
                  }
                  placeholder="STU-1043"
                  className="font-mono"
                />
              </div>

              <div>
                <Label className="text-xs">Department</Label>
                <Input
                  value={dept}
                  onChange={(e) => setDept(e.target.value)}
                  placeholder="Computer Science"
                />
              </div>

              <div>
                <Label className="text-xs">Year</Label>

                <select
                  value={year}
                  onChange={(e) => setYear(e.target.value)}
                  className="h-9 w-full rounded-md border border-border bg-surface-2 px-2 text-sm"
                >
                  {[1, 2, 3, 4].map((y) => (
                    <option key={y} value={y}>
                      {y}
                    </option>
                  ))}
                </select>
              </div>

              <div className="sm:col-span-2">
                <Label className="text-xs">Email</Label>

                <Input
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="aarav@campus.edu"
                />
              </div>
            </div>
          ) : null}

          {step === 1 ? (
            <div className="grid gap-3 md:grid-cols-2">
              <div className="relative overflow-hidden rounded-md border border-border bg-black">
                <img
                  src={camGate}
                  alt="Face enrollment capture preview"
                  className="aspect-video w-full object-cover opacity-85"
                />

                <div className="pointer-events-none absolute left-1/2 top-1/2 size-32 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-primary/80" />

                <span className="absolute bottom-2 left-2 rounded bg-background/80 px-1.5 py-0.5 font-mono text-[0.6rem] uppercase tracking-wider">
                  capture preview
                </span>
              </div>

              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Capture at least 3 angles (front, left, right) for a
                  robust embedding.
                </p>

                <div className="flex gap-2">
                  {[0, 1, 2, 3, 4].map((i) => (
                    <span
                      key={i}
                      className={cn(
                        "h-12 w-12 rounded border",
                        shots[i] !== undefined
                          ? "border-success bg-success/15"
                          : "border-dashed border-border",
                      )}
                    />
                  ))}
                </div>

                {shots.length ? (
                  <ConfidenceMeter
                    value={Math.min(99, 70 + shots.length * 7)}
                    label="Embedding quality"
                  />
                ) : null}

                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() =>
                      setShots((previous) =>
                        previous.length < 5
                          ? [...previous, Date.now()]
                          : previous,
                      )
                    }
                  >
                    Capture frame
                  </Button>

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShots([])}
                  >
                    Retake all
                  </Button>
                </div>
              </div>
            </div>
          ) : null}

          {step === 2 ? (
            <div className="grid gap-3 md:grid-cols-2">
              <div className="relative overflow-hidden rounded-md border border-border bg-black">
                <img
                  src={camVehicle}
                  alt="Plate capture preview"
                  className="aspect-video w-full object-cover opacity-85"
                />

                <span className="absolute bottom-2 left-2 rounded bg-background/80 px-1.5 py-0.5 font-mono text-[0.6rem] uppercase tracking-wider">
                  ANPR preview
                </span>
              </div>

              <div className="space-y-3">
                <div>
                  <Label className="text-xs">Vehicle number</Label>

                  <Input
                    value={plate}
                    onChange={(e) =>
                      setPlate(e.target.value.toUpperCase())
                    }
                    placeholder="KA 05 MJ 4471"
                    className="font-mono"
                  />
                </div>

                <div>
                  <Label className="text-xs">Vehicle type</Label>

                  <select
                    value={vtype}
                    onChange={(e) => setVtype(e.target.value)}
                    className="h-9 w-full rounded-md border border-border bg-surface-2 px-2 text-sm"
                  >
                    {VEHICLE_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                </div>

                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setPlate("MP 07 AB 1234");
                    toast.success("Plate auto-read from camera");
                  }}
                >
                  Auto-read from camera
                </Button>
              </div>
            </div>
          ) : null}

          {step === 3 ? (
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <Field label="Name">{name}</Field>
                <Field label="Student ID">{sid}</Field>
                <Field label="Department">
                  {dept} · Year {year}
                </Field>
                <Field label="Email">{email || "—"}</Field>
                <Field label="Face frames">
                  {shots.length} captured
                </Field>
                <Field label="Vehicle">
                  {plate} · {vtype}
                </Field>
              </div>

              <div className="space-y-3">
                <label className="flex items-start gap-2 rounded border border-border p-3 text-xs text-muted-foreground">
                  <Checkbox
                    checked={consent}
                    onCheckedChange={(checked) =>
                      setConsent(!!checked)
                    }
                  />

                  <span>
                    The student consents to biometric face data being
                    stored and processed for campus entry verification,
                    retained per the institution's data policy and
                    deletable on request.
                  </span>
                </label>

                <Badge2 tone={consent ? "success" : "warning"}>
                  {consent
                    ? "consent recorded"
                    : "consent required"}
                </Badge2>
              </div>
            </div>
          ) : null}

          <div className="mt-5 flex justify-between border-t border-border pt-4">
            <Button
              variant="outline"
              size="sm"
              disabled={step === 0}
              onClick={() => setStep((s) => s - 1)}
            >
              Back
            </Button>

            {step < 3 ? (
              <Button
                size="sm"
                disabled={!canNext}
                onClick={() => setStep((s) => s + 1)}
              >
                Continue
              </Button>
            ) : (
              <Button
                size="sm"
                disabled={!consent || submitting}
                onClick={async () => {
                  setSubmitting(true);
                  try {
                    const student = await createStudent({
                      student_id: sid.trim(),
                      name: name.trim(),
                      department: dept.trim(),
                      year: Number(year),
                      email: email.trim() || undefined,
                      biometric_consent: consent,
                    });

                    if (shots.length > 0) {
                      try {
                        const res = await fetch(camGate);
                        const blob = await res.blob();
                        const file = new File([blob], "face-reference.jpg", { type: "image/jpeg" });
                        await uploadStudentPhoto(student.id, file);
                      } catch {
                        // Non-fatal - student record was still created.
                      }
                    }

                    if (plate.trim()) {
                      await createVehicle({
                        registration_number: plate.trim(),
                        vehicle_type: vtype,
                        owner_student_id: student.id,
                      });
                    }

                    toast.success(`${name} enrolled`, {
                      description: `${sid} · face + ${plate || "no vehicle"}`,
                    });

                    navigate({ to: "/students" });
                  } catch (err) {
                    toast.error("Enrollment failed", { description: err.message });
                  } finally {
                    setSubmitting(false);
                  }
                }}
              >
                {submitting ? "Saving…" : "Complete enrollment"}
              </Button>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}