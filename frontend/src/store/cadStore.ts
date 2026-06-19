"use client";
import { create } from "zustand";
import type { Session, Design, AgentLog, WSEvent, ExportArtifact } from "@/lib/types";

interface CADStore {
  // Sessions
  sessions: Session[];
  activeSession: Session | null;
  setSessions: (s: Session[]) => void;
  setActiveSession: (s: Session | null) => void;

  // Design
  activeDesign: Design | null;
  setActiveDesign: (d: Design | null) => void;

  // Agent activity
  agentEvents: WSEvent[];
  addAgentEvent: (e: WSEvent) => void;
  clearAgentEvents: () => void;

  // Pipeline state
  isGenerating: boolean;
  setIsGenerating: (v: boolean) => void;
  currentTaskId: string | null;
  setCurrentTaskId: (id: string | null) => void;

  // Exports
  exports: ExportArtifact[];
  setExports: (e: ExportArtifact[]) => void;

  // 3D Viewer
  glbUrl: string | null;
  setGlbUrl: (url: string | null) => void;
  wireframe: boolean;
  toggleWireframe: () => void;

  // UI panels
  leftPanelTab: "feature-tree" | "sessions";
  setLeftPanelTab: (t: "feature-tree" | "sessions") => void;
  rightPanelTab: "chat" | "agent-log" | "reports" | "export";
  setRightPanelTab: (t: "chat" | "agent-log" | "reports" | "export") => void;
}

export const useCADStore = create<CADStore>((set) => ({
  sessions: [],
  activeSession: null,
  setSessions: (sessions) => set({ sessions }),
  setActiveSession: (activeSession) => set({ activeSession }),

  activeDesign: null,
  setActiveDesign: (activeDesign) => set({ activeDesign }),

  agentEvents: [],
  addAgentEvent: (e) => set((s) => ({ agentEvents: [...s.agentEvents.slice(-100), e] })),
  clearAgentEvents: () => set({ agentEvents: [] }),

  isGenerating: false,
  setIsGenerating: (isGenerating) => set({ isGenerating }),
  currentTaskId: null,
  setCurrentTaskId: (currentTaskId) => set({ currentTaskId }),

  exports: [],
  setExports: (exports) => set({ exports }),

  glbUrl: null,
  setGlbUrl: (glbUrl) => set({ glbUrl }),
  wireframe: false,
  toggleWireframe: () => set((s) => ({ wireframe: !s.wireframe })),

  leftPanelTab: "feature-tree",
  setLeftPanelTab: (leftPanelTab) => set({ leftPanelTab }),
  rightPanelTab: "chat",
  setRightPanelTab: (rightPanelTab) => set({ rightPanelTab }),
}));
