import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { PageHeader } from "@/components/app/AppShell";
import { Badge2, Card, Field, RoleGate } from "@/components/app/shared";
import { ROLE_LABEL, useApp } from "@/lib/app-store";
import { GATES } from "@/lib/campus-data";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";

export const Route = createFileRoute("/_app/settings")({
  head: () => ({
    meta: [
      { title: "System Settings — Campus Gate AI" },
      {
        name: "description",
        content:
          "Tune recognition thresholds, camera assignments, alert routing, data retention and operator accounts for the campus security system.",
      },
      { property: "og:title", content: "System Settings — Campus Gate AI" },
      { property: "og:description", content: "Configure AI thresholds, cameras, alerts and operator roles." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: SettingsPage,
});

function SettingsPage() {
  const { thresholds, setThresholds, aiOnline, setAiOnline, user, users, loadUsers, createUser } = useApp();
  const [retention, setRetention] = useState(90);
  const [notify, setNotify] = useState({ sound: true, desktop: true, email: false });
  const [newUser, setNewUser] = useState({ name: "", email: "", password: "", role: "security_officer" });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  return (
    <div>
      <PageHeader title="System Settings" subtitle="Detection tuning, camera assignment, alerts and access control" />

      <div className="grid gap-3 p-3 xl:grid-cols-2">
        <Card title="Recognition thresholds" subtitle="Below these values an entry is marked uncertain">
          <div className="space-y-5 p-4">
            <div>
              <div className="mb-2 flex items-center justify-between text-xs">
                <span>Plate OCR confidence</span>
                <span className="font-mono text-primary">{thresholds.ocr}%</span>
              </div>
              <Slider value={[thresholds.ocr]} min={50} max={99} step={1} onValueChange={([v]) => setThresholds({ ...thresholds, ocr: v ?? 85 })} />
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between text-xs">
                <span>Face match confidence</span>
                <span className="font-mono text-primary">{thresholds.face}%</span>
              </div>
              <Slider value={[thresholds.face]} min={50} max={99} step={1} onValueChange={([v]) => setThresholds({ ...thresholds, face: v ?? 78 })} />
            </div>
            <div className="flex items-center justify-between border-t border-border pt-4">
              <span className="text-sm">AI detection service</span>
              <div className="flex items-center gap-2">
                <Badge2 tone={aiOnline ? "success" : "danger"}>{aiOnline ? "online" : "paused"}</Badge2>
                <Switch checked={aiOnline} onCheckedChange={setAiOnline} />
              </div>
            </div>
          </div>
        </Card>

        <Card title="Camera assignment" subtitle="Streams mapped to gates">
          <ul className="divide-y divide-border">
            {GATES.map((g) => (
              <li key={g.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
                <span>
                  {g.label}
                  <span className="ml-2 font-mono text-[0.6rem] text-muted-foreground">{g.id}</span>
                </span>
                <Badge2 tone="success">streaming</Badge2>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Alert routing & notifications">
          <div className="space-y-3 p-4 text-sm">
            {([
              ["sound", "Audible alarm for critical alerts"],
              ["desktop", "Desktop notifications"],
              ["email", "Email digest to security lead"],
            ] as const).map(([k, label]) => (
              <div key={k} className="flex items-center justify-between">
                <span>{label}</span>
                <Switch checked={notify[k]} onCheckedChange={(c) => setNotify((p) => ({ ...p, [k]: c }))} />
              </div>
            ))}
          </div>
        </Card>

        <Card title="Data retention & privacy">
          <div className="space-y-4 p-4">
            <div>
              <div className="mb-2 flex items-center justify-between text-xs">
                <span>Retain captured frames and logs</span>
                <span className="font-mono text-primary">{retention} days</span>
              </div>
              <Slider value={[retention]} min={7} max={365} step={1} onValueChange={([v]) => setRetention(v ?? 90)} />
            </div>
            <p className="text-xs text-muted-foreground">
              Biometric templates are stored as irreversible embeddings and purged when a student's consent is withdrawn.
            </p>
            <RoleGate permission="settings" fallback={null}>
              <Button size="sm" variant="outline" onClick={() => toast.success("Retention policy saved")}>
                Save policy
              </Button>
            </RoleGate>
          </div>
        </Card>

        <Card title="Operator accounts" subtitle="Role-based access control" className="xl:col-span-2">
          <ul className="divide-y divide-border">
            {users.map((u) => (
              <li key={u.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
                <div>
                  <p className="text-sm font-medium">
                    {u.name} {u.id === user?.id ? <span className="text-xs text-muted-foreground">(you)</span> : null}
                  </p>
                  <p className="font-mono text-[0.65rem] text-muted-foreground">{u.email}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge2 tone={u.role === "admin" ? "primary" : "muted"}>
                    {ROLE_LABEL[u.role] ?? u.role}
                  </Badge2>
                  {!u.isActive ? <Badge2 tone="muted">inactive</Badge2> : null}
                </div>
              </li>
            ))}
            {users.length === 0 ? (
              <li className="px-4 py-3 text-sm text-muted-foreground">
                <RoleGate permission="settings" fallback="Only admins can view operator accounts.">
                  Loading…
                </RoleGate>
              </li>
            ) : null}
          </ul>
          <RoleGate permission="settings" fallback={null}>
            <div className="grid gap-2 border-t border-border p-4 sm:grid-cols-4">
              <Input
                placeholder="Full name"
                value={newUser.name}
                onChange={(e) => setNewUser((f) => ({ ...f, name: e.target.value }))}
              />
              <Input
                placeholder="Email"
                value={newUser.email}
                onChange={(e) => setNewUser((f) => ({ ...f, email: e.target.value }))}
              />
              <Input
                placeholder="Temp password"
                value={newUser.password}
                onChange={(e) => setNewUser((f) => ({ ...f, password: e.target.value }))}
              />
              <div className="flex gap-2">
                <select
                  className="h-9 flex-1 rounded-md border border-border bg-surface-2 px-2 text-sm"
                  value={newUser.role}
                  onChange={(e) => setNewUser((f) => ({ ...f, role: e.target.value }))}
                >
                  <option value="security_officer">Security Officer</option>
                  <option value="admin">Admin</option>
                </select>
                <Button
                  size="sm"
                  disabled={creating || !newUser.name || !newUser.email || newUser.password.length < 6}
                  onClick={async () => {
                    setCreating(true);
                    try {
                      await createUser(newUser);
                      toast.success(`Account created for ${newUser.name}`);
                      setNewUser({ name: "", email: "", password: "", role: "security_officer" });
                    } catch (err: any) {
                      toast.error("Could not create account", { description: err.message });
                    } finally {
                      setCreating(false);
                    }
                  }}
                >
                  Add
                </Button>
              </div>
            </div>
          </RoleGate>
          <div className="border-t border-border p-4">
            <Field label="Audit">Every setting change is written to the immutable audit trail.</Field>
          </div>
        </Card>
      </div>
    </div>
  );
}
