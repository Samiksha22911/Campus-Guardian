import camGate from "@/assets/cam-gate.jpg";
import camVehicle from "@/assets/cam-vehicle.jpg";
import camPerimeter from "@/assets/cam-perimeter.jpg";
import camServer from "@/assets/cam-serverroom.jpg";

import { Tag } from "./primitives";

/* ---------- Camera Feed Data ---------- */

const feeds = [
  {
    id: "CAM-01",
    label: "Gate 1 — Pedestrian",
    src: camGate,
    model: "FaceNet-512 · liveness on",
    box: {
      top: "58%",
      left: "50%",
      width: "13%",
      height: "30%",
      label: "MATCH 98.4%",
    },
    tone: "success",
  },
  {
    id: "CAM-04",
    label: "Vehicle Gate A",
    src: camVehicle,
    model: "ANPR · YOLOv8 + CRNN",
    box: {
      top: "66%",
      left: "51%",
      width: "22%",
      height: "22%",
      label: "KA 05 MJ 4471",
    },
    tone: "primary",
  },
  {
    id: "CAM-11",
    label: "North Perimeter",
    src: camPerimeter,
    model: "Intrusion · tripwire zone",
    box: {
      top: "48%",
      left: "26%",
      width: "16%",
      height: "26%",
      label: "MOTION · REVIEW",
    },
    tone: "accent",
  },
  {
    id: "CAM-17",
    label: "Server Room Corridor",
    src: camServer,
    model: "Loitering + access control",
    box: {
      top: "38%",
      left: "52%",
      width: "16%",
      height: "40%",
      label: "DOOR SECURE",
    },
    tone: "success",
  },
];

/* ---------- Camera Border Colors ---------- */

const toneRing = {
  primary: "border-primary text-primary",
  success: "border-success text-success",
  danger: "border-destructive text-destructive",
  accent: "border-accent text-accent",
};

/* ---------- Camera Wall ---------- */

export function CameraWall() {
  return (
    <div className="grid grid-cols-1 gap-3 p-3 sm:grid-cols-2">
      {feeds.map((feed, index) => {
        const ringClass = toneRing[feed.tone];

        return (
          <figure
            key={feed.id}
            className="group relative overflow-hidden rounded-md border border-border bg-black"
          >
            {/* Camera Image */}
            <img
              src={feed.src}
              alt={`${feed.label} camera feed`}
              width={1024}
              height={640}
              loading={index === 0 ? "eager" : "lazy"}
              className="aspect-video w-full object-cover opacity-80 transition-opacity duration-300 group-hover:opacity-100"
            />

            {/* Scanline Effect */}
            <div className="pointer-events-none absolute inset-0 scanline opacity-40" />

            {/* Sweep Animation */}
            <div className="pointer-events-none absolute inset-x-0 top-0 h-8 bg-primary/20 blur-md sweep-line" />

            {/* Detection Box */}
            <div
              className={`pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 border-2 ${ringClass}`}
              style={{
                top: feed.box.top,
                left: feed.box.left,
                width: feed.box.width,
                height: feed.box.height,
              }}
            >
              <span
                className={`absolute -top-5 left-0 whitespace-nowrap bg-background/85 px-1 font-mono text-[0.6rem] tracking-wider ${ringClass}`}
              >
                {feed.box.label}
              </span>
            </div>

            {/* Camera Header */}
            <figcaption className="absolute inset-x-0 top-0 flex items-start justify-between p-2.5">
              <span className="rounded bg-background/75 px-1.5 py-0.5 font-mono text-[0.65rem] tracking-wider text-foreground backdrop-blur">
                {feed.id} · {feed.label}
              </span>

              <span className="flex items-center gap-1.5 rounded bg-background/75 px-1.5 py-0.5 font-mono text-[0.6rem] uppercase tracking-wider text-destructive backdrop-blur">
                <span className="live-dot inline-block size-1.5 rounded-full bg-destructive" />
                live
              </span>
            </figcaption>

            {/* Camera Footer */}
            <div className="absolute inset-x-0 bottom-0 flex items-center justify-between gap-2 bg-gradient-to-t from-background/90 to-transparent px-2.5 pb-2 pt-6">
              <span className="font-mono text-[0.62rem] text-muted-foreground">
                {feed.model}
              </span>

              <Tag
                tone={
                  feed.tone === "accent"
                    ? "accent"
                    : feed.tone === "danger"
                    ? "danger"
                    : "primary"
                }
              >
                {feed.tone === "accent"
                  ? "review"
                  : "nominal"}
              </Tag>
            </div>
          </figure>
        );
      })}
    </div>
  );
}

