"use client";
import { useEffect } from "react";
import { useCADStore } from "@/store/cadStore";
import { api } from "@/lib/api";
import type { ExportArtifact } from "@/lib/types";
import { Download, FileBox, Layers, Code2, Box } from "lucide-react";

const FORMAT_META: Record<string, { label: string; icon: React.ReactNode; desc: string }> = {
  step: { label: "STEP", icon: <FileBox size={16} />, desc: "ISO 10303 — universal CAD exchange" },
  stl: { label: "STL", icon: <Layers size={16} />, desc: "Mesh — 3D printing / slicer" },
  glb: { label: "GLB", icon: <Box size={16} />, desc: "Binary glTF — web/game engine" },
  dxf: { label: "DXF", icon: <Code2 size={16} />, desc: "Drawing exchange — 2D CAM" },
};

export default function ExportPanel() {
  const { activeDesign, exports, setExports } = useCADStore();

  useEffect(() => {
    if (activeDesign?.id) {
      api.getExports(activeDesign.id).then((e) => setExports(e as ExportArtifact[])).catch(() => {});
    }
  }, [activeDesign?.id, setExports]);

  if (!activeDesign || !activeDesign.geometry_valid) {
    return (
      <div style={{ padding: 24, textAlign: "center", color: "var(--text-muted)", fontSize: 12 }}>
        <div style={{ fontSize: 28, marginBottom: 8 }}>📦</div>
        Export files will be available after a successful design generation
      </div>
    );
  }

  const handleDownload = (format: string) => {
    const url = api.getDownloadUrl(activeDesign.id, format);
    window.open(url, "_blank");
  };

  const availableFormats = exports.map(e => e.format.toLowerCase());

  return (
    <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>
        Export Files
      </div>

      {Object.entries(FORMAT_META).map(([fmt, meta]) => {
        const available = availableFormats.includes(fmt);
        const artifact = exports.find(e => e.format.toLowerCase() === fmt);
        const sizeKB = artifact ? (artifact.file_size_bytes / 1024).toFixed(1) : null;

        return (
          <div key={fmt} className="glass" style={{
            padding: "12px", display: "flex", alignItems: "center", gap: 12,
            opacity: available ? 1 : 0.4,
          }}>
            <div style={{ color: available ? "var(--cyan)" : "var(--text-muted)" }}>{meta.icon}</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{meta.label}</div>
              <div style={{ fontSize: 10, color: "var(--text-muted)" }}>{meta.desc}</div>
              {sizeKB && <div style={{ fontSize: 10, color: "var(--text-muted)" }}>{sizeKB} KB</div>}
            </div>
            <button
              className="btn btn-primary"
              style={{ padding: "6px 12px", fontSize: 11 }}
              disabled={!available}
              onClick={() => handleDownload(fmt)}
            >
              <Download size={12} />
              Download
            </button>
          </div>
        );
      })}

      {activeDesign.alternatives && activeDesign.alternatives.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>
            Design Alternatives ({activeDesign.alternatives.length})
          </div>
          {activeDesign.alternatives.map((alt) => (
            <div key={alt.id} className="glass" style={{ padding: 10, marginBottom: 6 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>{alt.name}</div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 3 }}>{alt.description}</div>
              <div style={{ fontSize: 10, color: "var(--warning)", marginTop: 4 }}>⚖ {alt.tradeoffs}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
