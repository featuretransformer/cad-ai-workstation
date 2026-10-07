"use client";
import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { useCADStore } from "@/store/cadStore";
import { useCADSession } from "@/hooks/useCADSession";
import { useDesignWebSocket } from "@/hooks/useWebSocket";
import { Send, Zap, RotateCcw } from "lucide-react";

const PROMPT_SUGGESTIONS = [
  "Create a 100×80×10mm aluminum mounting plate with four M6 corner holes",
  "Design a cylindrical enclosure 80mm diameter, 120mm tall with a removable lid",
  "Make a steel bracket 50×50×5mm with 45° gusset and two M8 holes",
  "Create an aluminum heat sink 100×60×30mm with 8 cooling fins",
];

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export default function ChatPanel() {
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<Message[]>([{
    role: "assistant",
    content: "Welcome to CAD·AI Workstation. Describe the part you want to design and I'll generate it using parametric CAD with full engineering analysis.",
    timestamp: new Date(),
  }]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const { isGenerating, activeDesign, setRightPanelTab } = useCADStore();
  const { generate } = useCADSession();
  const { activeDesign: design } = useCADStore();

  // Connect WebSocket when we have a design ID
  useDesignWebSocket(activeDesign?.id ?? null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!prompt.trim() || isGenerating) return;
    const text = prompt.trim();
    setPrompt("");

    setMessages(prev => [...prev, { role: "user", content: text, timestamp: new Date() }]);
    setMessages(prev => [...prev, { role: "assistant", content: "🔄 Starting CAD generation pipeline...", timestamp: new Date() }]);

    try {
      await generate(text);
      setRightPanelTab("agent-log");
    } catch (e: unknown) {
      const errMsg = e instanceof Error ? e.message : String(e);
      setMessages(prev => [...prev.slice(0, -1), {
        role: "assistant",
        content: `❌ Error: ${errMsg}`,
        timestamp: new Date(),
      }]);
    }
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: 12, gap: 8 }}>
      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8 }}>
        {messages.map((msg, i) => (
          <div key={i} className="animate-slide-up" style={{
            alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
            maxWidth: "85%",
          }}>
            <div style={{
              padding: "10px 13px",
              borderRadius: msg.role === "user" ? "12px 12px 4px 12px" : "4px 12px 12px 12px",
              background: msg.role === "user" ? "linear-gradient(135deg, var(--cyan), var(--blue))" : "var(--bg-elevated)",
              color: msg.role === "user" ? "#fff" : "var(--text-secondary)",
              fontSize: 13, lineHeight: 1.5,
              border: msg.role === "assistant" ? "1px solid var(--border)" : "none",
            }}>
              {msg.content}
            </div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 3, textAlign: msg.role === "user" ? "right" : "left" }}>
              {msg.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Suggestions */}
      {messages.length <= 2 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)", paddingLeft: 2 }}>Quick start</div>
          {PROMPT_SUGGESTIONS.slice(0, 2).map((s, i) => (
            <button key={i} onClick={() => setPrompt(s)} style={{
              background: "var(--bg-base)", border: "1px solid var(--border)",
              borderRadius: 8, padding: "6px 10px", fontSize: 11, color: "var(--text-secondary)",
              textAlign: "left", cursor: "pointer", transition: "all 0.15s",
            }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = "var(--border-glow)")}
              onMouseLeave={e => (e.currentTarget.style.borderColor = "var(--border)")}
            >
              <Zap size={10} style={{ display: "inline", marginRight: 5, color: "var(--cyan)" }} />
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={{
        background: "var(--bg-elevated)", border: "1px solid var(--border)",
        borderRadius: 10, padding: "8px 8px 8px 12px",
        display: "flex", alignItems: "flex-end", gap: 8,
        transition: "border-color 0.2s",
      }}
        onFocus={() => {}}
      >
        <textarea
          ref={textareaRef}
          rows={2}
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Describe your part... (Enter to send)"
          disabled={isGenerating}
          style={{
            flex: 1, background: "transparent", border: "none", outline: "none",
            resize: "none", color: "var(--text-primary)", fontSize: 13,
            fontFamily: "inherit", lineHeight: 1.5,
          }}
        />
        <button
          className="btn btn-primary"
          onClick={handleSend}
          disabled={isGenerating || !prompt.trim()}
          style={{ padding: "8px 12px", flexShrink: 0 }}
        >
          {isGenerating ? <div style={{ width: 14, height: 14, border: "1.5px solid rgba(255,255,255,0.4)", borderTop: "1.5px solid #fff", borderRadius: "50%" }} className="animate-spin" /> : <Send size={14} />}
        </button>
      </div>
    </div>
  );
}
