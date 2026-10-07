"use client";
import { useCallback, useRef } from "react";
import { useCADStore } from "@/store/cadStore";
import { api } from "@/lib/api";
import type { Session, Design } from "@/lib/types";

interface GenerateResponse { task_id: string; design_id: string; message: string; }

export function useCADSession() {
  const store = useCADStore();
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const loadSessions = useCallback(async (): Promise<Session[]> => {
    const sessions = (await api.listSessions()) as Session[] | null;
    const list = sessions ?? [];
    store.setSessions(list);
    return list;
  }, [store]);
  const createSession = useCallback(async (name?: string): Promise<Session | null> => {
    try {
      const session = (await api.createSession(name)) as Session;
      store.setSessions([session, ...store.sessions]); store.setActiveSession(session); return session;
    } catch { return null; }
  }, [store]);
  const stopPolling = useCallback(() => { if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; } }, []);
  const startPolling = useCallback((designId: string) => {
    stopPolling(); let attempts = 0;
    pollingRef.current = setInterval(async () => {
      attempts += 1;
      try {
        const design = (await api.getDesign(designId)) as Design;
        if (design.status === "COMPLETE" || design.status === "FAILED") {
          stopPolling(); store.setIsGenerating(false); store.setActiveDesign(design);
          if (design.status === "COMPLETE") store.setGlbUrl(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/export/${designId}/download/glb`);
        }
      } catch { /* websocket remains the primary live path */ }
      if (attempts >= 120) { stopPolling(); store.setIsGenerating(false); }
    }, 3000);
  }, [store, stopPolling]);
  const generate = useCallback(async (prompt: string): Promise<GenerateResponse> => {
    if (!store.activeSession) throw new Error("No active session");
    stopPolling(); store.clearAgentEvents(); store.setIsGenerating(true); store.setGlbUrl(null); store.setRightPanelTab("agent-log");
    try {
      const resp = (await api.generateDesign(store.activeSession.id, prompt)) as GenerateResponse;
      store.setCurrentTaskId(resp.task_id); startPolling(resp.design_id); return resp;
    } catch (err) { store.setIsGenerating(false); throw err; }
  }, [store, startPolling, stopPolling]);
  return { loadSessions, createSession, generate };
}
