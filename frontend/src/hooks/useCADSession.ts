"use client";
import { useCallback } from "react";
import { useCADStore } from "@/store/cadStore";
import { api } from "@/lib/api";
import type { Session } from "@/lib/types";

interface GenerateResponse {
  task_id: string;
  design_id: string;
  message: string;
}

export function useCADSession() {
  const store = useCADStore();

  const loadSessions = useCallback(async (): Promise<Session[]> => {
    try {
      const sessions = (await api.listSessions()) as Session[] | null;
      const list = sessions ?? [];
      store.setSessions(list);
      return list;
    } catch {
      // Backend offline — stay quiet, return empty list
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
      // Backend offline — can't create session
      return null;
    }
  }, [store]);

  const generate = useCallback(async (prompt: string): Promise<GenerateResponse> => {
    if (!store.activeSession) throw new Error("No active session");
    store.clearAgentEvents();
    store.setIsGenerating(true);
    store.setGlbUrl(null);
    store.setRightPanelTab("agent-log");

    const resp = (await api.generateDesign(store.activeSession.id, prompt)) as GenerateResponse;
    store.setCurrentTaskId(resp.task_id);
    return resp;
  }, [store]);

  return { loadSessions, createSession, generate };
}
