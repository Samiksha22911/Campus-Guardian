
import { useMemo, useState } from "react";
import camVehicle from "@/assets/cam-vehicle.jpg";
import { PageHeader } from "@/components/app/AppShell";
import {
  ConfidenceMeter,
  DataTable,
  DetailDrawer,
  FaceBadge,
  Field,
  RoleGate,
  StatusBadge,
  Badge2,
  type Column,
} from "@/components/app/shared";
import { useApp } from "@/lib/app-store";
import { GATES, fmtDate, fmtDateTime, fmtTime, studentById, type EntryLog } from "@/lib/campus-data";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

const sel = "rounded-md border border-border bg-surface-2 px-2 py-1 font-mono text-xs";

function LogsPage() {
  const { entries } = useApp();
  const [status, setStatus] = useState("all");
  const [gate, setGate] = useState("all");
  const [vehicleType, setVehicleType] = useState("all");
  const [alertOnly, setAlertOnly] = useState("all");
  const [range, setRange] = useState("24h");
  const [active, setActive] = useState<EntryLog | null>(null);

  const vehicleTypes = useMemo(
    () => Array.from(new Set(entries.map((e) => e.vehicleType).filter(Boolean))).sort(),
    [entries],
  );

  const rows = useMemo(() => {
    const cutoff = Date.now() - (range === "24h" ? 864e5 : range === "7d" ? 6048e5 : 2592e6);
    return entries.filter(
      (e) =>
        e.ts >= cutoff &&
        (status === "all" || e.status === status) &&
        (gate === "all" || e.gate === gate) &&
        (vehicleType === "all" || e.vehicleType === vehicleType) &&
        (alertOnly === "all" || (alertOnly === "yes" ? !!e.alertId : !e.alertId)),
    );
  }, [entries, status, gate, vehicleType, alertOnly, range]);

  const cols: Column<EntryLog>[] = [
    { key: "date", header: "Date", render: (r) => <span className="font-mono text-xs">{fmtDate(r.ts)}</span>, sortValue: (r) => r.ts },
    { key: "ts", header: "Time", render: (r) => <span className="font-mono text-xs">{fmtTime(r.ts)}</span>, sortValue: (r) => r.ts },
    { key: "plate", header: "Vehicle No.", render: (r) => <span className="font-mono text-xs">{r.plate}</span>, sortValue: (r) => r.plate },
    { key: "type", header: "Type", render: (r) => r.vehicleType },
    { key: "student", header: "Student", render: (r) => studentById(r.studentId)?.name ?? "—" },
    { key: "ocr", header: "OCR", render: (r) => <span className="font-mono text-xs">{r.plateConfidence}%</span>, sortValue: (r) => r.plateConfidence },
    { key: "face", header: "Face Match", render: (r) => <FaceBadge value={r.faceMatch} /> },
    { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
    { key: "reason", header: "Reason", render: (r) => <span className="text-xs text-muted-foreground">{r.reason ?? "—"}</span> },
    { key: "alert", header: "Alert", render: (r) => (r.alertId ? <Badge2 tone="danger">yes</Badge2> : <span className="text-muted-foreground">—</span>) },
  ];

  const exportCsv = () => {
    const header = "date,time,plate,type,student,ocr,face,status,reason,gate,face_conf\n";
    const body = rows
      .map((r) =>
        [fmtDate(r.ts), fmtTime(r.ts), r.plate, r.vehicleType, studentById(r.studentId)?.name ?? "", r.plateConfidence.toFixed(1), r.faceMatch, r.status, (r.reason ?? "").replace(/,/g, ";"), r.gate, r.faceConfidence.toFixed(1)].join(","),
      )
      .join("\n");
    const blob = new Blob([header + body], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "entry-logs.csv";
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`Exported ${rows.length} rows`);
  };

  return (
    <div>
      <PageHeader
        title="Entry Logs"
        subtitle="Immutable audit trail of gate decisions"
        action={
          <RoleGate permission="export">
            <Button size="sm" variant="outline" onClick={exportCsv}>
              Export CSV
            </Button>
          </RoleGate>
        }
      />
      <div className="p-3">
        <div className="panel overflow-hidden">
          <DataTable
            rows={rows}
            columns={cols}
            onRowClick={setActive}
            pageSize={14}
            searchPlaceholder="Search vehicle number, student name or ID…"
            searchFields={(r) => `${r.plate} ${r.studentId ?? ""} ${studentById(r.studentId)?.name ?? ""}`}
            toolbar={
              <>
                <select className={sel} value={range} onChange={(e) => setRange(e.target.value)} aria-label="Date range">
                  <option value="24h">Last 24 hours</option>
                  <option value="7d">Last 7 days</option>
                  <option value="30d">Last 30 days</option>
                </select>
                <select className={sel} value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
                  <option value="all">Any status</option>
                  {["granted", "denied", "uncertain", "manual"].map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
                <select className={sel} value={gate} onChange={(e) => setGate(e.target.value)} aria-label="Camera location">
                  <option value="all">All locations</option>
                  {GATES.map((g) => (
                    <option key={g.id} value={g.label}>{g.label}</option>
                  ))}
                </select>
                <select className={sel} value={vehicleType} onChange={(e) => setVehicleType(e.target.value)} aria-label="Vehicle type">
                  <option value="all">All vehicle types</option>
                  {vehicleTypes.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                <select className={sel} value={alertOnly} onChange={(e) => setAlertOnly(e.target.value)} aria-label="Alert filter">
                  <option value="all">With and without alerts</option>
                  <option value="yes">Has alert</option>
                  <option value="no">No alert</option>
                </select>
              </>
            }
          />
        </div>
      </div>

      <DetailDrawer open={!!active} onOpenChange={(v) => !v && setActive(null)} title={active ? `Entry ${active.id}` : ""}>
        {active ? (
          <>
            <img src={camVehicle} alt="Captured frame at detection" className="rounded-md border border-border" />
            <div>
              <Field label="Time">{fmtDateTime(active.ts)}</Field>
              <Field label="Vehicle">{active.plate}</Field>
              <Field label="Student">{studentById(active.studentId)?.name ?? "No record"}</Field>
              <Field label="Gate">{active.gate}</Field>
              <Field label="Face match"><FaceBadge value={active.faceMatch} /></Field>
              <Field label="Status"><StatusBadge status={active.status} /></Field>
              <Field label="Model version"><span className="font-mono text-xs">{active.modelVersion}</span></Field>
              {active.reason ? <Field label="Override reason">{active.reason}</Field> : null}
            </div>
            <div className="space-y-2">
              <p className="font-mono text-[0.65rem] uppercase tracking-wider text-muted-foreground">Confidence</p>
              <div className="flex items-center gap-2 text-xs"><span className="w-16">OCR</span><ConfidenceMeter value={active.plateConfidence} /></div>
              <div className="flex items-center gap-2 text-xs"><span className="w-16">Face</span><ConfidenceMeter value={active.faceConfidence} /></div>
            </div>
          </>
        ) : null}
      </DetailDrawer>
    </div>
  );
}

export default LogsPage;
