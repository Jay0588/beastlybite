"use client";

/**
 * J.A.Y. Global File Upload
 *
 * Two entry points:
 *  1. Drag-and-drop anywhere on screen — a glowing overlay appears
 *  2. Paperclip button in the Chat panel input bar
 *
 * When a file is dropped / selected:
 *  - Text files  → content is read and sent to J.A.Y. as context
 *  - Images      → base64 data-url is stored and shown as preview
 *  - Binary      → hex/info summary shown
 *
 * The upload zone publishes to the global store so any panel can
 * react to uploaded files.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, X, FileText, Image, File, CheckCircle } from "lucide-react";
import { useStore } from "@/store";
import type { UploadedFile } from "@/types";

// ── helpers ───────────────────────────────────────────────────────────────────

function genId() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

const TEXT_TYPES = new Set([
  "text/plain", "text/html", "text/css", "text/javascript",
  "text/typescript", "application/json", "application/xml",
  "application/javascript", "application/typescript",
  "text/markdown", "text/x-python", "text/x-java-source",
  "text/x-c", "text/x-cpp", "text/x-rust", "text/x-go",
  "text/x-sh", "text/x-yaml", "application/x-yaml",
  "application/toml", "text/csv",
]);

const TEXT_EXTS = new Set([
  "txt", "md", "py", "js", "ts", "jsx", "tsx", "json", "yaml", "yml",
  "toml", "html", "css", "scss", "sh", "bash", "rs", "go", "java",
  "cpp", "c", "h", "sql", "env", "gitignore", "dockerfile", "rb",
  "php", "swift", "kt", "xml", "csv", "log",
]);

function isTextFile(file: File): boolean {
  if (TEXT_TYPES.has(file.type)) return true;
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  return TEXT_EXTS.has(ext);
}

function isImageFile(file: File): boolean {
  return file.type.startsWith("image/");
}

function formatSize(bytes: number): string {
  if (bytes < 1024)       return `${bytes} B`;
  if (bytes < 1024 ** 2)  return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

async function readAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload  = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsText(file, "utf-8");
  });
}

async function readAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload  = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface UploadResult extends UploadedFile {
  dataUrl?: string;     // for images
  isImage: boolean;
  isText:  boolean;
}

// ── Toast-style confirmation ───────────────────────────────────────────────────

function UploadToast({ files, onDismiss }: { files: UploadResult[]; onDismiss: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 4000);
    return () => clearTimeout(t);
  }, [files]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 20, scale: 0.95 }}
      className="fixed bottom-6 right-6 z-[200] flex flex-col gap-2 max-w-sm"
    >
      {files.map((f) => (
        <div
          key={f.id}
          className="flex items-center gap-3 px-4 py-3 bg-jay-panel border border-jay-green/30 rounded-xl shadow-lg backdrop-blur-sm"
        >
          <CheckCircle size={16} className="text-jay-green flex-shrink-0" />
          <div className="min-w-0">
            <div className="text-xs font-mono text-jay-text truncate">{f.name}</div>
            <div className="text-[10px] text-jay-textMuted">
              {formatSize(f.size)} · {f.isImage ? "image" : f.isText ? "sent to J.A.Y." : "binary"}
            </div>
          </div>
          <button onClick={onDismiss} className="text-jay-textMuted hover:text-jay-text ml-auto">
            <X size={12} />
          </button>
        </div>
      ))}
    </motion.div>
  );
}

// ── Drop overlay ──────────────────────────────────────────────────────────────

function DropOverlay({ active }: { active: boolean }) {
  return (
    <AnimatePresence>
      {active && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[150] pointer-events-none flex items-center justify-center"
          style={{ background: "rgba(5,10,20,0.85)" }}
        >
          {/* Animated border */}
          <motion.div
            animate={{ scale: [1, 1.02, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="border-2 border-dashed border-jay-accent/60 rounded-3xl w-[500px] h-[280px] flex flex-col items-center justify-center gap-4"
            style={{ boxShadow: "0 0 60px rgba(0,212,255,0.15), inset 0 0 40px rgba(0,212,255,0.05)" }}
          >
            <motion.div
              animate={{ y: [-4, 4, -4] }}
              transition={{ duration: 1.2, repeat: Infinity }}
            >
              <Upload size={48} className="text-jay-accent" />
            </motion.div>
            <div className="text-center">
              <div className="text-xl font-display font-bold text-jay-text tracking-wide">Drop files for J.A.Y.</div>
              <div className="text-sm text-jay-textDim mt-1">Code · Documents · Images · Data</div>
            </div>
            <div className="flex gap-2">
              {["Python", "TypeScript", "JSON", "Images", "Text"].map((t) => (
                <span key={t} className="text-[10px] font-mono px-2 py-0.5 border border-jay-accent/20 text-jay-accent/70 rounded">
                  {t}
                </span>
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// ── Upload manager (headless logic) ───────────────────────────────────────────

export function useFileUpload() {
  const { addMessage, activeConversationId, setActiveConversation, addNotification } = useStore();

  const processFiles = useCallback(async (fileList: FileList | File[]) => {
    const files = Array.from(fileList);
    const results: UploadResult[] = [];

    for (const file of files) {
      const id   = genId();
      const isImg  = isImageFile(file);
      const isText = !isImg && isTextFile(file);

      let content  = "";
      let dataUrl: string | undefined;

      if (isImg) {
        dataUrl = await readAsDataURL(file);
        content = `[Image: ${file.name} (${formatSize(file.size)})] — analyzing with vision AI…`;
      } else if (isText) {
        try {
          const raw = await readAsText(file);
          content   = raw.slice(0, 200_000); // 200KB limit
        } catch {
          content = `[Could not read: ${file.name}]`;
        }
      } else {
        content = `[Binary file: ${file.name} (${formatSize(file.size)})]`;
      }

      results.push({
        id,
        name:        file.name,
        content,
        size:        file.size,
        type:        file.type,
        uploadedAt:  new Date().toISOString(),
        isImage:     isImg,
        isText,
        dataUrl,
      });
    }

    // Inject into chat as a context message
    const convId = activeConversationId || genId();
    if (!activeConversationId) setActiveConversation(convId);

    for (const r of results) {
      let chatContent = "";

      if (r.isImage) {
        // Show image inline + analyze with vision AI
        chatContent = `📎 **${r.name}** *(image, ${formatSize(r.size)})*\n\n![${r.name}](${r.dataUrl})`;
        addMessage({ id: r.id, role: "user", content: chatContent, created_at: r.uploadedAt });

        // Call vision API to analyze the image
        try {
          const visionResp = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/vision/analyze`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                image_base64: r.dataUrl ?? "",
                prompt: "Analyze this image in detail. Describe what you see including: objects, text, colors, layout, and any relevant context.",
              }),
            }
          );
          if (visionResp.ok) {
            const visionData = await visionResp.json();
            addMessage({
              id: genId(),
              role: "assistant",
              content: `**Image Analysis** *(via ${visionData.provider}/${visionData.model_used})*\n\n${visionData.description}`,
              created_at: new Date().toISOString(),
            });
          } else {
            const errText = await visionResp.text();
            addMessage({
              id: genId(),
              role: "assistant",
              content: `*I can see you uploaded an image, but I need a vision model to analyze it.*\n\nTo enable image understanding:\n- **Local:** Run \`ollama pull llava\`\n- **Cloud:** Set \`OPENROUTER_API_KEY\` in \`backend/.env\`\n\n*Error: ${errText.slice(0, 200)}*`,
              created_at: new Date().toISOString(),
            });
          }
        } catch (e: any) {
          addMessage({
            id: genId(),
            role: "assistant",
            content: `*Image uploaded but vision analysis failed: ${e.message}. Make sure the backend is running.*`,
            created_at: new Date().toISOString(),
          });
        }
        continue; // Skip the generic injection below
      } else if (r.isText) {
        const lang = r.name.split(".").pop() ?? "";
        chatContent = `📎 **${r.name}** *(${formatSize(r.size)}, ${r.content.split("\n").length} lines)*\n\n\`\`\`${lang}\n${r.content.slice(0, 8000)}${r.content.length > 8000 ? "\n\n// ... truncated" : ""}\n\`\`\``;
      } else {
        chatContent = `📎 **${r.name}** *(binary, ${formatSize(r.size)})*`;
      }

      // Add as a "user" message so J.A.Y. sees the file
      addMessage({
        id:         r.id,
        role:       "user",
        content:    chatContent,
        created_at: r.uploadedAt,
      });
    }

    // Auto-prompt J.A.Y.
    if (results.length > 0) {
      const names = results.map((r) => r.name).join(", ");
      addMessage({
        id:         genId(),
        role:       "user",
        content:    `I've uploaded: ${names}. Please review and tell me what you see.`,
        created_at: new Date().toISOString(),
      });
    }

    addNotification({
      title:   "Files uploaded",
      message: `${results.length} file${results.length > 1 ? "s" : ""} sent to J.A.Y.`,
      type:    "success",
    });

    return results;
  }, [activeConversationId]);

  return { processFiles };
}

// ── Global drag-and-drop listener ─────────────────────────────────────────────

export function GlobalDropZone() {
  const [dragging, setDragging]   = useState(false);
  const [toast, setToast]         = useState<UploadResult[]>([]);
  const dragCounter               = useRef(0);
  const { processFiles }          = useFileUpload();

  useEffect(() => {
    const onEnter = (e: DragEvent) => {
      if (!e.dataTransfer?.types.includes("Files")) return;
      dragCounter.current++;
      setDragging(true);
    };
    const onLeave = () => {
      dragCounter.current--;
      if (dragCounter.current <= 0) { dragCounter.current = 0; setDragging(false); }
    };
    const onOver  = (e: DragEvent) => { e.preventDefault(); };
    const onDrop  = async (e: DragEvent) => {
      e.preventDefault();
      dragCounter.current = 0;
      setDragging(false);
      if (!e.dataTransfer?.files?.length) return;
      const results = await processFiles(e.dataTransfer.files);
      setToast(results);
    };

    window.addEventListener("dragenter", onEnter);
    window.addEventListener("dragleave", onLeave);
    window.addEventListener("dragover",  onOver);
    window.addEventListener("drop",      onDrop);
    return () => {
      window.removeEventListener("dragenter", onEnter);
      window.removeEventListener("dragleave", onLeave);
      window.removeEventListener("dragover",  onOver);
      window.removeEventListener("drop",      onDrop);
    };
  }, [processFiles]);

  return (
    <>
      <DropOverlay active={dragging} />
      <AnimatePresence>
        {toast.length > 0 && (
          <UploadToast files={toast} onDismiss={() => setToast([])} />
        )}
      </AnimatePresence>
    </>
  );
}

// ── Inline upload button (for Chat panel) ─────────────────────────────────────

export function UploadButton({ className = "" }: { className?: string }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const { processFiles } = useFileUpload();
  const { setActivePanel } = useStore();

  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    await processFiles(e.target.files);
    // Switch to chat so user sees the file
    setActivePanel("chat");
    e.target.value = "";
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept="*/*"
        onChange={handleChange}
        className="hidden"
      />
      <button
        onClick={() => inputRef.current?.click()}
        title="Upload files for J.A.Y. to read"
        className={`p-2 rounded-lg text-jay-textDim hover:text-jay-accent hover:bg-jay-accent/10 border border-transparent hover:border-jay-accent/30 transition-all ${className}`}
      >
        <Upload size={16} />
      </button>
    </>
  );
}
