"use client";
import { useState, useRef, useEffect, KeyboardEvent, DragEvent, ChangeEvent } from "react";
import { useCADStore } from "@/store/cadStore";
import { useCADSession } from "@/hooks/useCADSession";
import { useDesignWebSocket } from "@/hooks/useWebSocket";
import { Send, Zap, ImagePlus, X } from "lucide-react";

const PROMPT_SUGGESTIONS = [
  "Create a 100×80×10mm aluminum mounting plate with four M6 corner holes",
  "Design a cylindrical enclosure 80mm diameter, 120mm tall with a removable lid",
  "Make a steel bracket 50×50×5mm with 45° gusset and two M8 holes",
  "Create an aluminum heat sink 100×60×30mm with 8 cooling fins",
];

const ACCEPTED_MIME = ["image/png", "image/jpeg", "image/webp", "image/bmp", "image/svg+xml"];
const MAX_IMAGES = 3;

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  images?: string[];
}

function ImageThumb({ src, onRemove }: { src: string; onRemove: () => void }) {
  return (
    <div style={{ position: "relative", width: 58, height: 58, borderRadius: 8, overflow: "hidden", border: "1.5px solid var(--border)", flexShrink: 0 }}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      <button onClick={onRemove} style={{ position: "absolute", top: 2, right: 2, background: "rgba(0,0,0,0.65)", border: "none", borderRadius: "50%", width: 18, height: 18, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", padding: 0, color: "#fff" }}>
        <X size={10} />
      </button>
    </div>
  );
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => res(r.result as string);
    r.onerror = rej;
    r.readAsDataURL(file);
  });
}

