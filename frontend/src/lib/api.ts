// FastAPI client

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json();
}

// Sessions
export const api = {
  createSession: (name = "Untitled Session") =>
    request("/api/sessions/", { method: "POST", body: JSON.stringify({ name }) }),

  listSessions: () => request("/api/sessions/"),

  deleteSession: (id: string) =>
    request(`/api/sessions/${id}`, { method: "DELETE" }),

  listDesigns: (sessionId: string) =>
    request(`/api/sessions/${sessionId}/designs`),

  // Design
  generateDesign: (sessionId: string, prompt: string) =>
    request("/api/design/generate", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, prompt }),
    }),

  getDesign: (designId: string) => request(`/api/design/${designId}`),

  getDesignLogs: (designId: string) => request(`/api/design/${designId}/logs`),

  getTaskStatus: (taskId: string) => request(`/api/design/task/${taskId}/status`),

  // Exports
  getExports: (designId: string) => request(`/api/export/${designId}/files`),

  getDownloadUrl: (designId: string, format: string) =>
    `${API_URL}/api/export/${designId}/download/${format}`,

  // Health
  health: () => request("/api/health"),
};
