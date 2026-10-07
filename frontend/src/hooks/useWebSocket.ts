"use client";
import { useEffect, useRef, useCallback } from "react";
import { useCADStore } from "@/store/cadStore";
import type { WSEvent } from "@/lib/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
const MAX_RECONNECTS = 5;

export function useDesignWebSocket(designId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnects = useRef(0);
  const { addAgentEvent, setIsGenerating, setActiveDesign, setGlbUrl } = useCADStore();

  const connect = useCallback(() => {
    if (!designId || wsRef.current?.readyState === WebSocket.OPEN) return;
    const ws = new WebSocket(`${WS_URL}/ws/${designId}`);
    wsRef.current = ws;
    ws.onopen = () => { reconnects.current = 0; };
    ws.onmessage = (ev) => {
      try {
        const event: WSEvent = JSON.parse(ev.data);
        addAgentEvent(event);
        if (event.type === "pipeline_complete" || event.type === "pipeline_error") {
          setIsGenerating(false);
          import("@/lib/api").then(({ api }) => api.getDesign(designId).then((d: unknown) => setActiveDesign(d as import("@/lib/types").Design)));
          if (event.type === "pipeline_complete" && event.export_paths?.glb) {
            setGlbUrl(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/export/${designId}/download/glb`);
          }
        }
      } catch { /* ignore malformed events */ }
    };
    ws.onerror = () => ws.close();
    ws.onclose = () => {
      wsRef.current = null;
      if (reconnects.current < MAX_RECONNECTS) {
        const delay = Math.min(1000 * 2 ** reconnects.current, 10000);
        reconnects.current += 1;
        reconnectTimer.current = setTimeout(connect, delay);
      }
    };
  }, [designId, addAgentEvent, setIsGenerating, setActiveDesign, setGlbUrl]);

  useEffect(() => {
    reconnects.current = 0;
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  return wsRef;
}
