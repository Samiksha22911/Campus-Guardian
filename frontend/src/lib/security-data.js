export const FIRST = [
  "Aarav",
  "Diya",
  "Rohan",
  "Meera",
  "Kabir",
  "Ananya",
  "Ishaan",
  "Sanya",
  "Vikram",
  "Neha",
  "Arjun",
  "Priya",
];

export const LAST = [
  "Sharma",
  "Iyer",
  "Nair",
  "Verma",
  "Rao",
  "Khan",
  "Bose",
  "Patel",
  "Menon",
];

export const GATES_P = [
  "Gate 1 — Main",
  "Gate 3 — Hostel",
  "Lab Block A",
  "Library Turnstile",
];

export const GATES_V = [
  "Vehicle Gate A",
  "Vehicle Gate B",
  "Service Gate",
];

export const ZONES = [
  "North Perimeter",
  "Server Room Corridor",
  "Parking Lot C",
  "Chem Lab Wing",
  "Admin Block Roof",
  "East Fence Line",
];

let seq = 1;

const uid = (p) =>
  `${p}-${(seq++).toString().padStart(4, "0")}`;

const pick = (array) =>
  array[Math.floor(Math.random() * array.length)];

const rnd = (min, max) =>
  min + Math.random() * (max - min);

export const clockAt = (offsetSec) => {
  const d = new Date(Date.now() - offsetSec * 1000);

  return d.toLocaleTimeString("en-GB", {
    hour12: false,
  });
};

export function makeFaceEvent(offsetSec = 0) {
  const roll = Math.random();

  const unknown = roll > 0.9;
  const review = !unknown && roll > 0.82;

  const role = unknown
    ? "Unknown"
    : pick([
        "Student",
        "Student",
        "Student",
        "Faculty",
        "Staff",
        "Visitor",
      ]);

  return {
    id: uid("F"),

    name: unknown
      ? "Unidentified subject"
      : `${pick(FIRST)} ${pick(LAST)}`,

    role,

    idNo: unknown
      ? "—"
      : `${role.slice(0, 2).toUpperCase()}-${Math.floor(
          rnd(10000, 99999)
        )}`,

    gate: pick(GATES_P),

    confidence: unknown
      ? rnd(41, 62)
      : review
        ? rnd(66, 78)
        : rnd(93.5, 99.6),

    verdict: unknown
      ? "denied"
      : review
        ? "review"
        : "granted",

    ts: clockAt(offsetSec),
  };
}

const PLATE_STATES = [
  "KA",
  "TN",
  "MH",
  "DL",
  "KL",
  "AP",
];

const randPlate = () =>
  `${pick(PLATE_STATES)} ${Math.floor(
    rnd(10, 99)
  )} ${String.fromCharCode(
    65 + Math.floor(rnd(0, 26))
  )}${String.fromCharCode(
    65 + Math.floor(rnd(0, 26))
  )} ${Math.floor(rnd(1000, 9999))}`;

export function makePlateEvent(offsetSec = 0) {
  const roll = Math.random();

  const blacklisted = roll > 0.94;
  const unregistered = !blacklisted && roll > 0.82;
  const visitor =
    !blacklisted &&
    !unregistered &&
    roll > 0.66;

  const category = blacklisted
    ? "Blacklisted"
    : unregistered
      ? "Unregistered"
      : visitor
        ? "Visitor"
        : "Registered";

  return {
    id: uid("V"),

    plate: randPlate(),

    owner:
      category === "Registered"
        ? `${pick(FIRST)} ${pick(LAST)}`
        : category === "Visitor"
          ? "Guest pass #" + Math.floor(rnd(100, 999))
          : "No record",

    category,

    gate: pick(GATES_V),

    direction: Math.random() > 0.45
      ? "IN"
      : "OUT",

    confidence:
      blacklisted || unregistered
        ? rnd(84, 95)
        : rnd(95, 99.4),

    verdict:
      blacklisted
        ? "denied"
        : unregistered
          ? "review"
          : "granted",

    ts: clockAt(offsetSec),
  };
}

export function makeAlert(offsetSec = 0) {
  const kind = pick([
    "Intrusion",
    "Tailgating",
    "Loitering",
    "Unattended object",
    "Crowd density",
    "Blacklisted vehicle",
    "Face mismatch",
  ]);

  const severity =
    kind === "Intrusion" ||
    kind === "Blacklisted vehicle"
      ? "critical"
      : kind === "Tailgating" ||
        kind === "Unattended object"
        ? "high"
        : "medium";

  const detail = {
    Intrusion:
      "Fence-line crossing detected outside authorised hours",

    Tailgating:
      "2 subjects passed on a single verified credential",

    Loitering:
      "Subject stationary > 6 min in restricted corridor",

    "Unattended object":
      "Bag left unattended > 4 min",

    "Crowd density":
      "Density above safe threshold (>4.2 persons/m²)",

    "Blacklisted vehicle":
      "Plate matched watchlist entry",

    "Face mismatch":
      "Face embedding did not match presented ID card",
  };

  return {
    id: uid("A"),
    kind,
    zone: pick(ZONES),
    severity,
    detail: detail[kind],
    ts: clockAt(offsetSec),
    status: "open",
  };
}

export const seedFaces = (n) =>
  Array.from(
    { length: n },
    (_, i) => makeFaceEvent(i * 37 + 12)
  );

export const seedPlates = (n) =>
  Array.from(
    { length: n },
    (_, i) => makePlateEvent(i * 71 + 25)
  );

export const seedAlerts = (n) =>
  Array.from(
    { length: n },
    (_, i) => makeAlert(i * 260 + 90)
  );

export const visitors = [
  {
    id: "VP-2041",
    name: "R. Krishnan",
    host: "Dept. of CSE",
    purpose: "Guest lecture",
    pass: "QR + Face",
    validTill: "18:00",
    state: "on-campus",
  },

  {
    id: "VP-2042",
    name: "Suhana Rai",
    host: "Admin Block",
    purpose: "Vendor demo",
    pass: "QR",
    validTill: "16:30",
    state: "on-campus",
  },

  {
    id: "VP-2043",
    name: "Deepak Menon",
    host: "Placement Cell",
    purpose: "Recruiter visit",
    pass: "QR + Plate",
    validTill: "19:00",
    state: "expected",
  },

  {
    id: "VP-2039",
    name: "Anita Gupta",
    host: "Library",
    purpose: "Audit",
    pass: "Face",
    validTill: "14:00",
    state: "checked-out",
  },
];

