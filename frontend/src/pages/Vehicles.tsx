
import { useMemo, useState } from "react";
import { PageHeader } from "@/components/app/AppShell";
import {
  Badge2,
  DataTable,
  DetailDrawer,
  Field,
  RoleGate,
  StatusBadge,
  type Column,
} from "@/components/app/shared";
import { useApp } from "@/lib/app-store";
import { fmtDateTime, studentById, type Vehicle } from "@/lib/campus-data";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";

const sel = "rounded-md border border-border bg-surface-2 px-2 py-1 font-mono text-xs";
const VEHICLE_TYPES = ["Bike", "Scooty", "Activa", "Car", "Other"];

function VehiclesPage() {
  const { entries, vehicles: ALL, students, createVehicle, updateVehicle } = useApp();
  const [type, setType] = useState("all");
  const [status, setStatus] = useState("all");
  const [block, setBlock] = useState("all");
  const [active, setActive] = useState<Vehicle | null>(null);
  const [newPlate, setNewPlate] = useState("");
  const [newType, setNewType] = useState(VEHICLE_TYPES[0]);
  const [newOwner, setNewOwner] = useState("");
  const [blockReason, setBlockReason] = useState("");
  const [adding, setAdding] = useState(false);

  const rows = useMemo(
    () =>
      ALL.filter(
        (v) =>
          (type === "all" || v.type === type) &&
          (status === "all" || v.status === status) &&
          (block === "all" || String(v.blocklisted) === block),
      ),
    [ALL, type, status, block],
  );

  const activeFresh = active ? ALL.find((v) => v.id === active.id) ?? active : null;

  const cols: Column<Vehicle>[] = [
    { key: "plate", header: "Vehicle number", render: (r) => <span className="font-mono text-xs">{r.plate}</span>, sortValue: (r) => r.plate },
    { key: "type", header: "Type", render: (r) => r.type, sortValue: (r) => r.type },
    { key: "owner", header: "Owner", render: (r) => studentById(r.ownerId)?.name ?? "—" },
    { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
    { key: "block", header: "Blocklist", render: (r) => (r.blocklisted ? <Badge2 tone="danger">blocked</Badge2> : <Badge2 tone="muted">clear</Badge2>) },
  ];

  const update = async (dbId: number, patch: Record<string, unknown>) => {
    try {
      await updateVehicle(dbId, patch);
    } catch (err: any) {
      toast.error("Could not update vehicle", { description: err.message });
    }
  };

  const history = activeFresh ? entries.filter((e) => e.plate === activeFresh.plate).slice(0, 8) : [];

  const attachVehicle = async () => {
    const owner = studentById(newOwner.trim().toUpperCase());
    if (!newPlate.trim() || !owner) {
      toast.error("Enter a plate and a valid student ID");
      return;
    }
    setAdding(true);
    try {
      await createVehicle({
        registration_number: newPlate.trim(),
        vehicle_type: newType,
        owner_student_id: owner.dbId,
      });
      toast.success(`${newPlate.trim().toUpperCase()} linked to ${owner.name}`);
      setNewPlate("");
      setNewOwner("");
    } catch (err: any) {
      toast.error("Could not register vehicle", { description: err.message });
    } finally {
      setAdding(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Vehicle Management"
        subtitle="Registered plates, blocklists and owner links (multiple vehicles per student supported)"
      />
      <div className="grid gap-3 p-3 xl:grid-cols-4">
        <div className="panel overflow-hidden xl:col-span-3">
          <DataTable
            rows={rows}
            columns={cols}
            onRowClick={setActive}
            searchPlaceholder="Search by plate or owner…"
            searchFields={(r) => `${r.plate} ${studentById(r.ownerId)?.name ?? ""}`}
            toolbar={
              <>
                <select className={sel} value={type} onChange={(e) => setType(e.target.value)} aria-label="Type">
                  <option value="all">All types</option>
                  {VEHICLE_TYPES.map((t) => (
                    <option key={t}>{t}</option>
                  ))}
                </select>
                <select className={sel} value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
                  <option value="all">Any status</option>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
                <select className={sel} value={block} onChange={(e) => setBlock(e.target.value)} aria-label="Blocklist">
                  <option value="all">Any blocklist state</option>
                  <option value="true">Blocklisted</option>
                  <option value="false">Clear</option>
                </select>
              </>
            }
          />
        </div>

        <RoleGate permission="edit">
          <section className="panel h-fit p-3">
            <h2 className="font-mono text-[0.68rem] uppercase tracking-[0.18em] text-muted-foreground">Add vehicle</h2>
            <div className="mt-3 space-y-2">
              <Input value={newPlate} onChange={(e) => setNewPlate(e.target.value.toUpperCase())} placeholder="MP 07 AB 1234" className="font-mono text-xs" />
              <select className={`${sel} w-full`} value={newType} onChange={(e) => setNewType(e.target.value)}>
                {VEHICLE_TYPES.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
              <Input value={newOwner} onChange={(e) => setNewOwner(e.target.value)} placeholder="Owner student ID (STU1001)" className="font-mono text-xs" />
              <Button className="w-full" size="sm" onClick={attachVehicle} disabled={adding}>
                {adding ? "Saving…" : "Attach to student"}
              </Button>
              <p className="text-[0.65rem] text-muted-foreground">
                {students.length} students registered — pick a Student ID from the Students page.
              </p>
            </div>
          </section>
        </RoleGate>
      </div>

      <DetailDrawer open={!!active} onOpenChange={(v) => !v && setActive(null)} title={activeFresh?.plate ?? ""}>
        {activeFresh ? (
          <>
            <div>
              <Field label="Owner">{studentById(activeFresh.ownerId)?.name ?? "No record"}</Field>
              <Field label="Student ID">{activeFresh.ownerId ?? "—"}</Field>
              <Field label="Type">{activeFresh.type}</Field>
              <Field label="Status"><StatusBadge status={activeFresh.status} /></Field>
              {activeFresh.blocklisted ? <Field label="Block reason">{activeFresh.blockReason ?? "—"}</Field> : null}
            </div>

            <RoleGate
              permission="edit"
              fallback={<p className="text-xs text-muted-foreground">Guards have read-only access to vehicle records.</p>}
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Active</span>
                  <Switch
                    checked={activeFresh.status === "active"}
                    onCheckedChange={(c) => update(activeFresh.dbId, { status: c ? "active" : "inactive" })}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Blocklisted</span>
                  <Switch
                    checked={activeFresh.blocklisted}
                    onCheckedChange={(c) =>
                      update(activeFresh.dbId, {
                        is_blocklisted: c,
                        block_reason: c ? blockReason || "Flagged by operator" : null,
                      })
                    }
                  />
                </div>
                <Input
                  value={blockReason}
                  onChange={(e) => setBlockReason(e.target.value)}
                  placeholder="Blocklist reason"
                  className="text-xs"
                />
              </div>
            </RoleGate>

            <div>
              <h3 className="mb-2 font-mono text-[0.65rem] uppercase tracking-wider text-muted-foreground">
                Entry history for this plate
              </h3>
              <ul className="space-y-1">
                {history.length === 0 ? (
                  <li className="text-sm text-muted-foreground">No recent entries.</li>
                ) : (
                  history.map((e) => (
                    <li key={e.id} className="flex items-center justify-between text-xs">
                      <span className="font-mono text-muted-foreground">{fmtDateTime(e.ts)}</span>
                      <StatusBadge status={e.status} />
                    </li>
                  ))
                )}
              </ul>
            </div>
          </>
        ) : null}
      </DetailDrawer>
    </div>
  );
}

export default VehiclesPage;
