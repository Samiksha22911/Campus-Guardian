import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import camPerimeter from "@/assets/cam-perimeter.jpg";
import { PageHeader } from "@/components/app/AppShell";
import { Badge2, StatusBadge } from "@/components/app/shared";
import { useApp } from "@/lib/app-store";
import { fmtDateTime, studentById } from "@/lib/campus-data";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export const Route = createFileRoute("/_app/alerts")({
  head: () => ({
    meta: [
      {
        title: "Alerts — Campus Guardian AI",
      },
      {
        name: "description",
        content:
          "Triage campus security alerts by severity and status: blocklisted vehicles, face mismatches, intrusion and loitering events.",
      },
      {
        property: "og:title",
        content: "Alerts — Campus Guardian AI",
      },
      {
        property: "og:description",
        content:
          "Acknowledge, resolve and escalate live campus security alerts.",
      },
      {
        property: "og:type",
        content: "website",
      },
      {
        name: "twitter:card",
        content: "summary_large_image",
      },
    ],
  }),

  component: AlertsPage,
});

const sel =
  "rounded-md border border-border bg-surface-2 px-2 py-1 font-mono text-xs";

function AlertsPage() {
  const { alerts, setAlertStatus } = useApp();

  const [preset, setPreset] = useState("attention");
  const [sev, setSev] = useState("all");
  const [status, setStatus] = useState("all");

  const rows = useMemo(() => {
    let out = alerts;

    if (preset === "attention") {
      out = out.filter(
        (a) =>
          a.status === "open" &&
          (a.severity === "high" || a.severity === "critical"),
      );
    }

    if (sev !== "all") {
      out = out.filter((a) => a.severity === sev);
    }

    if (status !== "all") {
      out = out.filter((a) => a.status === status);
    }

    return out;
  }, [alerts, preset, sev, status]);

  return (
    <div>
      <PageHeader
        title="Alerts"
        subtitle={`${alerts.filter((a) => a.status === "open").length} open · ${alerts.length} total`}
        action={
          <div className="flex flex-wrap gap-2">
            <select
              className={sel}
              value={preset}
              onChange={(e) => setPreset(e.target.value)}
              aria-label="Preset"
            >
              <option value="attention">Needs attention now</option>
              <option value="all">All alerts</option>
            </select>

            <select
              className={sel}
              value={sev}
              onChange={(e) => setSev(e.target.value)}
              aria-label="Severity"
            >
              <option value="all">Any severity</option>

              {["critical", "high", "medium", "low"].map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>

            <select
              className={sel}
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              aria-label="Status"
            >
              <option value="all">Any status</option>

              {["open", "acknowledged", "resolved"].map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        }
      />

      <div className="grid gap-3 p-3 md:grid-cols-2 xl:grid-cols-3">
        {rows.map((a) => (
          <article
            key={a.id}
            className={cn(
              "panel overflow-hidden",
              a.severity === "critical" &&
                "border-destructive/60 shadow-[0_0_0_1px_var(--destructive)]",
            )}
          >
            <div className="flex items-start justify-between gap-2 border-b border-border px-3 py-2">
              <div>
                <p className="text-sm font-semibold">{a.type}</p>

                <p className="font-mono text-[0.6rem] text-muted-foreground">
                  {fmtDateTime(a.ts)}
                </p>
              </div>

              <div className="flex flex-col items-end gap-1">
                <StatusBadge status={a.severity} />
                <StatusBadge status={a.status} />
              </div>
            </div>

            <img
              src={camPerimeter}
              alt={`${a.type} captured frame`}
              className="h-28 w-full object-cover opacity-80"
              loading="lazy"
            />

            <div className="space-y-1 px-3 py-2 text-xs">
              <p className="text-muted-foreground">{a.detail}</p>

              <p className="flex flex-wrap items-center gap-1.5">
                {a.plate ? (
                  <Badge2 tone="primary">{a.plate}</Badge2>
                ) : null}

                {a.studentId ? (
                  <Badge2 tone="muted">
                    {studentById(a.studentId)?.name}
                  </Badge2>
                ) : null}

                <Badge2 tone="muted">{a.gate}</Badge2>
              </p>
            </div>

            <div className="flex gap-1.5 border-t border-border px-3 py-2">
              <Button
                size="sm"
                variant="outline"
                disabled={a.status !== "open"}
                onClick={() =>
                  setAlertStatus(a.id, "acknowledged")
                }
              >
                Acknowledge
              </Button>

              <Button
                size="sm"
                variant="outline"
                disabled={a.status === "resolved"}
                onClick={() =>
                  setAlertStatus(a.id, "resolved")
                }
              >
                Resolve
              </Button>

              <Button
                size="sm"
                variant="destructive"
                onClick={() =>
                  toast.error("Escalated to campus security lead")
                }
              >
                Escalate
              </Button>
            </div>
          </article>
        ))}

        {rows.length === 0 ? (
          <p className="panel p-6 text-center text-sm text-muted-foreground md:col-span-2 xl:col-span-3">
            Nothing needs attention right now.
          </p>
        ) : null}
      </div>
    </div>
  );
}

