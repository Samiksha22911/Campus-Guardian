/* ---------- Live campus data cache ----------
 * This used to be a static, randomly-generated mock dataset. It is now a
 * thin cache populated from the real Campus Guardian backend by
 * `app-store.jsx` (see `setCampusData`). Keeping the same exported names
 * (`students`, `vehicles`, `GATES`, `studentById`, ...) means the pages
 * that already consume them don't need to change - only the source of
 * the data changed, from `Math.random()` to the MySQL database.
 */

export let GATES = [
  { id: 1, label: "Main Gate" },
  { id: 2, label: "North Gate" },
  { id: 3, label: "Hostel Gate" },
];

export let students = [];
export let vehicles = [];

/** Called by app-store.jsx after it fetches real data from the API. */
export function setCampusData({ students: s, vehicles: v, gates: g } = {}) {
  if (s) students = s;
  if (v) vehicles = v;
  if (g && g.length) GATES = g;
}

export const studentById = (id) => students.find((s) => s.id === id) ?? null;

export const vehicleByPlate = (plate) =>
  vehicles.find(
    (v) => v.plate.replace(/\s+/g, "").toUpperCase() === String(plate).replace(/\s+/g, "").toUpperCase()
  ) ?? null;

export const vehiclesForStudent = (studentId) => vehicles.filter((v) => v.ownerId === studentId);

export const gateLabel = (gateId) => GATES.find((g) => g.id === gateId)?.label ?? `Gate ${gateId}`;

export const gateIdFromLabel = (label) => GATES.find((g) => g.label === label)?.id ?? GATES[0]?.id;

/* ---------- Date Helpers ---------- */

export const fmtTime = (timestamp) => {
  return new Date(timestamp).toLocaleTimeString("en-GB", {
    hour12: false,
  });
};

export const fmtDateTime = (timestamp) => {
  return new Date(timestamp).toLocaleString("en-GB", {
    hour12: false,
  });
};

export const fmtDate = (timestamp) => {
  return new Date(timestamp).toLocaleDateString("en-GB");
};
