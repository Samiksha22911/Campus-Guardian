import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { PageHeader } from "@/components/app/AppShell";
import { Card, StatCard } from "@/components/app/shared";
import { api } from "@/lib/api-client";
import { toast } from "sonner";

export const Route = createFileRoute("/_app/analytics")({
  head: () => ({
    meta: [
      { title: "Analytics — Campus Guardian AI" },
      {
        name: "description",
        content:
          "Campus entry analytics: grant rate, peak traffic hours, per-gate volume and detection confidence trends.",
      },
      { property: "og:title", content: "Analytics — Campus Guardian AI" },
      { property: "og:description", content: "Trends across every verified campus gate entry." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: AnalyticsPage,
});

const OUTCOME_COLORS = {
  Granted: "var(--success)",
  Manual: "var(--primary)",
  Uncertain: "var(--warning)",
  Denied: "var(--destructive)",
};

function AnalyticsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    api
      .getAnalytics()
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => toast.error("Could not load analytics", { description: err.message }))
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <PageHeader title="Analytics" subtitle="Trends across every verified campus gate entry" />

      {loading ? (
        <p className="p-6 text-sm text-muted-foreground">Loading analytics…</p>
      ) : !data || data.total_entries === 0 ? (
        <p className="p-6 text-sm text-muted-foreground">No entries recorded yet — analytics will appear once the gate starts logging verifications.</p>
      ) : (
        <>
          <div className="grid gap-3 p-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Total entries" value={data.total_entries} tone="primary" />
            <StatCard label="Grant rate" value={`${data.grant_rate.toFixed(1)}%`} tone="success" />
            <StatCard label="Avg. OCR confidence" value={`${data.avg_ocr_confidence.toFixed(1)}%`} tone="primary" />
            <StatCard label="Peak hour" value={data.peak_hour} tone="warning" />
          </div>

          <div className="grid gap-3 p-3 xl:grid-cols-3">
            <Card title="Entries by hour" className="xl:col-span-2" bodyClassName="p-3">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data.hourly}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="hour" tick={{ fontSize: 10 }} interval={2} />
                  <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border)", fontSize: 12 }}
                  />
                  <Bar dataKey="entries" fill="var(--primary)" radius={[3, 3, 0, 0]} name="Entries" />
                  <Bar dataKey="denied" fill="var(--destructive)" radius={[3, 3, 0, 0]} name="Denied" />
                </BarChart>
              </ResponsiveContainer>
            </Card>

            <Card title="Outcome breakdown" bodyClassName="p-3">
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie data={data.outcomes} dataKey="value" nameKey="name" innerRadius={45} outerRadius={80} paddingAngle={2}>
                    {data.outcomes.map((entry) => (
                      <Cell key={entry.name} fill={OUTCOME_COLORS[entry.name] ?? "var(--muted)"} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border)", fontSize: 12 }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <ul className="flex flex-wrap justify-center gap-3 px-3 pb-3 text-xs">
                {data.outcomes.map((o) => (
                  <li key={o.name} className="flex items-center gap-1.5">
                    <span
                      className="size-2.5 rounded-full"
                      style={{ background: OUTCOME_COLORS[o.name] ?? "var(--muted)" }}
                    />
                    {o.name} ({o.value})
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          <div className="grid gap-3 px-3 pb-6 xl:grid-cols-2">
            <Card title="Volume by gate" bodyClassName="p-3">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={data.by_gate} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis type="number" tick={{ fontSize: 10 }} allowDecimals={false} />
                  <YAxis type="category" dataKey="gate" tick={{ fontSize: 10 }} width={70} />
                  <Tooltip
                    contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border)", fontSize: 12 }}
                  />
                  <Bar dataKey="count" fill="var(--primary)" radius={[0, 3, 3, 0]} name="Entries" />
                </BarChart>
              </ResponsiveContainer>
            </Card>

            <Card title="Detection confidence" bodyClassName="space-y-4 p-4">
              <div>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span>Average OCR confidence</span>
                  <span className="font-mono text-primary">{data.avg_ocr_confidence.toFixed(1)}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-surface-2">
                  <div className="h-full bg-primary" style={{ width: `${data.avg_ocr_confidence}%` }} />
                </div>
              </div>
              <div>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span>Average face-match confidence</span>
                  <span className="font-mono text-primary">{data.avg_face_confidence.toFixed(1)}%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-surface-2">
                  <div className="h-full bg-primary" style={{ width: `${data.avg_face_confidence}%` }} />
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Computed from every stored entry log. Face-match confidence only includes entries where face
                verification actually ran.
              </p>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
