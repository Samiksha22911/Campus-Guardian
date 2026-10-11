import { Link } from "react-router-dom";

import camVehicle from "@/assets/cam-vehicle.jpg";

import { PageHeader } from "@/components/app/AppShell";

import {
  Card,
  ConfidenceMeter,
  DataTable,
  FaceBadge,
  LiveFeedFrame,
  StatCard,
  StatusBadge,
} from "@/components/app/shared";

import { useApp } from "@/lib/app-store";
import { fmtTime, studentById, vehicles } from "@/lib/campus-data";
import { cn } from "@/lib/utils";

const spark = (seed) =>
  Array.from(
    { length: 12 },
    (_, i) => 20 + ((seed * (i + 3)) % 40),
  );

export function CurrentVerification({ entry }) {
  if (!entry) {
    return (
      <p className="p-4 text-sm text-muted-foreground">
        Waiting for first detection…
      </p>
    );
  }

  const student = studentById(entry.studentId);

  const tone =
    entry.status === "granted"
      ? "border-success/50 bg-success/10"
      : entry.status === "denied"
        ? "border-destructive/50 bg-destructive/10"
        : "border-warning/50 bg-warning/10";

  return (
    <div className={cn("m-3 rounded-md border p-4", tone)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-mono text-2xl font-semibold tracking-wide">
          {entry.plate}
        </p>

        <StatusBadge status={entry.status} />
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        <Info
          label="Student"
          value={
            student
              ? `${student.name} (${student.id})`
              : "No record"
          }
        />

        <Info
          label="Vehicle type"
          value={entry.vehicleType}
        />

        <Info
          label="Gate"
          value={entry.gate}
        />

        <Info
          label="Time"
          value={fmtTime(entry.ts)}
        />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[0.62rem] uppercase text-muted-foreground">
            Face
          </span>

          <FaceBadge value={entry.faceMatch} />
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono text-[0.62rem] uppercase text-muted-foreground">
            OCR
          </span>

          <ConfidenceMeter value={entry.plateConfidence} />
        </div>

        <div className="flex items-center gap-2">
          <span className="font-mono text-[0.62rem] uppercase text-muted-foreground">
            Match
          </span>

          <ConfidenceMeter value={entry.faceConfidence} />
        </div>
      </div>

      {entry.reason ? (
        <p className="mt-3 rounded border border-border bg-surface-2 px-2 py-1 font-mono text-[0.65rem] text-muted-foreground">
          Manual override — {entry.reason}
        </p>
      ) : null}
    </div>
  );
}

function Info({ label, value }) {
  return (
    <p className="text-sm">
      <span className="font-mono text-[0.62rem] uppercase tracking-wider text-muted-foreground">
        {label}:{" "}
      </span>

      {value}
    </p>
  );
}

function DashboardPage() {
  const {
    entries,
    alerts,
    current,
    user,
  } = useApp();

  const today = entries;

  const verified = today.filter(
    (e) => e.status === "granted",
  ).length;

  const unknown = today.filter(
    (e) => e.studentId === null,
  ).length;

  const mismatch = today.filter(
    (e) => e.faceMatch === "mismatch",
  ).length;

  const pending = today.filter(
    (e) => e.status === "uncertain",
  ).length;

  const openAlerts = alerts.filter(
    (a) => a.status === "open",
  );

  const cols = [
    {
      key: "ts",
      header: "Time",
      render: (r) => (
        <span className="font-mono text-xs">
          {fmtTime(r.ts)}
        </span>
      ),
    },

    {
      key: "plate",
      header: "Vehicle",
      render: (r) => (
        <span className="font-mono text-xs">
          {r.plate}
        </span>
      ),
    },

    {
      key: "student",
      header: "Student",
      render: (r) =>
        studentById(r.studentId)?.name ?? "—",
    },

    {
      key: "face",
      header: "Face",
      render: (r) => (
        <FaceBadge value={r.faceMatch} />
      ),
    },

    {
      key: "status",
      header: "Status",
      render: (r) => (
        <StatusBadge status={r.status} />
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Security Dashboard"
        subtitle={`Signed in as ${user?.name ?? "Security Officer"} · live stream active`}
      />

      <div className="grid gap-3 p-3 sm:grid-cols-2 xl:grid-cols-6">
        <StatCard
          label="Vehicles today"
          value={today.length}
          spark={spark(3)}
        />

        <StatCard
          label="Verified entries"
          value={verified}
          tone="success"
          spark={spark(5)}
        />

        <StatCard
          label="Unknown vehicles"
          value={unknown}
          tone="warning"
          spark={spark(7)}
        />

        <StatCard
          label="Mismatches"
          value={mismatch}
          tone="danger"
          spark={spark(2)}
        />

        <StatCard
          label="Pending verification"
          value={pending}
          tone="warning"
          spark={spark(11)}
        />

        <StatCard
          label="Registered vehicles"
          value={vehicles.length}
          tone="primary"
          spark={spark(4)}
        />
      </div>

      <div className="grid gap-3 px-3 pb-3 xl:grid-cols-3">
        <Card
          title="Current verification"
          className="xl:col-span-2"
        >
          <CurrentVerification entry={current} />
        </Card>

        <Card
          title="Gate camera"
          action={
            <Link
              to="/live"
              className="font-mono text-[0.65rem] uppercase text-primary hover:underline"
            >
              Open live
            </Link>
          }
          bodyClassName="p-3"
        >
          <LiveFeedFrame
            src={camVehicle}
            label={current?.gate ?? "Gate"}
            plate={current?.plate}
            confidence={current?.plateConfidence}
            compact
          />
        </Card>
      </div>

      <div className="grid gap-3 px-3 pb-6 xl:grid-cols-3">
        <Card
          title={`Recent alerts (${openAlerts.length} open)`}
          action={
            <Link
              to="/alerts"
              className="font-mono text-[0.65rem] uppercase text-primary hover:underline"
            >
              View all
            </Link>
          }
        >
          <ul className="divide-y divide-border/60">
            {openAlerts.slice(0, 5).map((a) => (
              <li
                key={a.id}
                className="flex items-start justify-between gap-3 px-3 py-2"
              >
                <div>
                  <p className="text-sm font-medium">
                    {a.type}
                  </p>

                  <p className="text-xs text-muted-foreground">
                    {a.plate ?? a.gate}
                  </p>
                </div>

                <div className="text-right">
                  <StatusBadge status={a.severity} />

                  <p className="mt-1 font-mono text-[0.6rem] text-muted-foreground">
                    {fmtTime(a.ts)}
                  </p>
                </div>
              </li>
            ))}

            {openAlerts.length === 0 ? (
              <li className="px-3 py-6 text-center text-sm text-muted-foreground">
                No open alerts.
              </li>
            ) : null}
          </ul>
        </Card>

        <Card
          title="Recent entries"
          className="xl:col-span-2"
          action={
            <Link
              to="/logs"
              className="font-mono text-[0.65rem] uppercase text-primary hover:underline"
            >
              Entry logs
            </Link>
          }
        >
          <DataTable
            rows={entries.slice(0, 10)}
            columns={cols}
            pageSize={10}
          />
        </Card>
      </div>
    </div>
  );
}

export default DashboardPage;
