"use client";
import { useState } from "react";
import { useCADStore } from "@/store/cadStore";
import { useCADSession } from "@/hooks/useCADSession";
import { api } from "@/lib/api";
import type { Session, Design } from "@/lib/types";
import { Plus, Folder, Trash2, CheckCircle2 } from "lucide-react";

export default function SessionsPanel() {
  const { sessions, activeSession, setActiveSession, setActiveDesign, setGlbUrl, setSessions } = useCADStore();
  const { createSession, loadSessions } = useCADSession();
  const [newSessionName, setNewSessionName] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const handleSelectSession = async (session: Session) => {
    setActiveSession(session);
    // Load latest design for selected session
    try {
      const designs = (await api.listDesigns(session.id)) as Design[];
      if (Array.isArray(designs) && designs.length > 0) {
        const latest = designs[0];
        setActiveDesign(latest);
        if (latest.status === "COMPLETE" && latest.geometry_valid) {
          const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
          setGlbUrl(`${API_URL}/api/export/${latest.id}/download/glb?t=${Date.now()}`);
        } else {
          setGlbUrl(null);
        }
      } else {
        setActiveDesign(null);
        setGlbUrl(null);
      }
    } catch {
      setActiveDesign(null);
      setGlbUrl(null);
    }
  };

  const handleCreate = async () => {
    const name = newSessionName.trim() || `Session ${sessions.length + 1}`;
    setIsCreating(true);
    try {
      const s = await createSession(name);
      if (s) {
        setActiveSession(s);
        setActiveDesign(null);
        setGlbUrl(null);
        setNewSessionName("");
      }
    } finally {
      setIsCreating(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await api.deleteSession(id);
      const remaining = sessions.filter((s) => s.id !== id);
      setSessions(remaining);
      if (activeSession?.id === id) {
        if (remaining.length > 0) {
          handleSelectSession(remaining[0]);
        } else {
          setActiveSession(null);
          setActiveDesign(null);
          setGlbUrl(null);
        }
      }
    } catch {
      // ignore
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, height: "100%" }}>
      {/* Create New Session Bar */}
      <div style={{ display: "flex", gap: 6 }}>
        <input
          type="text"
          placeholder="New session name..."
          value={newSessionName}
          onChange={(e) => setNewSessionName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          style={{
            flex: 1,
            background: "var(--bg-base)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: "5px 10px",
            fontSize: 12,
            color: "var(--text-primary)",
            outline: "none",
          }}
        />
        <button
          className="btn btn-primary"
          onClick={handleCreate}
          disabled={isCreating}
          style={{ fontSize: 11, padding: "5px 10px", display: "flex", alignItems: "center", gap: 4 }}
        >
          <Plus size={13} />
          <span>New</span>
        </button>
      </div>

      {/* Sessions List */}
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 4 }}>
        {sessions.map((s) => {
          const isActive = activeSession?.id === s.id;
          return (
            <div
              key={s.id}
              onClick={() => handleSelectSession(s)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "8px 10px",
                borderRadius: 6,
                background: isActive ? "var(--bg-elevated)" : "transparent",
                border: isActive ? "1px solid var(--border-active, var(--cyan))" : "1px solid transparent",
                cursor: "pointer",
                transition: "all 0.15s",
              }}
              onMouseEnter={(e) => {
                if (!isActive) e.currentTarget.style.background = "var(--bg-base)";
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.background = "transparent";
              }}
            >
              <Folder size={14} color={isActive ? "var(--cyan)" : "var(--text-muted)"} />
              <div style={{ flex: 1, overflow: "hidden" }}>
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: isActive ? 600 : 400,
                    color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {s.name}
                </div>
                <div style={{ fontSize: 10, color: "var(--text-muted)" }}>
                  {new Date(s.created_at).toLocaleDateString()}
                </div>
              </div>
              {isActive && <CheckCircle2 size={13} color="var(--cyan)" />}
              {sessions.length > 1 && (
                <button
                  onClick={(e) => handleDelete(e, s.id)}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    padding: 2,
                    opacity: 0.6,
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = "var(--error)")}
                  onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-muted)")}
                  title="Delete session"
                >
                  <Trash2 size={12} />
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
