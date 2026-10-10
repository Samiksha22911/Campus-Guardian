import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
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
import { api } from "@/lib/api-client";
import { fmtDateTime, vehiclesForStudent, type Student } from "@/lib/campus-data";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

export const Route = createFileRoute("/_app/students")({
  head: () => ({
    meta: [
      { title: "Student Management — Campus Gate AI" },
      {
        name: "description",
        content:
          "Search, filter and manage student records: enrollment status, linked vehicles, face enrollment and consent for campus entry verification.",
      },
      { property: "og:title", content: "Student Management — Campus Gate AI" },
      { property: "og:description", content: "Student registry with linked vehicles and face enrollment status." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: StudentsPage,
});

const sel = "rounded-md border border-border bg-surface-2 px-2 py-1 font-mono text-xs";

function PendingApprovalsPanel() {
  const { refreshAll } = useApp();
  const [pending, setPending] = useState<Student[] | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function load() {
    try {
      const rows = await api.getPendingStudents();
      setPending(rows);
    } catch {
      setPending([]);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleApprove(id: number, name: string) {
    setBusyId(id);
    try {
      await api.approveStudent(id);
      toast.success(`${name} approved — their vehicle can now enter`);
      await load();
      await refreshAll();
    } catch (err: any) {
      toast.error(err.message || "Could not approve this registration");
    } finally {
      setBusyId(null);
    }
  }

  async function handleReject(id: number, name: string) {
    setBusyId(id);
    try {
      await api.rejectStudent(id);
      toast.success(`${name}'s registration rejected`);
      await load();
      await refreshAll();
    } catch (err: any) {
      toast.error(err.message || "Could not reject this registration");
    } finally {
      setBusyId(null);
    }
  }

  if (!pending || pending.length === 0) return null;

  return (
    <div className="panel p-3">
      <div className="flex items-center gap-2">
        <Badge2 tone="warning">{pending.length} pending</Badge2>
        <p className="text-sm font-medium">Self-registered students awaiting approval</p>
      </div>
      <div className="mt-3 space-y-2">
        {pending.map((s) => {
          const vehicle = s.vehicles?.[0];
          return (
            <div
              key={s.id}
              className="flex flex-wrap items-center gap-3 rounded-md border border-border bg-surface-2 p-2.5"
            >
              <div className="min-w-[10rem]">
                <p className="text-sm font-medium">{s.name}</p>
                <p className="font-mono text-xs text-muted-foreground">
                  {s.student_id} · {s.department}
                </p>
              </div>
              {vehicle ? (
                <div className="text-xs text-muted-foreground">
                  <span className="font-mono text-foreground">{vehicle.registration_number}</span>{" "}
                  ({vehicle.vehicle_type})
                </div>
              ) : null}
              <Badge2 tone={s.face_enrolled ? "success" : "muted"}>
                {s.face_enrolled ? "face on file" : "no face photo"}
              </Badge2>
              <div className="ml-auto flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={busyId === s.id}
                  onClick={() => handleReject(s.id, s.name)}
                >
                  Reject
                </Button>
                <Button size="sm" disabled={busyId === s.id} onClick={() => handleApprove(s.id, s.name)}>
                  Approve
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StudentsPage() {
  const {
    entries,
    students: ALL,
    updateStudent,
    deactivateStudent,
    uploadStudentPhoto,
  } = useApp();

  const [dept, setDept] = useState("all");
  const [year, setYear] = useState("all");
  const [enr, setEnr] = useState("all");
  const [acct, setAcct] = useState("all");
  const [active, setActive] = useState<Student | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ department: "", year: "", email: "", phone: "" });
  const [saving, setSaving] = useState(false);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const rows = useMemo(
    () =>
      ALL.filter(
        (s) =>
          (dept === "all" || s.department === dept) &&
          (year === "all" || String(s.year) === year) &&
          (enr === "all" || s.enrollment === enr) &&
          (acct === "all" || s.account === acct),
      ),
    [ALL, dept, year, enr, acct],
  );

  const cols: Column<Student>[] = [
    { key: "id", header: "Student ID", render: (r) => <span className="font-mono text-xs">{r.id}</span>, sortValue: (r) => r.id },
    { key: "name", header: "Name", render: (r) => r.name, sortValue: (r) => r.name },
    { key: "dept", header: "Department", render: (r) => r.department, sortValue: (r) => r.department },
    { key: "year", header: "Year", render: (r) => r.year, sortValue: (r) => r.year },
    { key: "enr", header: "Enrollment", render: (r) => <StatusBadge status={r.enrollment} /> },
    { key: "acct", header: "Account", render: (r) => <StatusBadge status={r.account} /> },
  ];

  // Keep `active` pointed at the freshest copy after any mutation refreshes ALL.
  const activeFresh = active ? ALL.find((s) => s.id === active.id) ?? active : null;

  const history = activeFresh ? entries.filter((e) => e.studentId === activeFresh.id).slice(0, 8) : [];

  const openEdit = () => {
    if (!activeFresh) return;
    setForm({
      department: activeFresh.department,
      year: String(activeFresh.year),
      email: activeFresh.email,
      phone: activeFresh.phone ?? "",
    });
    setEditing(true);
  };

  const saveEdit = async () => {
    if (!activeFresh) return;
    setSaving(true);
    try {
      await updateStudent(activeFresh.dbId, {
        department: form.department,
        year: Number(form.year) || activeFresh.year,
        email: form.email,
        phone: form.phone,
      });
      toast.success("Student details updated");
      setEditing(false);
    } catch (err: any) {
      toast.error("Could not save changes", { description: err.message });
    } finally {
      setSaving(false);
    }
  };

  const toggleAccount = async () => {
    if (!activeFresh) return;
    try {
      if (activeFresh.account === "active") {
        await deactivateStudent(activeFresh.dbId);
        toast.success("Account suspended");
      } else {
        await updateStudent(activeFresh.dbId, { status: "active" });
        toast.success("Account reactivated");
      }
    } catch (err: any) {
      toast.error("Could not update account", { description: err.message });
    }
  };

  const softDelete = async () => {
    if (!activeFresh) return;
    if (!confirm(`Deactivate ${activeFresh.name}? This can be reversed later.`)) return;
    try {
      await deactivateStudent(activeFresh.dbId);
      toast.success("Student deactivated");
      setActive(null);
    } catch (err: any) {
      toast.error("Could not deactivate student", { description: err.message });
    }
  };

  const reEnrollFace = async (file: File) => {
    if (!activeFresh) return;
    try {
      await uploadStudentPhoto(activeFresh.dbId, file);
      toast.success("Face reference updated");
    } catch (err: any) {
      toast.error("Could not upload photo", { description: err.message });
    }
  };

  return (
    <div>
      <PageHeader
        title="Student Management"
        subtitle="Registry of enrolled students, linked vehicles and consent records"
        action={
          <RoleGate permission="enrollment" fallback={<Badge2 tone="muted">view only</Badge2>}>
            <Link to="/enrollment">
              <Button size="sm">New enrollment</Button>
            </Link>
          </RoleGate>
        }
      />
      <div className="p-3 space-y-3">
        <PendingApprovalsPanel />
        <div className="panel overflow-hidden">
          <DataTable
            rows={rows}
            columns={cols}
            onRowClick={(r) => {
              setActive(r);
              setEditing(false);
            }}
            searchPlaceholder="Search by name or student ID…"
            searchFields={(r) => `${r.name} ${r.id} ${r.email}`}
            toolbar={
              <>
                <select className={sel} value={dept} onChange={(e) => setDept(e.target.value)} aria-label="Department">
                  <option value="all">All departments</option>
                  {[...new Set(ALL.map((s) => s.department))].map((d) => (
                    <option key={d}>{d}</option>
                  ))}
                </select>
                <select className={sel} value={year} onChange={(e) => setYear(e.target.value)} aria-label="Year">
                  <option value="all">All years</option>
                  {[1, 2, 3, 4].map((y) => (
                    <option key={y}>{y}</option>
                  ))}
                </select>
                <select className={sel} value={enr} onChange={(e) => setEnr(e.target.value)} aria-label="Enrollment">
                  <option value="all">Any enrollment</option>
                  <option value="registered">Registered</option>
                  <option value="inactive">Inactive</option>
                </select>
                <select className={sel} value={acct} onChange={(e) => setAcct(e.target.value)} aria-label="Account">
                  <option value="all">Any account</option>
                  <option value="active">Active</option>
                  <option value="suspended">Suspended</option>
                </select>
              </>
            }
          />
        </div>
      </div>

      <DetailDrawer open={!!active} onOpenChange={(v) => !v && setActive(null)} title={activeFresh?.name ?? ""}>
        {activeFresh ? (
          <>
            {!editing ? (
              <div>
                <Field label="Student ID">{activeFresh.id}</Field>
                <Field label="Department">{activeFresh.department}</Field>
                <Field label="Year">{activeFresh.year}</Field>
                <Field label="Email">{activeFresh.email}</Field>
                <Field label="Phone">{activeFresh.phone || "—"}</Field>
                <Field label="Enrollment"><StatusBadge status={activeFresh.enrollment} /></Field>
                <Field label="Account"><StatusBadge status={activeFresh.account} /></Field>
                <Field label="Face enrolled">
                  <StatusBadge status={activeFresh.faceEnrolled ? "registered" : "pending"} />
                </Field>
                <Field label="Consent">
                  {activeFresh.consentGiven ? `Given · ${activeFresh.consentDate}` : "Not recorded"}
                </Field>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Department</label>
                  <Input value={form.department} onChange={(e) => setForm((f) => ({ ...f, department: e.target.value }))} />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Year</label>
                  <Input value={form.year} onChange={(e) => setForm((f) => ({ ...f, year: e.target.value }))} />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Email</label>
                  <Input value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Phone</label>
                  <Input value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} />
                </div>
                <div className="flex gap-2 pt-1">
                  <Button size="sm" onClick={saveEdit} disabled={saving}>
                    {saving ? "Saving…" : "Save"}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setEditing(false)}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            <div>
              <h3 className="mb-2 font-mono text-[0.65rem] uppercase tracking-wider text-muted-foreground">
                Linked vehicles
              </h3>
              <ul className="space-y-1.5">
                {vehiclesForStudent(activeFresh.id).map((v) => (
                  <li key={v.id} className="flex items-center justify-between rounded border border-border px-2 py-1.5">
                    <span className="font-mono text-xs">{v.plate}</span>
                    <span className="flex items-center gap-1.5">
                      <Badge2 tone="muted">{v.type}</Badge2>
                      <StatusBadge status={v.status} />
                      {v.blocklisted ? <Badge2 tone="danger">blocklisted</Badge2> : null}
                    </span>
                  </li>
                ))}
                {vehiclesForStudent(activeFresh.id).length === 0 ? (
                  <li className="text-sm text-muted-foreground">No vehicles registered.</li>
                ) : null}
              </ul>
            </div>

            <div>
              <h3 className="mb-2 font-mono text-[0.65rem] uppercase tracking-wider text-muted-foreground">
                Recent entry history
              </h3>
              <ul className="space-y-1">
                {history.length === 0 ? (
                  <li className="text-sm text-muted-foreground">No entries yet.</li>
                ) : (
                  history.map((e) => (
                    <li key={e.id} className="flex items-center justify-between text-xs">
                      <span className="font-mono text-muted-foreground">{fmtDateTime(e.ts)}</span>
                      <span className="font-mono">{e.plate}</span>
                      <StatusBadge status={e.status} />
                    </li>
                  ))
                )}
              </ul>
            </div>

            <RoleGate
              permission="edit"
              fallback={
                <p className="rounded border border-border bg-surface-2 px-3 py-2 text-xs text-muted-foreground">
                  Guards have read-only access to student records.
                </p>
              }
            >
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={openEdit}>Edit info</Button>
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) reEnrollFace(file);
                    e.target.value = "";
                  }}
                />
                <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()}>
                  Re-enroll face
                </Button>
                <Button size="sm" variant="outline" onClick={toggleAccount}>
                  {activeFresh.account === "active" ? "Suspend account" : "Reactivate"}
                </Button>
                <Button size="sm" variant="destructive" onClick={softDelete}>Soft delete</Button>
              </div>
            </RoleGate>
          </>
        ) : null}
      </DetailDrawer>
    </div>
  );
}
