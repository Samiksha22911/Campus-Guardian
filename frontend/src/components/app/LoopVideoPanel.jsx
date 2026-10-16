import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const VIDEO_SRC = import.meta.env.VITE_DEMO_VIDEO_URL || "/demo.mp4";
const MAX_WIDTH = 960; // downscale frames before upload - faster, and plenty for plate detection

const STATUS_STYLE = {
  granted: "border-success/60 bg-success/20 text-success",
  denied: "border-destructive/60 bg-destructive/20 text-destructive",
  uncertain: "border-warning/60 bg-warning/20 text-warning",
  manual: "border-primary/60 bg-primary/20 text-primary",
};

/**
 * Plays a recorded video in a loop (stand-in for a live gate camera) and, while
 * "Auto-verify" is on, grabs a frame every few seconds and sends it through the
 * normal /api/verification/process pipeline (live=true -> empty frames and
 * repeat sightings of the same plate are ignored by the backend).
 */
export default function LoopVideoPanel({ gate, current, aiOnline, runVerification, fallback }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const busyRef = useRef(false);
  const runRef = useRef(runVerification);
  runRef.current = runVerification;

  const [videoOk, setVideoOk] = useState(true);
  const [auto, setAuto] = useState(false);
  const [everyMs, setEveryMs] = useState(3000);
  const [sent, setSent] = useState(0);

  const grabAndVerify = useCallback(async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || busyRef.current) return;
    if (video.paused || video.readyState < 2 || !video.videoWidth) return;

    busyRef.current = true;
    try {
      const scale = Math.min(1, MAX_WIDTH / video.videoWidth);
      canvas.width = Math.round(video.videoWidth * scale);
      canvas.height = Math.round(video.videoHeight * scale);
      canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);

      const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
      if (!blob) return;

      const file = new File([blob], `frame-${Date.now()}.jpg`, { type: "image/jpeg" });
      setSent((n) => n + 1);
      await runRef.current(file, { live: true });
    } finally {
      busyRef.current = false; // never fire a new request while one is in flight
    }
  }, []);

  useEffect(() => {
    if (!auto || !aiOnline) return undefined;
    const id = setInterval(grabAndVerify, everyMs);
    return () => clearInterval(id);
  }, [auto, aiOnline, everyMs, grabAndVerify]);

  if (!videoOk) {
    return (
      <div>
        <div className="mb-2 rounded border border-warning/40 bg-warning/10 px-3 py-2 text-xs text-warning">
          Demo video not found at <code>{VIDEO_SRC}</code>. Put your recording at <code>frontend/public/demo.mp4</code> and redeploy.
          Showing the placeholder camera instead.
        </div>
        {fallback}
      </div>
    );
  }

  return (
    <div>
      <div className="relative overflow-hidden rounded border border-border bg-black">
        <video
          ref={videoRef}
          src={VIDEO_SRC}
          className="aspect-video w-full object-cover"
          autoPlay
          loop
          muted
          playsInline
          onError={() => setVideoOk(false)}
        />
        <span className="absolute left-2 top-2 rounded bg-black/60 px-2 py-0.5 font-mono text-[0.6rem] uppercase tracking-wider text-white">
          ● {gate} · demo loop
        </span>
        {current ? (
          <span
            className={cn(
              "absolute bottom-2 left-2 rounded border px-2 py-1 font-mono text-xs font-semibold",
              STATUS_STYLE[current.status] ?? STATUS_STYLE.uncertain,
            )}
          >
            {current.plate} · {current.status.toUpperCase()} · {current.plateConfidence}%
          </span>
        ) : null}
      </div>

      <canvas ref={canvasRef} className="hidden" />

      <div className="mt-2 flex flex-wrap items-center gap-2">
        <Button size="sm" variant={auto ? "destructive" : "default"} onClick={() => setAuto((v) => !v)} disabled={!aiOnline}>
          {auto ? "Stop auto-verify" : "Start auto-verify"}
        </Button>
        <select
          value={everyMs}
          onChange={(e) => setEveryMs(Number(e.target.value))}
          className="rounded-md border border-border bg-surface-2 px-2 py-1.5 font-mono text-xs"
          aria-label="Frame interval"
        >
          <option value={2000}>every 2 s</option>
          <option value={3000}>every 3 s</option>
          <option value={5000}>every 5 s</option>
        </select>
        <Button size="sm" variant="outline" onClick={grabAndVerify} disabled={!aiOnline}>
          Verify this frame now
        </Button>
        <span className="font-mono text-[0.65rem] text-muted-foreground">frames sent: {sent}</span>
      </div>
    </div>
  );
}
