import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Card } from "@/components/app/shared";
import { mediaUrl } from "@/lib/api-client";
import { cn } from "@/lib/utils";

/**
 * THE one results UI. Both modes render this with the same `results` object
 * (schema in demo-data/results.schema.json):
 *   - hosted demo  : results = precomputed demo-data/results.json (+ live DB status)
 *   - local upload : results = produced by the real pipeline for your own video
 * Everything shown (box, plate, DB status, decision, entry log) is driven by the
 * video's currentTime, so it stays in sync with playback, scrubbing and looping.
 */

const DECISION_STYLE = {
  ALLOWED: "border-success/60 bg-success/20 text-success",
  DENIED: "border-destructive/60 bg-destructive/20 text-destructive",
  REVIEW: "border-warning/60 bg-warning/20 text-warning",
};
const DB_LABEL = {
  REGISTERED: "Registered", UNREGISTERED: "Not registered", BLOCKLISTED: "Blocklisted", INACTIVE: "Inactive",
  PENDING: "Pending approval", LOW_CONFIDENCE: "OCR too uncertain", NO_PLATE: "No readable plate", NOT_CHECKED: "Not checked",
};
const fmt = (s) => `${Math.floor(s / 60)}:${(s % 60).toFixed(1).padStart(4, "0")}`;
const pct = (v) => `${Math.round((v ?? 0) * 100)}%`;

/** Box position at time t - interpolates the event's `track` so the box follows the vehicle. */
function boxAt(ev, t) {
  const tr = ev.track;
  if (!tr || tr.length < 2) return ev.bbox;
  if (t <= tr[0].t) return tr[0];
  if (t >= tr[tr.length - 1].t) return tr[tr.length - 1];
  const i = tr.findIndex((p) => p.t >= t);
  const a = tr[i - 1], b = tr[i];
  const k = (t - a.t) / (b.t - a.t || 1);
  return { x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k, w: a.w + (b.w - a.w) * k, h: a.h + (b.h - a.h) * k };
}

function Banner({ results, demoMode }) {
  const gen = results?.meta?.generated_by;
  if (gen === "sample")
    return (
      <div className="mb-2 rounded border border-warning/50 bg-warning/10 px-3 py-2 text-xs text-warning">
        <b>Sample data</b> — this is a format example, not output of the real pipeline. Run{" "}
        <code>ai-service/analyze_video.py</code> on your video and commit <code>demo-data/results.json</code>.
      </div>
    );
  return (
    <div className="mb-2 rounded border border-primary/40 bg-primary/10 px-3 py-2 text-xs text-primary">
      {demoMode
        ? "Demo mode: detections, plate text and confidences are precomputed offline by the real pipeline (YOLO plate detection + EasyOCR) on this video. Database status and login are live."
        : "Analysed by the local pipeline (YOLO + EasyOCR + database lookup) on your video."}
    </div>
  );
}

