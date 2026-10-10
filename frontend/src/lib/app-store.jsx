import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import { toast } from "sonner";

import { api, getToken, setToken } from "./api-client";
import { GATES, gateIdFromLabel, gateLabel, setCampusData } from "./campus-data";

const AppCtx = createContext(null);

/* ---------- Shape adapters ----------
 * Transform backend API responses into the exact object shapes the
 * existing UI components already expect, so pages built against the old
 * mock data keep working unchanged against the real database.
 */

function mapStudent(s) {
  return {
    id: s.student_id,
    dbId: s.id,
    name: s.name,
    department: s.department,
    course: s.course,
    year: s.year,
    email: s.email ?? "",
    phone: s.phone ?? "",
    photo: s.profile_image ?? null,
    enrollment: s.status === "active" ? "registered" : "inactive",
    account: s.status === "active" ? "active" : "suspended",
    faceEnrolled: !!s.face_enrolled,
    consentGiven: !!s.biometric_consent,
    consentDate: s.created_at ? s.created_at.slice(0, 10) : "",
  };
}

function mapVehicle(v, studentCodeByDbId) {
  return {
    id: `VEH-${v.id}`,
    dbId: v.id,
    plate: v.registration_number,
    type: v.vehicle_type,
    make: v.make,
    model: v.model,
    color: v.color,
    photo: v.vehicle_image ?? null,
    ownerId: studentCodeByDbId.get(v.owner_student_id) ?? null,
    ownerDbId: v.owner_student_id,
    status: v.status,
    blocklisted: !!v.is_blocklisted,
    blockReason: v.block_reason ?? undefined,
  };
}

function mapEntry(e, studentCodeByDbId, entryIdsWithAlert) {
  return {
    id: e.id,
    ts: new Date(e.entry_time).getTime(),
    plate: e.detected_plate ?? "UNREADABLE",
    studentId: e.student_id ? studentCodeByDbId.get(e.student_id) ?? null : null,
    vehicleType: e.detected_vehicle_type ?? "Unknown",
    gate: gateLabel(e.gate_id),
    status: e.status,
    faceMatch: e.face_match === "match" ? "match" : e.face_match === "mismatch" ? "mismatch" : "none",
    plateConfidence: Math.round((e.plate_confidence ?? 0) * 100),
    faceConfidence: Math.round((e.face_confidence ?? 0) * 100),
    reason: e.rejection_reason,
    capturedImage: e.captured_image,
    alertId: entryIdsWithAlert.get(e.id) ?? null,
    modelVersion: "mock-ai-v1",
  };
}

function mapAlert(a, entryById) {
  const entry = a.entry_id ? entryById.get(a.entry_id) : null;
  return {
    id: a.id,
    entryId: a.entry_id,
    type: a.type,
    severity: a.severity,
    status: a.status,
    detail: a.detail,
    ts: new Date(a.created_at).getTime(),
    plate: entry?.plate ?? "—",
    studentId: entry?.studentId ?? null,
    gate: entry?.gate ?? "—",
  };
}

const ROLE_FROM_BACKEND = {
  security_officer: "guard",
  admin: "admin",
};

