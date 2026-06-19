"use client";
import { useCADStore } from "@/store/cadStore";

export default function StatusBar() {
  const { isGenerating, activeDesign, agentEvents } = useCADStore();
  const lastEvent = agentEvents[agentEvents.length - 1];

  const runningAgent = isGenerating && lastEvent?.type === "agent_update"
    ? lastEvent.display_name : null;

  const confidence = activeDesign
    ? Object.values(activeDesign.confidence_scores || {}).reduce((a, b) => a + b, 0) /
      Math.max(Object.keys(activeDesign.confidence_scores || {}).length, 1)
    : null;

  return (
    <div style={{
      height: 28, background: "var(--bg-panel)", borderTop: "1px solid var(--border)",
      display: "flex", alignItems: "center", padding: "0 12px", gap: 12,
      fontSize: 11, color: "var(--text-muted)", flexShrink: 0,
    }}>
      {/* Status */}
      <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
        <div style={{
          width: 6, height: 6, borderRadius: "50%",
          background: isGenerating ? "var(--cyan)" : activeDesign?.geometry_valid ? "var(--success)" : "var(--text-muted)",
        }} />
        <span>
          {isGenerating ? (runningAgent ? `Running: ${runningAgent}` : "Generating...") :
            activeDesign ? (activeDesign.geometry_valid ? "Geometry valid" : "Generation failed") : "Ready"}
        </span>
      </div>

      <div style={{ flex: 1 }} />

      {/* Confidence */}
      {confidence !== null && (
        <span>Confidence: <span style={{ color: "var(--cyan)" }}>{confidence.toFixed(0)}%</span></span>
      )}

      {/* Design version */}
      {activeDesign && (
        <span>v{activeDesign.version} · {new Date(activeDesign.created_at).toLocaleTimeString()}</span>
      )}

      <span>CAD·AI Workstation v1.0</span>
    </div>
  );
}
