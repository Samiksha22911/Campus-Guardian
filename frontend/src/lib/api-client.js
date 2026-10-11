// Set VITE_API_URL at build time (see .env.example). A trailing slash is tolerated.
const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const TOKEN_KEY = "campus-guardian-token";
const STUDENT_TOKEN_KEY = "campus-guardian-student-token";

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

// The student portal (self-registration + status check) is a completely
// separate login from the staff dashboard, so it gets its own token slot -
// a student browsing the portal should never accidentally be treated as
// (or overwrite the session of) a logged-in admin/security user, or vice versa.
export function getStudentToken() {
  try {
    return localStorage.getItem(STUDENT_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setStudentToken(token) {
  try {
    if (token) localStorage.setItem(STUDENT_TOKEN_KEY, token);
    else localStorage.removeItem(STUDENT_TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

export function imageUrl(path) {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  return `${API_URL}${path}`;
}

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body, isForm = false, auth = true } = {}) {
  const headers = {};
  if (!isForm) headers["Content-Type"] = "application/json";

  if (auth === "student") {
    const token = getStudentToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  } else if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let res;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
    });
  } catch (err) {
    throw new ApiError(
      "Could not reach the Campus Guardian server. Is the backend running?",
      0
    );
  }

  if (res.status === 204) return null;

  const contentType = res.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await res.json() : await res.text();

  if (!res.ok) {
    const message =
      (data && typeof data === "object" && (data.detail?.msg || data.detail)) ||
      `Request failed (${res.status})`;
    throw new ApiError(typeof message === "string" ? message : "Request failed", res.status);
  }

  return data;
}

export const api = {
  // -------- auth --------
  login: (email, password) => request("/api/auth/login", { method: "POST", body: { email, password }, auth: false }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  me: () => request("/api/auth/me"),

  // -------- students --------
  getStudents: (params = {}) => request(`/api/students${qs(params)}`),
  getStudent: (id) => request(`/api/students/${id}`),
  createStudent: (data) => request("/api/students", { method: "POST", body: data }),
  updateStudent: (id, data) => request(`/api/students/${id}`, { method: "PUT", body: data }),
  deactivateStudent: (id) => request(`/api/students/${id}`, { method: "DELETE" }),
  uploadStudentPhoto: (id, file) => {
    const form = new FormData();
    form.append("file", file);
    return request(`/api/students/${id}/photo`, { method: "POST", body: form, isForm: true });
  },

  // -------- student self-registration approval (staff) --------
  getPendingStudents: () => request("/api/students/pending"),
  approveStudent: (id) => request(`/api/students/${id}/approve`, { method: "POST" }),
  rejectStudent: (id, reason) =>
    request(`/api/students/${id}/reject`, { method: "POST", body: { reason: reason || null } }),

  // -------- student portal (public self-registration + student login) --------
  registerStudent: (formData) =>
    request("/api/student-portal/register", { method: "POST", body: formData, isForm: true, auth: false }),
  studentLogin: (student_id, password) =>
    request("/api/student-portal/login", { method: "POST", body: { student_id, password }, auth: false }),
  studentMe: () => request("/api/student-portal/me", { auth: "student" }),

  // -------- vehicles --------
  getVehicles: (params = {}) => request(`/api/vehicles${qs(params)}`),
  getVehicle: (id) => request(`/api/vehicles/${id}`),
  createVehicle: (data) => request("/api/vehicles", { method: "POST", body: data }),
  updateVehicle: (id, data) => request(`/api/vehicles/${id}`, { method: "PUT", body: data }),
  deactivateVehicle: (id) => request(`/api/vehicles/${id}`, { method: "DELETE" }),
  uploadVehiclePhoto: (id, file) => {
    const form = new FormData();
    form.append("file", file);
    return request(`/api/vehicles/${id}/photo`, { method: "POST", body: form, isForm: true });
  },

  // -------- verification --------
  processVerification: (file, { gateId, requireFace, scenario } = {}) => {
    const form = new FormData();
    form.append("image", file);
    form.append("gate_id", String(gateId));
    if (requireFace !== undefined) form.append("require_face", String(requireFace));
    if (scenario) form.append("scenario", scenario);
    return request("/api/verification/process", { method: "POST", body: form, isForm: true });
  },
  getVerificationHistory: (limit = 100) => request(`/api/verification/history/list?limit=${limit}`),

  // -------- entries --------
  getEntries: (params = {}) => request(`/api/entries${qs(params)}`),
  getRecentEntries: () => request("/api/entries/recent"),
  manualDecision: (entryId, status, reason) =>
    request(`/api/entries/${entryId}/manual-decision`, { method: "POST", body: { status, reason } }),

  // -------- alerts --------
  getAlerts: (params = {}) => request(`/api/alerts${qs(params)}`),
  setAlertStatus: (id, status) => request(`/api/alerts/${id}/status`, { method: "PATCH", body: { status } }),

  // -------- dashboard --------
  getDashboardStats: () => request("/api/dashboard/stats"),
  getRecentActivity: (limit = 10) => request(`/api/dashboard/recent-activity?limit=${limit}`),

  // -------- analytics / reports --------
  getAnalytics: () => request("/api/analytics"),
  getReportStatistics: (params = {}) => request(`/api/reports/statistics${qs(params)}`),
  getReportEntriesCsvUrl: (params = {}) => `${API_URL}/api/reports/entries${qs({ ...params, format: "csv" })}`,

  // -------- gates --------
  getGates: () => request("/api/gates"),

  // -------- users (admin) --------
  getUsers: () => request("/api/users"),
  createUser: (data) => request("/api/users", { method: "POST", body: data }),
  deactivateUser: (id) => request(`/api/users/${id}/deactivate`, { method: "PATCH" }),

  // -------- profile (any logged-in user) --------
  updateProfile: (data) => request("/api/users/me", { method: "PATCH", body: data }),

  // -------- audit logs (admin) --------
  getAuditLogs: (limit = 200) => request(`/api/audit-logs?limit=${limit}`),
};

function qs(params) {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  if (!entries.length) return "";
  return `?${new URLSearchParams(entries).toString()}`;
}

export { ApiError, API_URL };