export default function ResultsPlayer({ results, demoMode = false }) {
  const videoRef = useRef(null);
  const [t, setT] = useState(0);
  const events = useMemo(() => results?.events ?? [], [results]);
  const vw = results?.video?.width || 16, vh = results?.video?.height || 9;

  // currentTime -> state, ~60 fps while playing (also catches seeking & loop restarts).
  useEffect(() => {
    let raf;
    const tick = () => {
      if (videoRef.current) setT(videoRef.current.currentTime);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  const seek = useCallback((time) => {
    if (videoRef.current) videoRef.current.currentTime = Math.max(0, time);
  }, []);

  const visible = events.filter((e) => t >= (e.ts_start ?? e.timestamp) - 0.15 && t <= (e.ts_end ?? e.timestamp) + 0.5);
  const decided = events.filter((e) => e.timestamp <= t);       // entry log = everything decided so far
  const current = [...decided].reverse()[0] ?? null;

  const stepsFor = (e) => {
    if (!e) return [false, false, false, false, false];
    const s = e.ts_start ?? e.timestamp, mid = s + (e.timestamp - s) * 0.5;
    return [t >= s, t >= mid, t >= e.timestamp, t >= e.timestamp, t >= e.timestamp];
  };
  const active = visible.find((e) => t < e.timestamp) ?? current;
  const steps = stepsFor(active);
  const STEPS = ["Plate detected", "OCR read", "DB lookup", "Face check", "Decision"];

  if (!results) return null;

  return (
    <div>
      <Banner results={results} demoMode={demoMode} />
      <div className="grid gap-3 xl:grid-cols-3">
        <Card title="Gate camera" className="xl:col-span-2" bodyClassName="p-3">
          <div className="relative w-full overflow-hidden rounded border border-border bg-black" style={{ aspectRatio: `${vw} / ${vh}` }}>
            <video ref={videoRef} src={mediaUrl(results.video?.src)} className="absolute inset-0 h-full w-full" controls loop muted playsInline autoPlay />
            {/* overlay: pointer-events none so the native controls stay clickable */}
            <div className="pointer-events-none absolute inset-0">
              {visible.map((e) => {
                const b = boxAt(e, t);
                const done = t >= e.timestamp;
                return (
                  <div key={e.id} className={cn("absolute border-2", done ? (e.decision === "ALLOWED" ? "border-success" : e.decision === "DENIED" ? "border-destructive" : "border-warning") : "border-primary")}
                    style={{ left: `${b.x * 100}%`, top: `${b.y * 100}%`, width: `${b.w * 100}%`, height: `${b.h * 100}%` }}>
                    <span className={cn("absolute -top-6 left-0 whitespace-nowrap rounded border px-1.5 py-0.5 font-mono text-[0.65rem] font-semibold", done ? DECISION_STYLE[e.decision] : "border-primary/60 bg-black/70 text-primary")}>
                      {done ? `${e.plate_text ?? "UNREADABLE"} · ${e.decision}` : "detecting…"}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-1.5">
            {STEPS.map((s, i) => (
              <div key={s} className="flex items-center gap-1.5">
                <span className={cn("rounded-full border px-2 py-0.5 font-mono text-[0.6rem] uppercase tracking-wider", steps[i] ? "border-success/40 bg-success/10 text-success" : "border-border text-muted-foreground")}>{s}</span>
                {i < STEPS.length - 1 ? <span className="text-muted-foreground">→</span> : null}
              </div>
            ))}
            <span className="ml-auto font-mono text-[0.65rem] text-muted-foreground">t = {fmt(t)}</span>
          </div>
        </Card>

        <Card title="Current verification" bodyClassName="p-3 text-sm">
          {!current ? (
            <p className="text-muted-foreground">Waiting for a vehicle… press play.</p>
          ) : (
            <div className="space-y-2">
              <div className={cn("rounded border px-3 py-2 text-center font-mono text-lg font-semibold", DECISION_STYLE[current.decision])}>{current.decision}</div>
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
                <dt className="text-muted-foreground">Plate</dt><dd className="font-mono">{current.plate_text ?? "unreadable"}</dd>
                <dt className="text-muted-foreground">OCR confidence</dt><dd className="font-mono">{pct(current.plate_confidence)}</dd>
                <dt className="text-muted-foreground">Database</dt><dd>{DB_LABEL[current.db_status] ?? current.db_status}</dd>
                <dt className="text-muted-foreground">Owner</dt><dd>{current.owner_name ?? "—"}</dd>
                <dt className="text-muted-foreground">Face match</dt>
                <dd>{current.face_score == null ? "Not performed" : `${current.face_match_name ?? "no match"} (${pct(current.face_score)})`}</dd>
              </dl>
            </div>
          )}
        </Card>

        <Card title={`Entry log (${decided.length}/${events.length})`} className="xl:col-span-3" bodyClassName="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-border font-mono uppercase tracking-wider text-muted-foreground">
                <tr>{["Video time", "Plate", "OCR conf.", "Face match", "Database", "Decision"].map((h) => <th key={h} className="px-3 py-2 font-normal">{h}</th>)}</tr>
              </thead>
              <tbody>
                {events.length === 0 ? (
                  <tr><td colSpan={6} className="px-3 py-4 text-muted-foreground">No vehicles were detected in this video.</td></tr>
                ) : null}
                {[...decided].reverse().map((e) => (
                  <tr key={e.id} onClick={() => seek((e.ts_start ?? e.timestamp) - 0.2)} className="cursor-pointer border-b border-border/60 hover:bg-surface-2">
                    <td className="px-3 py-2 font-mono">{fmt(e.timestamp)}</td>
                    <td className="px-3 py-2 font-mono">{e.plate_text ?? "unreadable"}</td>
                    <td className="px-3 py-2 font-mono">{pct(e.plate_confidence)}</td>
                    <td className="px-3 py-2">{e.face_score == null ? "—" : `${e.face_match_name ?? "no match"} (${pct(e.face_score)})`}</td>
                    <td className="px-3 py-2">{DB_LABEL[e.db_status] ?? e.db_status}</td>
                    <td className="px-3 py-2"><span className={cn("rounded border px-2 py-0.5 font-mono", DECISION_STYLE[e.decision])}>{e.decision}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
