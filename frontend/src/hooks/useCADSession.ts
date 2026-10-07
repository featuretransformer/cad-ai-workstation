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
   * Used as fallback when WebSocket/Redis is unavailable.
   */
  const startPolling = useCallback((designId: string) => {
    stopPolling();
    let attempts = 0;
    const MAX_ATTEMPTS = 120; // 120 × 3s = 6 minutes max

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
            store.setGlbUrl(
              `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/export/${designId}/download/glb`
            );
          }
        }
      } catch {
        // ignore transient errors
      }

      if (attempts >= MAX_ATTEMPTS) {
        stopPolling();
        store.setIsGenerating(false);
      }
    }, 3000);
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

      // Start polling as a fallback completion detector (works even without WebSocket/Redis)
      // If WebSocket delivers pipeline_complete first, polling will just see COMPLETE and stop.
      startPolling(resp.design_id);

      return resp;
    } catch (err) {
      // BUG #6 FIX: always reset isGenerating on API error so UI doesn't get stuck
      store.setIsGenerating(false);
      throw err;
    }
  }, [store, startPolling, stopPolling]);

  return { loadSessions, createSession, generate };
}
