"use client";
import { useCADStore } from "@/store/cadStore";
import type { Feature } from "@/lib/types";

const TYPE_COLORS: Record<string, string> = {
  primitive: "var(--cyan)", feature: "var(--blue)", modify: "var(--warning)", pattern: "var(--success)",
};
const TYPE_ICONS: Record<string, string> = {
  primitive: "■", feature: "◆", modify: "⬡", pattern: "⊞",
};

function FeatureNode({ feature }: { feature: Feature }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8, padding: "5px 8px", borderRadius: 6,
      cursor: "pointer", transition: "background 0.15s",
      opacity: feature.suppressed ? 0.4 : 1,
    }}
      onMouseEnter={e => (e.currentTarget.style.background = "var(--bg-elevated)")}
      onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
    >
      <span style={{ color: TYPE_COLORS[feature.type] ?? "var(--text-muted)", fontSize: 10 }}>
        {TYPE_ICONS[feature.type] ?? "·"}
      </span>
      <span style={{ flex: 1, fontSize: 12, color: "var(--text-secondary)" }}>{feature.name}</span>
      <span style={{ fontSize: 9, color: "var(--text-muted)", fontFamily: "JetBrains Mono, monospace" }}>
        L{feature.line}
      </span>
    </div>
  );
}

export default function FeatureTree() {
  const { activeDesign } = useCADStore();
  const features = activeDesign?.feature_tree?.root?.children ?? [];

  if (!activeDesign) {
    return (
      <div style={{ padding: 16, textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
        <div style={{ fontSize: 28, marginBottom: 8 }}>🗂️</div>
        Feature tree will appear after generating a design
      </div>
    );
  }

  return (
    <div>
      {/* Root node */}
      <div style={{ padding: "6px 8px", display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
        <span style={{ fontSize: 10 }}>▼</span>
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
          {activeDesign.feature_tree?.root?.name ?? "Design"}
        </span>
        <span className="badge badge-info" style={{ fontSize: 9 }}>{features.length}</span>
      </div>

      {/* Feature list */}
      <div style={{ paddingLeft: 12, borderLeft: "1px solid var(--border)", marginLeft: 12 }}>
        {features.length === 0 ? (
          <div style={{ fontSize: 11, color: "var(--text-muted)", padding: 8 }}>No features extracted</div>
        ) : (
          features.map((f) => <FeatureNode key={f.id} feature={f} />)
        )}
      </div>

      {/* Legend */}
      <div style={{ marginTop: 12, padding: "8px", background: "var(--bg-base)", borderRadius: 6, display: "flex", flexWrap: "wrap", gap: 8 }}>
        {Object.entries(TYPE_COLORS).map(([t, c]) => (
          <div key={t} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 10, color: "var(--text-muted)" }}>
            <span style={{ color: c }}>{TYPE_ICONS[t]}</span> {t}
          </div>
        ))}
      </div>
    </div>
  );
}
