import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/app/AppShell";
import { Card } from "@/components/app/shared";
import ResultsPlayer from "@/components/app/ResultsPlayer";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";

export default function Analysis() {
  const [config, setConfig] = useState(null);
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [job, setJob] = useState(null); // {id, status, progress}
  const fileRef = useRef(null);

  const loadDemo = () =>
    api.getDemoResults().then(setResults).catch((e) => setError(e.message));

  useEffect(() => {
    api.getConfig().then((c) => {
      setConfig(c);
      if (c.demo_mode) loadDemo();
    }).catch((e) => setError(e.message));
  }, []);

  // poll the analysis job (local mode)
  useEffect(() => {
    if (!job || job.status === "done" || job.status === "error") return undefined;
    const id = setInterval(async () => {
      try {
        const s = await api.getAnalysis(job.id);
        setJob({ id: job.id, status: s.status, progress: s.progress, message: s.message });
        if (s.status === "done") { setResults(s.results); toast.success("Analysis finished"); }
        if (s.status === "error") toast.error(s.message || "Analysis failed");
      } catch (e) { setJob({ ...job, status: "error", message: e.message }); }
    }, 1500);
    return () => clearInterval(id);
  }, [job]);

  const onFile = async (file) => {
    setError(""); setResults(null);
    try {
      const { job_id } = await api.uploadAnalysis(file);
      setJob({ id: job_id, status: "queued", progress: 0 });
    } catch (e) { setError(e.message); }
  };

  const demoMode = !!config?.demo_mode;
  return (
    <div>
      <PageHeader
        title="Video Analysis"
        subtitle={demoMode ? "Demo mode — precomputed results replayed in sync with the video" : "Local mode — upload any video and run the real pipeline"}
      />
      <div className="space-y-3 p-3">
        {error ? <div className="rounded border border-destructive/50 bg-destructive/10 px-3 py-2 text-xs text-destructive">{error}</div> : null}

        {config && !demoMode ? (
          <Card title="Analyse a video" bodyClassName="p-3">
            <input ref={fileRef} type="file" accept="video/*" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }} />
            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" onClick={() => fileRef.current?.click()} disabled={job && ["queued", "running"].includes(job.status)}>Upload video</Button>
              <Button size="sm" variant="outline" onClick={loadDemo}>Load bundled demo results</Button>
              {job ? (
                <span className="font-mono text-xs text-muted-foreground">
                  {job.status === "error" ? `failed: ${job.message}` : `${job.status} ${Math.round((job.progress ?? 0) * 100)}%`}
                </span>
              ) : null}
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Runs YOLO + EasyOCR on your machine (CPU: roughly real-time or slower). Events are also written to the Entry Logs / Alerts pages.
            </p>
          </Card>
        ) : null}

        {results ? <ResultsPlayer results={results} demoMode={demoMode} /> : !error && config ? (
          <p className="font-mono text-xs text-muted-foreground">{demoMode ? "Loading demo results…" : "Upload a video to begin."}</p>
        ) : null}
      </div>
    </div>
  );
}