export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [hydrated, setHydrated] = useState(false);
  const [loadingData, setLoadingData] = useState(false);

  const [aiOnline, setAiOnline] = useState(true);
  const [gate, setGate] = useState(GATES[0]?.label);

  const [students, setStudents] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [entries, setEntries] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [current, setCurrent] = useState(null);
  const [step, setStep] = useState(-1);
  const [queue] = useState([]);

  const [thresholds, setThresholds] = useState({ ocr: 55, face: 60 });
  const [users, setUsers] = useState([]);

  /* ---------- Restore session ---------- */

  useEffect(() => {
    const token = getToken();

    if (!token) {
      setHydrated(true);
      return;
    }

    api
      .me()
      .then((me) => {
        setUser({ ...me, role: ROLE_FROM_BACKEND[me.role] ?? me.role, backendRole: me.role });
      })
      .catch(() => {
        setToken(null);
      })
      .finally(() => setHydrated(true));
  }, []);

  /* ---------- Load all campus data whenever we have a logged-in user ---------- */

  const refreshAll = useCallback(async () => {
    setLoadingData(true);
    try {
      const [studentsRaw, vehiclesRaw, entriesRaw, alertsRaw, gatesRaw] = await Promise.all([
        api.getStudents(),
        api.getVehicles(),
        api.getEntries(),
        api.getAlerts(),
        api.getGates().catch(() => []),
      ]);

      const gatesList = gatesRaw.length
        ? gatesRaw.map((g) => ({ id: g.id, label: g.name }))
        : GATES;

      setCampusData({ gates: gatesList });

      const studentCodeByDbId = new Map(studentsRaw.map((s) => [s.id, s.student_id]));

      const mappedStudents = studentsRaw.map(mapStudent);
      const mappedVehicles = vehiclesRaw.map((v) => mapVehicle(v, studentCodeByDbId));

      setCampusData({ students: mappedStudents, vehicles: mappedVehicles });
      setStudents(mappedStudents);
      setVehicles(mappedVehicles);

      const entryById = new Map();
      const entryIdsWithAlert = new Map();
      for (const a of alertsRaw) {
        if (a.entry_id) entryIdsWithAlert.set(a.entry_id, a.id);
      }

      const mappedEntries = entriesRaw.map((e) => mapEntry(e, studentCodeByDbId, entryIdsWithAlert));
      mappedEntries.forEach((e) => entryById.set(e.id, e));

      setEntries(mappedEntries);
      setCurrent(mappedEntries[0] ?? null);

      setAlerts(alertsRaw.map((a) => mapAlert(a, entryById)));

      if (gatesList[0]) setGate((g) => g ?? gatesList[0].label);
    } catch (err) {
      toast.error("Could not load campus data", { description: err.message });
    } finally {
      setLoadingData(false);
    }
  }, []);

  useEffect(() => {
    if (user) refreshAll();
  }, [user, refreshAll]);

  /* ---------- Login / Logout ---------- */

  const login = useCallback(async (email, password) => {
    try {
      const res = await api.login(email, password);
      setToken(res.access_token);
      setUser({
        ...res.user,
        role: ROLE_FROM_BACKEND[res.user.role] ?? res.user.role,
        backendRole: res.user.role,
      });
      return { ok: true };
    } catch (err) {
      return { ok: false, error: err.message || "Invalid credentials. Check your email and password." };
    }
  }, []);

  const logout = useCallback(() => {
    api.logout().catch(() => {});
    setToken(null);
    setUser(null);
    setStudents([]);
    setVehicles([]);
    setEntries([]);
    setAlerts([]);
    setCurrent(null);
  }, []);

  /* ---------- Verification pipeline (real backend call) ---------- */

  const runVerification = useCallback(
    async (file, options = {}) => {
      const gateId = gateIdFromLabel(gate);
      setStep(0);

      const anim = [1, 2, 3, 4].map((s, i) => setTimeout(() => setStep(s), (i + 1) * 350));

      try {
        const result = await api.processVerification(file, { gateId, ...options });
        setStep(5);

        // Pull the freshly created entry from the entries endpoint so it
        // has the exact same shape as the rest of the history.
        const [freshEntries, freshAlerts] = await Promise.all([api.getEntries(), api.getAlerts()]);

        const studentCodeByDbId = new Map(students.map((s) => [s.dbId, s.id]));
        const entryIdsWithAlert = new Map();
        for (const a of freshAlerts) if (a.entry_id) entryIdsWithAlert.set(a.entry_id, a.id);

        const mappedEntries = freshEntries.map((e) => mapEntry(e, studentCodeByDbId, entryIdsWithAlert));
        const entryById = new Map(mappedEntries.map((e) => [e.id, e]));

        setEntries(mappedEntries);
        const newCurrent = entryById.get(result.entry_id) ?? mappedEntries[0] ?? null;
        setCurrent(newCurrent);
        setAlerts(freshAlerts.map((a) => mapAlert(a, entryById)));

        if (result.verification_status !== "GRANTED") {
          const toastType = ["UNKNOWN_VEHICLE", "FACE_MISMATCH"].includes(result.verification_status)
            ? "error"
            : "warning";
          toast[toastType](`${result.verification_status.replace(/_/g, " ")}`, {
            description: result.rejection_reason ?? `${result.plate_number ?? "Unknown plate"} · ${gate}`,
          });
        } else {
          toast.success("Entry granted", { description: `${result.plate_number} · ${gate}` });
        }

        return { ok: true, result };
      } catch (err) {
        setStep(-1);
        toast.error("Verification failed", { description: err.message });
        return { ok: false, error: err.message };
      } finally {
        anim.forEach(clearTimeout);
      }
    },
    [gate, students]
  );

  /* ---------- Alert status ---------- */

  const setAlertStatus = useCallback(async (id, status) => {
    setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, status } : a)));
    try {
      await api.setAlertStatus(id, status);
    } catch (err) {
      toast.error("Could not update alert", { description: err.message });
    }
  }, []);

  /* ---------- Manual decision ---------- */

  const manualDecision = useCallback(
    async (status, reason) => {
      if (!current) return;

      try {
        const updated = await api.manualDecision(current.id, status, reason);
        const studentCodeByDbId = new Map(students.map((s) => [s.dbId, s.id]));
        const mapped = mapEntry(updated, studentCodeByDbId, new Map());

        setCurrent((c) => (c ? { ...c, status: "manual", reason: mapped.reason } : c));
        setEntries((prev) => prev.map((e) => (e.id === updated.id ? { ...e, status: "manual", reason: mapped.reason } : e)));

        toast.success(`Manual ${status} recorded`, { description: reason });
      } catch (err) {
        toast.error("Could not save manual decision", { description: err.message });
      }
    },
    [current, students]
  );

  /* ---------- Students CRUD ---------- */

  const createStudent = useCallback(async (data) => {
    const created = await api.createStudent(data);
    await refreshAll();
    return created;
  }, [refreshAll]);

  const updateStudent = useCallback(async (dbId, data) => {
    const updated = await api.updateStudent(dbId, data);
    await refreshAll();
    return updated;
  }, [refreshAll]);

  const deactivateStudent = useCallback(async (dbId) => {
    await api.deactivateStudent(dbId);
    await refreshAll();
  }, [refreshAll]);

  const uploadStudentPhoto = useCallback(async (dbId, file) => {
    const updated = await api.uploadStudentPhoto(dbId, file);
    await refreshAll();
    return updated;
  }, [refreshAll]);

  /* ---------- Vehicles CRUD ---------- */

  const createVehicle = useCallback(async (data) => {
    const created = await api.createVehicle(data);
    await refreshAll();
    return created;
  }, [refreshAll]);

  const updateVehicle = useCallback(async (dbId, data) => {
    const updated = await api.updateVehicle(dbId, data);
    await refreshAll();
    return updated;
  }, [refreshAll]);

  const deactivateVehicle = useCallback(async (dbId) => {
    await api.deactivateVehicle(dbId);
    await refreshAll();
  }, [refreshAll]);

  const uploadVehiclePhoto = useCallback(async (dbId, file) => {
    const updated = await api.uploadVehiclePhoto(dbId, file);
    await refreshAll();
    return updated;
  }, [refreshAll]);

  const loadUsers = useCallback(async () => {
    try {
      const list = await api.getUsers();
      setUsers(
        list.map((u) => ({
          id: u.id,
          name: u.name,
          email: u.email,
          role: ROLE_FROM_BACKEND[u.role] ?? u.role,
          isActive: u.is_active,
        }))
      );
    } catch (err) {
      toast.error("Could not load operator accounts", { description: err.message });
    }
  }, []);

  const createUser = useCallback(async (data) => {
    const created = await api.createUser(data);
    await loadUsers();
    return created;
  }, [loadUsers]);

  const updateProfile = useCallback(async (data) => {
    const updated = await api.updateProfile(data);
    setUser((prev) => (prev ? { ...prev, name: updated.name } : prev));
    return updated;
  }, []);

  /* ---------- Context value ---------- */

  const value = {
    user,
    hydrated,
    loadingData,

    login,
    logout,
    refreshAll,

    aiOnline,
    setAiOnline,

    gate,
    setGate,

    students,
    vehicles,
    entries,
    alerts,

    current,
    step,
    queue,

    runVerification,
    setAlertStatus,
    manualDecision,

    createStudent,
    updateStudent,
    deactivateStudent,
    uploadStudentPhoto,

    createVehicle,
    updateVehicle,
    deactivateVehicle,
    uploadVehiclePhoto,

    thresholds,
    setThresholds,

    users,
    loadUsers,
    createUser,
    updateProfile,
  };

  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>;
}

export function useApp() {
  const context = useContext(AppCtx);

  if (!context) {
    throw new Error("useApp must be used within AppProvider");
  }

  return context;
}

export const ROLE_LABEL = {
  guard: "Security Officer",
  admin: "Admin",
};

export const can = (role, page) => {
  if (!role) return false;

  const matrix = {
    dashboard: ["guard", "admin"],
    live: ["guard", "admin"],
    students: ["guard", "admin"],
    vehicles: ["guard", "admin"],
    enrollment: ["admin"],
    logs: ["guard", "admin"],
    alerts: ["guard", "admin"],
    analytics: ["admin"],
    settings: ["admin"],
    profile: ["guard", "admin"],
    audit: ["admin"],
    edit: ["admin"],
    export: ["admin"],
  };

  return (matrix[page] ?? []).includes(role);
};
