"use client";
import { useEffect, useRef } from "react";
import { useCADStore } from "@/store/cadStore";
import type { WSEvent } from "@/lib/types";

const AGENT_ICONS: Record<string, string> = {
  supervisor: "🧠", design_agent: "✏️", cad_executor: "⚙️",
  geometry_validator: "✅", dfm_agent: "🔧", engineering_agent: "📐",
  cost_agent: "💰", safety_agent: "🛡️", alternatives_agent: "🔀",
  cam_agent: "🏭", doc_agent: "📄",
};

function AgentCard({ event }: { event: WSEvent }) {
  const isStart = event.type === "pipeline_started";
  const isEnd = event.type === "pipeline_complete" || event.type === "pipeline_error";
  const isUpdate = event.type === "agent_update";
  const confidence = event.confidence ?? 0;

  if (isStart) {
    return (
      <div className="animate-slide-up" style={{ padding: "8px 10px", borderRadius: 8, background: "var(--bg-elevated)", border: "1px solid var(--border)", fontSize: 12, color: "var(--cyan)" }}>
        🚀 {event.message}
      </div>
    );
  }

  if (isEnd) {
    const ok = event.type === "pipeline_complete" && event.geometry_valid;
    return (
      <div className="animate-slide-up" style={{
        padding: "10px 12px", borderRadius: 8, fontSize: 12,
        background: ok ? "rgba(34,197,94,0.08)" : "rgba(239,68,68,0.08)",
        border: `1px solid ${ok ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)"}`,
        color: ok ? "var(--success)" : "var(--error)",
      }}>
        {ok ? "✅" : "❌"} {event.message || event.error}
      </div>
    );
  }

  if (!isUpdate) return null;

  return (
    <div className="animate-slide-up" style={{
      padding: "8px 10px", borderRadius: 8, background: "var(--bg-elevated)",
      border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 5,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ fontSize: 14 }}>{AGENT_ICONS[event.agent ?? ""] ?? "🤖"}</span>
        <span style={{ fontWeight: 600, fontSize: 12, color: "var(--text-primary)" }}>{event.display_name}</span>
        <div style={{ flex: 1 }} />
        <span className={`badge badge-${event.status === "done" ? "success" : event.status === "error" ? "error" : "info"}`} style={{ fontSize: 9 }}>
          {event.status}
        </span>
        <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
          {confidence.toFixed(0)}%
        </span>
      </div>
      {confidence > 0 && (
        <div className="confidence-bar"><div className="confidence-fill" style={{ width: `${confidence}%` }} /></div>
      )}
      {event.payload && Object.keys(event.payload).length > 0 && (
        <div style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "JetBrains Mono, monospace" }}>
          {JSON.stringify(event.payload).slice(0, 120)}
        </div>
      )}
    </div>
  );
}

export default function AgentLog() {
  const { agentEvents, isGenerating } = useCADStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [agentEvents]);

  return (
    <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 6, height: "100%", overflowY: "auto" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 1 }}>
          Agent Activity
        </span>
        {isGenerating && (
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--cyan)" }} className="animate-pulse-ring" />
        )}
      </div>

      {agentEvents.length === 0 ? (
        <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8, color: "var(--text-muted)", fontSize: 12 }}>
          <span style={{ fontSize: 28 }}>🤖</span>
          Agent activity will appear here when you generate a design
        </div>
      ) : (
        agentEvents.map((e, i) => <AgentCard key={i} event={e} />)
      )}
      <div ref={bottomRef} />
    </div>
  );
}