export default function ChatPanel() {
  const [prompt, setPrompt] = useState("");
  const [attachedImages, setAttachedImages] = useState<string[]>([]);
  const [dragging, setDragging] = useState(false);
  const [messages, setMessages] = useState<Message[]>([{
    role: "assistant",
    content: "Welcome to CAD·AI Workstation. Describe the part you want to design — or attach a sketch / photo — and I'll generate it with full engineering analysis.",
    timestamp: new Date(),
  }]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { isGenerating, activeDesign, activeDesignId, setRightPanelTab } = useCADStore();
  const { generate } = useCADSession();

  useDesignWebSocket(activeDesignId ?? activeDesign?.id ?? null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(Math.max(textareaRef.current.scrollHeight, 44), 180)}px`;
    }
  }, [prompt]);

  const addImages = async (files: FileList | File[]) => {
    const arr = Array.from(files).filter((f) => ACCEPTED_MIME.includes(f.type));
    const slots = MAX_IMAGES - attachedImages.length;
    if (slots <= 0) return;
    const dataUrls = await Promise.all(arr.slice(0, slots).map(fileToDataUrl));
    setAttachedImages((prev) => [...prev, ...dataUrls]);
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) addImages(e.target.files);
    e.target.value = "";
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files) addImages(e.dataTransfer.files);
  };

  const handleSend = async () => {
    if ((!prompt.trim() && attachedImages.length === 0) || isGenerating) return;
    const text = prompt.trim();
    const imgs = [...attachedImages];
    setPrompt("");
    setAttachedImages([]);

    setMessages((prev) => [
      ...prev,
      { role: "user", content: text || "(image input)", timestamp: new Date(), images: imgs },
      { role: "assistant", content: "🔄 Starting CAD generation pipeline...", timestamp: new Date() },
    ]);

    try {
      await generate(text, imgs.length > 0 ? imgs : undefined);
      setRightPanelTab("agent-log");
    } catch (e: unknown) {
      const errMsg = e instanceof Error ? e.message : String(e);
      setMessages((prev) => [...prev.slice(0, -1), { role: "assistant", content: `❌ Error: ${errMsg}`, timestamp: new Date() }]);
    }
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const hasImages = attachedImages.length > 0;
  const canAddMore = attachedImages.length < MAX_IMAGES;

  return (
    <div
      style={{ display: "flex", flexDirection: "column", height: "100%", padding: 12, gap: 8, position: "relative" }}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {dragging && (
        <div style={{ position: "absolute", inset: 0, background: "rgba(0,200,255,0.07)", border: "2px dashed var(--cyan)", borderRadius: 12, zIndex: 20, display: "flex", alignItems: "center", justifyContent: "center", pointerEvents: "none" }}>
          <span style={{ color: "var(--cyan)", fontSize: 14, fontWeight: 600 }}>Drop images here</span>
        </div>
      )}

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8 }}>
        {messages.map((msg, i) => (
          <div key={i} className="animate-slide-up" style={{ alignSelf: msg.role === "user" ? "flex-end" : "flex-start", maxWidth: "87%" }}>
            {/* Image thumbnails in bubble */}
            {msg.images && msg.images.length > 0 && (
              <div style={{ display: "flex", gap: 5, marginBottom: 5, flexWrap: "wrap", justifyContent: "flex-end" }}>
                {msg.images.map((src, j) => (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img key={j} src={src} alt="" style={{ width: 72, height: 72, objectFit: "cover", borderRadius: 8, border: "1.5px solid var(--border)" }} />
                ))}
              </div>
            )}
            <div style={{ padding: "10px 13px", borderRadius: msg.role === "user" ? "12px 12px 4px 12px" : "4px 12px 12px 12px", background: msg.role === "user" ? "linear-gradient(135deg, var(--cyan), var(--blue))" : "var(--bg-elevated)", color: msg.role === "user" ? "#fff" : "var(--text-secondary)", fontSize: 13, lineHeight: 1.5, border: msg.role === "assistant" ? "1px solid var(--border)" : "none" }}>
              {msg.content}
            </div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 3, textAlign: msg.role === "user" ? "right" : "left" }}>
              {msg.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Quick-start suggestions */}
      {messages.length <= 2 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)", paddingLeft: 2 }}>Quick start</div>
          {PROMPT_SUGGESTIONS.slice(0, 2).map((s, i) => (
            <button key={i} onClick={() => setPrompt(s)} style={{ background: "var(--bg-base)", border: "1px solid var(--border)", borderRadius: 8, padding: "6px 10px", fontSize: 11, color: "var(--text-secondary)", textAlign: "left", cursor: "pointer", transition: "all 0.15s" }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--border-glow)")}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border)")}>
              <Zap size={10} style={{ display: "inline", marginRight: 5, color: "var(--cyan)" }} />
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Attached image strip */}
      {hasImages && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", padding: "2px 0" }}>
          {attachedImages.map((src, i) => (
            <ImageThumb key={i} src={src} onRemove={() => setAttachedImages((p) => p.filter((_, j) => j !== i))} />
          ))}
          {canAddMore && (
            <button onClick={() => fileInputRef.current?.click()} title="Add another image"
              style={{ width: 58, height: 58, borderRadius: 8, border: "1.5px dashed var(--border)", background: "var(--bg-base)", color: "var(--text-muted)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 2, fontSize: 9 }}>
              <ImagePlus size={15} />add
            </button>
          )}
        </div>
      )}

      {/* Input bar */}
      <div style={{ background: "var(--bg-elevated)", border: `1px solid ${dragging ? "var(--cyan)" : "var(--border)"}`, borderRadius: 10, padding: "8px 8px 8px 12px", display: "flex", alignItems: "flex-end", gap: 8, transition: "border-color 0.2s" }}>
        <input ref={fileInputRef} type="file" accept={ACCEPTED_MIME.join(",")} multiple style={{ display: "none" }} onChange={handleFileChange} />

        {/* Attach button */}
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={isGenerating || !canAddMore}
          title={canAddMore ? "Attach image (PNG · JPG · WEBP · SVG, up to 3)" : `Max ${MAX_IMAGES} images`}
          style={{ background: "none", border: "none", cursor: canAddMore && !isGenerating ? "pointer" : "not-allowed", color: canAddMore && !isGenerating ? "var(--cyan)" : "var(--text-muted)", padding: "4px 2px", display: "flex", alignItems: "center", gap: 3, transition: "color 0.15s", flexShrink: 0 }}>
          <ImagePlus size={17} />
          {attachedImages.length > 0 && <span style={{ fontSize: 10 }}>{attachedImages.length}/{MAX_IMAGES}</span>}
        </button>

        <textarea
          ref={textareaRef}
          rows={2}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKey}
          placeholder={hasImages ? "Describe your part (optional when image is attached)…" : "Describe your part in detail (dimensions, holes, features, materials)… Shift+Enter for new line"}
          disabled={isGenerating}
          style={{ flex: 1, background: "transparent", border: "none", outline: "none", resize: "none", color: "var(--text-primary)", fontSize: 13, fontFamily: "inherit", lineHeight: 1.5, maxHeight: 180, overflowY: "auto" }}
        />

        {prompt.trim().length > 30 && (
          <div style={{ fontSize: 10, color: "var(--text-muted)", alignSelf: "center", whiteSpace: "nowrap", paddingRight: 4 }}>
            {prompt.trim().split(/\s+/).filter(Boolean).length} words
          </div>
        )}

        <button
          className="btn btn-primary"
          onClick={handleSend}
          disabled={isGenerating || (!prompt.trim() && !hasImages)}
          style={{ padding: "8px 12px", flexShrink: 0 }}>
          {isGenerating
            ? <div style={{ width: 14, height: 14, border: "1.5px solid rgba(255,255,255,0.4)", borderTop: "1.5px solid #fff", borderRadius: "50%" }} className="animate-spin" />
            : <Send size={14} />}
        </button>
      </div>

      {/* Helper hint */}
      {hasImages && (
        <div style={{ fontSize: 10, color: "var(--text-muted)", textAlign: "center", paddingBottom: 2 }}>
          ✦ {attachedImages.length} image{attachedImages.length > 1 ? "s" : ""} attached — AI vision will extract dimensions, shape &amp; features
        </div>
      )}
    </div>
  );
}

