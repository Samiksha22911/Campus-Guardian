"""The ONE results format used by every mode (see ../demo-data/results.schema.json).

Pure Python (no cv2 / torch) so the converter, the validator and the backend
can all import it. Readings are grouped into one "event" per vehicle pass.
"""

import difflib
from datetime import datetime, timezone

SCHEMA_VERSION = "1.0"
DB_STATUSES = {"REGISTERED", "UNREGISTERED", "BLOCKLISTED", "INACTIVE", "PENDING",
               "LOW_CONFIDENCE", "NO_PLATE", "NOT_CHECKED"}
DECISIONS = {"ALLOWED", "DENIED", "REVIEW"}


def clean_plate(raw):
    return "".join(ch for ch in (raw or "").upper() if ch.isalnum())


def iou(a, b):
    """a, b = (x, y, w, h) in the same units."""
    ax2, ay2, bx2, by2 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    iw = max(0.0, min(ax2, bx2) - max(a[0], b[0]))
    ih = max(0.0, min(ay2, by2) - max(a[1], b[1]))
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def group_readings(readings, max_gap_s=1.5, min_hits=2, text_sim=0.7, box_iou=0.25):
    """readings: dicts with t, text (or None), conf, det_conf, box=(x,y,w,h) NORMALISED 0-1.
    Returns events (without db fields) - one per tracked plate."""
    tracks = []
    for r in sorted(readings, key=lambda r: r["t"]):
        best, best_score = None, 0.0
        for tr in tracks:
            if r["t"] - tr["last_t"] > max_gap_s:
                continue
            sim = 0.0
            if r["text"] and tr["top_text"]:
                sim = difflib.SequenceMatcher(None, r["text"], tr["top_text"]).ratio()
            ov = iou(r["box"], tr["last_box"])
            score = max(sim if sim >= text_sim else 0.0, ov if ov >= box_iou else 0.0)
            if score > best_score:
                best, best_score = tr, score
        if best is None:
            best = {"readings": [], "last_t": r["t"], "last_box": r["box"], "top_text": None}
            tracks.append(best)
        best["readings"].append(r)
        best["last_t"], best["last_box"] = r["t"], r["box"]
        votes = {}
        for x in best["readings"]:
            if x["text"]:
                votes[x["text"]] = votes.get(x["text"], 0.0) + x["conf"]
        best["top_text"] = max(votes, key=votes.get) if votes else None

    events = []
    for tr in tracks:
        rs = tr["readings"]
        text = tr["top_text"]
        if text:
            same = [x for x in rs if x["text"] and len(x["text"]) == len(text)]
            # character-by-character weighted vote: one bad character in one frame cannot win
            text = "".join(
                max({c: sum(x["conf"] for x in same if x["text"][i] == c) for c in {x["text"][i] for x in same}}.items(),
                    key=lambda kv: kv[1])[0]
                for i in range(len(text))
            )
        readable = [x for x in rs if text and x["text"] and len(x["text"]) == len(text)] if text else []
        if text and len(rs) < min_hits:
            continue
        if not text and len(rs) < min_hits + 1:
            continue  # a few unreadable boxes are usually noise
        best = max(readable or rs, key=lambda x: (x["conf"], x["det_conf"]))
        conf = sum(x["conf"] for x in readable) / len(readable) if readable else 0.0
        events.append({
            "timestamp": round(best["t"], 3),
            "ts_start": round(rs[0]["t"], 3),
            "ts_end": round(rs[-1]["t"], 3),
            "plate_text": text,
            "plate_confidence": round(conf, 4),
            "detector_confidence": round(max(x["det_conf"] for x in rs), 4),
            "face_match_name": None,
            "face_score": None,
            "bbox": _box(best["box"]),
            "track": [{"t": round(x["t"], 3), **_box(x["box"])} for x in rs],
        })
    events.sort(key=lambda e: e["timestamp"])
    return events


def _box(b):
    return {"x": round(b[0], 4), "y": round(b[1], 4), "w": round(b[2], 4), "h": round(b[3], 4)}


def apply_lookup(events, lookup=None):
    """lookup(plate_text, confidence) -> {db_status, decision, owner_name}."""
    for i, ev in enumerate(events, 1):
        ev["id"] = i
        info = lookup(ev["plate_text"], ev["plate_confidence"]) if lookup else None
        info = info or {"db_status": "NOT_CHECKED", "decision": "REVIEW", "owner_name": None}
        ev["db_status"] = info["db_status"]
        ev["decision"] = info["decision"]
        ev["owner_name"] = info.get("owner_name")
    return events


def build_results(events, *, source_video, duration_s, fps, width, height, models, stride_s=None,
                  generated_by="real-pipeline", video_src=None):
    return {
        "schema_version": SCHEMA_VERSION,
        "meta": {
            "generated_by": generated_by,   # "real-pipeline" | "sample"
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_video": source_video,
            "models": models,
            "stride_s": stride_s,
        },
        "video": {"src": video_src, "duration_s": round(duration_s, 3), "fps": round(fps, 3),
                  "width": width, "height": height},
        "events": events,
    }


def validate_results(d):
    """Returns a list of problems (empty list = valid). No external deps."""
    errs = []
    if d.get("schema_version") != SCHEMA_VERSION:
        errs.append(f"schema_version must be {SCHEMA_VERSION!r}")
    for k in ("meta", "video", "events"):
        if k not in d:
            errs.append(f"missing top-level key {k!r}")
    if errs:
        return errs
    if d["meta"].get("generated_by") not in ("real-pipeline", "sample"):
        errs.append("meta.generated_by must be 'real-pipeline' or 'sample'")
    for i, e in enumerate(d["events"]):
        p = f"events[{i}]"
        for k in ("id", "timestamp", "plate_text", "plate_confidence", "face_match_name", "face_score",
                  "db_status", "decision", "bbox"):
            if k not in e:
                errs.append(f"{p}: missing {k!r}")
        if e.get("db_status") not in DB_STATUSES:
            errs.append(f"{p}: bad db_status {e.get('db_status')!r}")
        if e.get("decision") not in DECISIONS:
            errs.append(f"{p}: bad decision {e.get('decision')!r}")
        b = e.get("bbox") or {}
        if not all(isinstance(b.get(k), (int, float)) and 0 <= b[k] <= 1 for k in ("x", "y", "w", "h")):
            errs.append(f"{p}: bbox must have x,y,w,h as 0-1 fractions of the frame")
        if not isinstance(e.get("plate_confidence"), (int, float)) or not 0 <= e["plate_confidence"] <= 1:
            errs.append(f"{p}: plate_confidence must be 0-1")
    return errs
