"use client";
import { useCallback, useRef } from "react";
import { useCADStore } from "@/store/cadStore";
import { api } from "@/lib/api";
import type { Session, Design } from "@/lib/types";

interface GenerateResponse {
  task_id: string;
  design_id: string;
  message: string;
}

export function useCADSession() {
  const store = useCADStore();
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadSessions = useCallback(async (): Promise<Session[]> => {
    try {
      const sessions = (await api.listSessions()) as Session[] | null;
      const list = sessions ?? [];
      store.setSessions(list);
      return list;
    } catch {
      return [];
    }
  }, [store]);

  const createSession = useCallback(async (name?: string): Promise<Session | null> => {
    try {
      const session = (await api.createSession(name)) as Session;
      store.setSessions([session, ...store.sessions]);
      store.setActiveSession(session);
      return session;
    } catch {
      return null;
    }
  }, [store]);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  /**
   * Polls /api/design/{design_id} until status is COMPLETE or FAILED.
   * Used as fallback when WebSocket/Redis is unavailable or as a complementary watcher.
   */
  const startPolling = useCallback((designId: string) => {
    stopPolling();
    let attempts = 0;
    const MAX_ATTEMPTS = 120; // 120 × 2s = 4 minutes max

    pollingRef.current = setInterval(async () => {
      attempts++;
      try {
        const design = (await api.getDesign(designId)) as Design;
        const status = (design as unknown as { status?: string }).status;

        if (status === "COMPLETE" || status === "FAILED") {
          stopPolling();
          store.setIsGenerating(false);
          store.setActiveDesign(design);
          if (status === "COMPLETE") {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            store.setGlbUrl(`${API_URL}/api/export/${designId}/download/glb?t=${Date.now()}`);
          }
        }
      } catch {
        // ignore transient errors
      }

      if (attempts >= MAX_ATTEMPTS) {
        stopPolling();
        store.setIsGenerating(false);
        try {
          const finalDesign = (await api.getDesign(designId)) as Design;
          if (finalDesign) {
            store.setActiveDesign(finalDesign);
            if (finalDesign.status === "COMPLETE") {
              const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
              store.setGlbUrl(`${API_URL}/api/export/${designId}/download/glb?t=${Date.now()}`);
            }
          }
        } catch {
          // ignore
        }
      }
    }, 2000);
  }, [store, stopPolling]);

  const generate = useCallback(async (prompt: string): Promise<GenerateResponse> => {
    if (!store.activeSession) throw new Error("No active session");

    stopPolling();
    store.clearAgentEvents();
    store.setIsGenerating(true);
    store.setGlbUrl(null);
    store.setRightPanelTab("agent-log");

    try {
      const resp = (await api.generateDesign(store.activeSession.id, prompt)) as GenerateResponse;
      store.setCurrentTaskId(resp.task_id);
      store.setActiveDesignId(resp.design_id);

      // Start polling as a fallback completion detector
      startPolling(resp.design_id);

      return resp;
    } catch (err) {
      store.setIsGenerating(false);
      throw err;
    }
  }, [store, startPolling, stopPolling]);

  return { loadSessions, createSession, generate };
}
