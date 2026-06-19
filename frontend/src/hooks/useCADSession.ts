"use client";
import { useCallback } from "react";
import { useCADStore } from "@/store/cadStore";
import { api } from "@/lib/api";
import type { Session, Design, GenerateResponse } from "@/lib/types";



export function useCADSession() {
  const store = useCADStore();

  const loadSessions = useCallback(async () => {
    const sessions = await api.listSessions() as Session[];
    store.setSessions(sessions);
    return sessions;
  }, [store]);

  const createSession = useCallback(async (name?: string) => {
    const session = await api.createSession(name) as Session;
    store.setSessions([session, ...store.sessions]);
    store.setActiveSession(session);
    return session;
  }, [store]);

  const generate = useCallback(async (prompt: string): Promise<GenerateResponse> => {
    if (!store.activeSession) throw new Error("No active session");
    store.clearAgentEvents();
    store.setIsGenerating(true);
    store.setGlbUrl(null);
    store.setRightPanelTab("agent-log");

    const resp = await api.generateDesign(store.activeSession.id, prompt) as GenerateResponse;
    store.setCurrentTaskId(resp.task_id);
    return resp;
  }, [store]);

  return { loadSessions, createSession, generate };
}
