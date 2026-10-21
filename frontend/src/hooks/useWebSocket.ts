"use client";
import { useEffect, useRef, useCallback } from "react";
import { useCADStore } from "@/store/cadStore";
import type { WSEvent } from "@/lib/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export function useDesignWebSocket(designId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const { addAgentEvent, setIsGenerating, setActiveDesign, setGlbUrl } = useCADStore();

  const connect = useCallback(() => {
    if (!designId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(`${WS_URL}/ws/${designId}`);
      wsRef.current = ws;

      ws.onmessage = (ev) => {
        try {
          const event: WSEvent = JSON.parse(ev.data);
          addAgentEvent(event);

          if (event.type === "pipeline_complete") {
            setIsGenerating(false);
            const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            setGlbUrl(`${API_URL}/api/export/${designId}/download/glb?t=${Date.now()}`);

            // Refresh design from API
            import("@/lib/api").then(({ api }) => {
              api.getDesign(designId).then((d: unknown) => {
                if (d) setActiveDesign(d as import("@/lib/types").Design);
              });
            });
          }
          if (event.type === "pipeline_error") {
            setIsGenerating(false);
            import("@/lib/api").then(({ api }) => {
              api.getDesign(designId).then((d: unknown) => {
                if (d) setActiveDesign(d as import("@/lib/types").Design);
              });
            });
          }
        } catch {
          // ignore parse errors
        }
      };

      ws.onerror = () => {
        try {
          ws.close();
        } catch {
          // ignore
        }
      };
      ws.onclose = () => {
        wsRef.current = null;
      };
    } catch {
      // WebSocket connection failed (e.g. backend offline)
      wsRef.current = null;
    }
  }, [designId, addAgentEvent, setIsGenerating, setActiveDesign, setGlbUrl]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  return wsRef;
}
