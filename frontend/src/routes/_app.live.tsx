import { createFileRoute } from "@tanstack/react-router";
import { useRef, useState } from "react";
import camVehicle from "@/assets/cam-vehicle.jpg";
import { PageHeader } from "@/components/app/AppShell";
import { Card, LiveFeedFrame } from "@/components/app/shared";
import { CurrentVerification } from "./_app.dashboard";
import { useApp } from "@/lib/app-store";
import { GATES } from "@/lib/campus-data";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const SCENARIOS = [
  { value: "", label: "Normal (random outcome)" },
  { value: "unknown_vehicle", label: "Test: unknown vehicle" },
  { value: "ocr_failure", label: "Test: OCR failure / unreadable plate" },
  { value: "low_confidence", label: "Test: low OCR confidence" },
  { value: "face_mismatch", label: "Test: face mismatch" },
  { value: "no_face", label: "Test: no face detected" },
];

export const Route = createFileRoute("/_app/live")({
  head: () => ({
    meta: [
      { title: "Live Gate Monitoring — Campus Gate AI" },
      {
        name: "description",
        content:
          "Real-time gate camera with plate bounding boxes, detection pipeline stepper, verification results and manual override controls for guards.",
      },
      { property: "og:title", content: "Live Gate Monitoring — Campus Gate AI" },
      { property: "og:description", content: "Guard console for live ANPR and face verification at campus gates." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: LivePage,
});

const STEPS = ["Plate Detected", "OCR Read", "DB Lookup", "Face Check", "Decision"];

function LivePage() {
  const { current, step, gate, setGate, aiOnline, setAiOnline, manualDecision, runVerification } = useApp();
  const [reason, setReason] = useState("");
  const [scenario, setScenario] = useState("");
  const [requireFace, setRequireFace] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const decide = (status: "granted" | "denied") => {
    if (!reason.trim()) {
      toast.error("A reason is required for a manual override");
      return;
    }
    manualDecision(status, reason.trim());
    setReason("");
  };

  const handleFile = async (file: File) => {
    setPreview(URL.createObjectURL(file));
    setSubmitting(true);
    await runVerification(file, { requireFace, scenario: scenario || undefined });
    setSubmitting(false);
  };

  return (
    <div>
      <PageHeader
        title="Live Gate Monitoring"
        subtitle={aiOnline ? "AI pipeline streaming" : "AI offline — manual verification mode"}
        action={
          <div className="flex items-center gap-2">
            <select
              value={gate}
              onChange={(e) => setGate(e.target.value)}
              className="rounded-md border border-border bg-surface-2 px-2 py-1.5 font-mono text-xs"
              aria-label="Gate"
            >
              {GATES.map((g) => (
                <option key={g.id} value={g.label}>
                  {g.label}
                </option>
              ))}
            </select>
            <Button variant="outline" size="sm" onClick={() => setAiOnline(!aiOnline)}>
              {aiOnline ? "Simulate AI outage" : "Restore AI service"}
            </Button>
          </div>
        }
      />

      <div className="grid gap-3 p-3 xl:grid-cols-3">
        <Card title={`Camera — ${gate}`} className="xl:col-span-2" bodyClassName="p-3">
          <LiveFeedFrame src={camVehicle} label={gate} plate={current?.plate} confidence={current?.plateConfidence} />
          <div className="mt-3 flex flex-wrap items-center gap-1.5">
            {STEPS.map((s, i) => (
              <div key={s} className="flex items-center gap-1.5">
                <span
                  className={cn(
                    "rounded-full border px-2 py-0.5 font-mono text-[0.6rem] uppercase tracking-wider",
                    i < step
                      ? "border-success/40 bg-success/12 text-success"
                      : i === step
                        ? "border-primary/50 bg-primary/15 text-primary"
                        : "border-border text-muted-foreground",
                  )}
                >
                  {s}
                </span>
                {i < STEPS.length - 1 ? <span className="text-muted-foreground">→</span> : null}
              </div>
            ))}
          </div>
        </Card>

        <div className="flex flex-col gap-3">
          <Card title="Verification result">
            <CurrentVerification entry={current} />
          </Card>

          <Card title="Upload / capture & verify" bodyClassName="space-y-2 p-3">
            {preview ? (
              <img src={preview} alt="Captured entry frame" className="aspect-video w-full rounded border border-border object-cover" />
            ) : null}

            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              capture="environment"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFile(file);
                e.target.value = "";
              }}
            />

            <div className="flex gap-2">
              <Button className="flex-1" size="sm" onClick={() => fileRef.current?.click()} disabled={submitting || !aiOnline}>
                {submitting ? "Processing…" : "Upload / capture image"}
              </Button>
            </div>

            <label className="flex items-center justify-between text-xs text-muted-foreground">
              Require face verification
              <input type="checkbox" checked={requireFace} onChange={(e) => setRequireFace(e.target.checked)} />
            </label>

            <select
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
              className="w-full rounded-md border border-border bg-surface-2 px-2 py-1.5 font-mono text-[0.65rem]"
              aria-label="Demo scenario"
            >
              {SCENARIOS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>

            {!aiOnline ? (
              <p className="text-[0.65rem] text-muted-foreground">
                AI pipeline is paused — use manual override below instead.
              </p>
            ) : (
              <p className="text-[0.65rem] text-muted-foreground">
                Runs the real backend pipeline: vehicle detect → plate detect → OCR → DB lookup → decision.
              </p>
            )}
          </Card>

          <Card title="Manual override" bodyClassName="space-y-2 p-3">
            <Textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Reason (required) — e.g. helmet obscured face, verified ID card manually"
              className="min-h-[70px] text-sm"
            />
            <div className="flex gap-2">
              <Button className="flex-1" onClick={() => decide("granted")}>
                Grant access manually
              </Button>
              <Button variant="destructive" className="flex-1" onClick={() => decide("denied")}>
                Deny entry
              </Button>
            </div>
            <p className="font-mono text-[0.6rem] text-muted-foreground">
              Every override is written to the entry log with operator, timestamp and reason.
            </p>
          </Card>
        </div>
      </div>
    </div>
  );
}
