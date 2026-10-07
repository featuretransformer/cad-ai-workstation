"use client";
import { useEffect, useState } from "react";
import { useCADStore } from "@/store/cadStore";
import { useCADSession } from "@/hooks/useCADSession";
import ViewerCanvas from "./ViewerCanvas";
import ChatPanel from "./ChatPanel";
import FeatureTree from "./FeatureTree";
import AgentLog from "./AgentLog";
import ExportPanel from "./ExportPanel";
import StatusBar from "./StatusBar";

export default function Workstation() {
  const { leftPanelTab, setLeftPanelTab, rightPanelTab, setRightPanelTab, activeSession } = useCADStore();
  const { loadSessions, createSession } = useCADSession();
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    loadSessions().then(async (sessions) => {
      if (sessions.length === 0) {
        // Try to create a default session — if backend is online
        const s = await createSession("Default Session");
        setBackendOnline(s !== null);
      } else {
        useCADStore.getState().setActiveSession(sessions[0]);
        setBackendOnline(true);
      }
    }).catch(() => setBackendOnline(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "var(--bg-base)", overflow: "hidden" }}>
      {/* Offline Banner */}
      {backendOnline === false && (
        <div style={{
          background: "rgba(239,68,68,0.12)", borderBottom: "1px solid rgba(239,68,68,0.25)",
          padding: "6px 16px", fontSize: 12, color: "#fca5a5",
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <span>⚠</span>
          <strong>Backend offline</strong> — Start the FastAPI server:
          <code style={{ background: "rgba(0,0,0,0.3)", padding: "1px 6px", borderRadius: 4, fontFamily: "JetBrains Mono, monospace" }}>
            cd backend &amp;&amp; source .venv/bin/activate &amp;&amp; uvicorn main:app --reload --port 8000
          </code>
        </div>
      )}
      {/* Header */}
      <header style={{ height: 52, background: "var(--bg-panel)", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", padding: "0 16px", gap: 12, flexShrink: 0, zIndex: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="var(--cyan)" strokeWidth="1.5" strokeLinejoin="round"/>
            <path d="M2 17l10 5 10-5M2 12l10 5 10-5" stroke="var(--cyan)" strokeWidth="1.5" strokeLinejoin="round"/>
          </svg>
          <span style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)", letterSpacing: "-0.3px" }}>CAD<span style={{ color: "var(--cyan)" }}>·AI</span></span>
        </div>
        <div style={{ height: 20, width: 1, background: "var(--border)" }} />
        <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
          {activeSession ? activeSession.name : "Loading..."}
        </span>
        <div style={{ flex: 1 }} />
        <div className="badge badge-info" style={{ fontSize: 10 }}>Phase 1 · Alpha</div>
      </header>

      {/* Main 3-panel layout */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* LEFT PANEL */}
        <aside style={{ width: 260, background: "var(--bg-panel)", borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", flexShrink: 0 }}>
          <div style={{ padding: "10px 10px 0" }}>
            <div className="tab-bar">
              <button className={`tab ${leftPanelTab === "feature-tree" ? "active" : ""}`} onClick={() => setLeftPanelTab("feature-tree")}>Feature Tree</button>
              <button className={`tab ${leftPanelTab === "sessions" ? "active" : ""}`} onClick={() => setLeftPanelTab("sessions")}>Sessions</button>
            </div>
          </div>
          <div style={{ flex: 1, overflow: "auto", padding: "8px" }}>
            <FeatureTree />
          </div>
        </aside>

        {/* CENTER — 3D Viewport */}
        <main style={{ flex: 1, position: "relative", overflow: "hidden" }}>
          <ViewerCanvas />
        </main>

        {/* RIGHT PANEL */}
        <aside style={{ width: 380, background: "var(--bg-panel)", borderLeft: "1px solid var(--border)", display: "flex", flexDirection: "column", flexShrink: 0 }}>
          <div style={{ padding: "10px 10px 0" }}>
            <div className="tab-bar" style={{ flexWrap: "wrap" }}>
              {(["chat", "agent-log", "reports", "export"] as const).map((t) => (
                <button key={t} className={`tab ${rightPanelTab === t ? "active" : ""}`} onClick={() => setRightPanelTab(t)}>
                  {t === "chat" ? "Chat" : t === "agent-log" ? "Agent Log" : t === "reports" ? "Reports" : "Export"}
                </button>
              ))}
            </div>
          </div>
          <div style={{ flex: 1, overflow: "auto" }}>
            {rightPanelTab === "chat" && <ChatPanel />}
            {rightPanelTab === "agent-log" && <AgentLog />}
            {rightPanelTab === "export" && <ExportPanel />}
            {rightPanelTab === "reports" && <ReportsPanel />}
          </div>
        </aside>
      </div>

      <StatusBar />
    </div>
  );
}

function ReportsPanel() {
  const { activeDesign } = useCADStore();
  if (!activeDesign) return <EmptyState msg="Generate a design to see reports" />;
  const { dfm_report, engineering_report, cost_estimate } = activeDesign;
  return (
    <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 12 }}>
      {/* DFM */}
      {dfm_report && !dfm_report.skipped && (
        <div className="glass" style={{ padding: 12 }}>
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>DFM Analysis</div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
            <span style={{ color: "var(--text-secondary)", fontSize: 12 }}>Score</span>
            <span style={{ color: "var(--cyan)", fontWeight: 700 }}>{dfm_report.overall_score}/100</span>
          </div>
          <div className="confidence-bar"><div className="confidence-fill" style={{ width: `${dfm_report.overall_score}%` }} /></div>
          {(dfm_report.issues || []).slice(0, 3).map((issue, i) => (
            <div key={i} style={{ marginTop: 8, fontSize: 11, color: "var(--text-secondary)" }}>
              <span className={`badge badge-${issue.severity === "error" ? "error" : issue.severity === "warning" ? "warning" : "info"}`}>{issue.severity}</span>
              <span style={{ marginLeft: 6 }}>{issue.description}</span>
            </div>
          ))}
        </div>
      )}
      {/* Cost */}
      {cost_estimate && !cost_estimate.skipped && (
        <div className="glass" style={{ padding: 12 }}>
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>Cost Estimate</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: "var(--cyan)" }}>${cost_estimate.total_unit_cost_usd?.toFixed(2)}</div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>per unit</div>
          {(cost_estimate.cost_drivers || []).slice(0, 3).map((d, i) => (
            <div key={i} style={{ marginTop: 4, fontSize: 11, color: "var(--text-secondary)" }}>· {d}</div>
          ))}
        </div>
      )}
      {/* Engineering */}
      {engineering_report && !engineering_report.skipped && engineering_report.material_properties && (
        <div className="glass" style={{ padding: 12 }}>
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>Engineering</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {[
              ["Material", engineering_report.material_properties.name],
              ["Mass", `${engineering_report.mass_estimate_kg?.toFixed(3)} kg`],
              ["Safety Factor", engineering_report.safety_factor_estimate?.toFixed(1)],
              ["Yield Strength", `${engineering_report.material_properties.yield_strength_mpa} MPa`],
            ].map(([k, v]) => (
              <div key={k} style={{ background: "var(--bg-base)", borderRadius: 6, padding: "6px 8px" }}>
                <div style={{ fontSize: 10, color: "var(--text-muted)" }}>{k}</div>
                <div style={{ fontSize: 12, color: "var(--text-primary)", fontWeight: 500 }}>{v}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function EmptyState({ msg }: { msg: string }) {
  return (
    <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: 12, padding: 24, textAlign: "center" }}>
      {msg}
    </div>
  );
}
