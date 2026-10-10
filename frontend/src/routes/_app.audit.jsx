import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@/components/app/AppShell";
import { Badge2, DataTable } from "@/components/app/shared";
import { api } from "@/lib/api-client";
import { fmtDateTime } from "@/lib/campus-data";
import { toast } from "sonner";

export const Route = createFileRoute("/_app/audit")({
  head: () => ({
    meta: [
      { title: "Audit Logs — Campus Gate AI" },
      {
        name: "description",
        content: "Immutable trail of every account, student, vehicle and verification change made in the console.",
      },
      { property: "og:title", content: "Audit Logs — Campus Gate AI" },
      { property: "og:description", content: "Who changed what, and when, across Campus Gate AI." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: AuditPage,
});

const sel = "rounded-md border border-border bg-surface-2 px-2 py-1 font-mono text-xs";

const ACTION_TONE = {
  CREATE: "success",
  UPDATE: "primary",
  DEACTIVATE: "danger",
  DELETE: "danger",
  VERIFY: "muted",
};

function AuditPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState("all");
  const [entity, setEntity] = useState("all");

  useEffect(() => {
    api
      .getAuditLogs(300)
      .then(setLogs)
      .catch((err) => toast.error("Could not load audit logs", { description: err.message }))
      .finally(() => setLoading(false));
  }, []);

  const actions = useMemo(() => Array.from(new Set(logs.map((l) => l.action))).sort(), [logs]);
  const entities = useMemo(() => Array.from(new Set(logs.map((l) => l.entity_type))).sort(), [logs]);

  const rows = useMemo(
    () =>
      logs.filter(
        (l) => (action === "all" || l.action === action) && (entity === "all" || l.entity_type === entity),
      ),
    [logs, action, entity],
  );

  const cols = [
    {
      key: "created_at",
      header: "Time",
      render: (r) => <span className="font-mono text-xs">{fmtDateTime(r.created_at)}</span>,
      sortValue: (r) => new Date(r.created_at).getTime(),
    },
    {
      key: "action",
      header: "Action",
      render: (r) => <Badge2 tone={ACTION_TONE[r.action] ?? "muted"}>{r.action}</Badge2>,
    },
    { key: "entity_type", header: "Entity", render: (r) => <span className="font-mono text-xs">{r.entity_type}</span> },
    { key: "entity_id", header: "Entity ID", render: (r) => <span className="font-mono text-xs">{r.entity_id ?? "—"}</span> },
    { key: "user_id", header: "By user", render: (r) => <span className="font-mono text-xs">{r.user_id ?? "system"}</span> },
    { key: "description", header: "Description", render: (r) => r.description ?? "—" },
  ];

  return (
    <div>
      <PageHeader title="Audit Logs" subtitle="Every account, student, vehicle and verification change, in order" />
      <div className="p-3">
        <div className="panel overflow-hidden">
          <DataTable
            rows={rows}
            columns={cols}
            pageSize={16}
            searchPlaceholder="Search description…"
            searchFields={(r) => `${r.description ?? ""} ${r.entity_type} ${r.action}`}
            toolbar={
              <>
                <select className={sel} value={action} onChange={(e) => setAction(e.target.value)} aria-label="Action">
                  <option value="all">Any action</option>
                  {actions.map((a) => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
                <select className={sel} value={entity} onChange={(e) => setEntity(e.target.value)} aria-label="Entity type">
                  <option value="all">Any entity</option>
                  {entities.map((e) => (
                    <option key={e} value={e}>{e}</option>
                  ))}
                </select>
              </>
            }
          />
          {loading ? <p className="p-4 text-sm text-muted-foreground">Loading…</p> : null}
          {!loading && rows.length === 0 ? (
            <p className="p-4 text-sm text-muted-foreground">No audit entries yet.</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
