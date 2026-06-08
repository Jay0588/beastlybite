"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Mic, MicOff, Plus, Trash2, ChevronRight } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useStore } from "@/store";
import { chatAPI } from "@/lib/api";
import type { Message } from "@/types";
import { v4 as uuid } from "crypto";
import VoiceVisualizer from "@/components/hud/visualizer/VoiceVisualizer";

// Inline uuid for browser
function genId() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className={`flex ${isUser ? "justify-end" : "justify-start"} group`}
    >
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 text-sm ${
          isUser
            ? "bg-jay-accent/10 border border-jay-accent/30 text-jay-text"
            : "bg-jay-panel border border-jay-border/50 text-jay-text"
        }`}
      >
        {/* Role badge */}
        {!isUser && (
          <div className="flex items-center gap-2 mb-2">
            <div className="w-4 h-4 rounded-full bg-jay-accent/20 border border-jay-accent/40 flex items-center justify-center">
              <div className="w-1.5 h-1.5 rounded-full bg-jay-accent" />
            </div>
            <span className="text-[10px] font-mono text-jay-accent tracking-widest">J.A.Y.</span>
          </div>
        )}

        {/* Content */}
        {msg.isStreaming ? (
          <div className="prose prose-invert prose-sm max-w-none">
            <span>{msg.content}</span>
            <motion.span
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.6, repeat: Infinity }}
              className="inline-block w-0.5 h-4 bg-jay-accent ml-0.5 align-middle"
            />
          </div>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code: ({ node, className, children, ...props }: any) => {
                  const isBlock = className?.includes("language-");
                  return isBlock ? (
                    <pre className="bg-jay-bg border border-jay-border rounded-md p-3 overflow-x-auto my-2">
                      <code className={`font-mono text-xs text-jay-text ${className}`} {...props}>
                        {children}
                      </code>
                    </pre>
                  ) : (
                    <code className="bg-jay-bg/80 border border-jay-border/50 rounded px-1 py-0.5 font-mono text-xs text-jay-accent" {...props}>
                      {children}
                    </code>
                  );
                },
                pre: ({ children }) => <>{children}</>,
                p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
                ul: ({ children }) => <ul className="list-disc list-inside space-y-1 mb-2">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 mb-2">{children}</ol>,
                li: ({ children }) => <li className="text-jay-text/90">{children}</li>,
                h1: ({ children }) => <h1 className="text-lg font-bold text-jay-text mb-2">{children}</h1>,
                h2: ({ children }) => <h2 className="text-base font-semibold text-jay-accent mb-1.5">{children}</h2>,
                h3: ({ children }) => <h3 className="text-sm font-semibold text-jay-textDim mb-1">{children}</h3>,
                strong: ({ children }) => <strong className="text-jay-accent font-semibold">{children}</strong>,
                blockquote: ({ children }) => (
                  <blockquote className="border-l-2 border-jay-accent/50 pl-3 italic text-jay-textDim my-2">{children}</blockquote>
                ),
                table: ({ children }) => (
                  <div className="overflow-x-auto my-2">
                    <table className="text-xs border-collapse w-full">{children}</table>
                  </div>
                ),
                th: ({ children }) => (
                  <th className="border border-jay-border px-2 py-1 text-jay-accent font-semibold bg-jay-surface text-left">{children}</th>
                ),
                td: ({ children }) => (
                  <td className="border border-jay-border/50 px-2 py-1 text-jay-text/90">{children}</td>
                ),
              }}
            >
              {msg.content}
            </ReactMarkdown>
          </div>
        )}

        {/* Timestamp */}
        <div className="mt-1.5 text-[10px] text-jay-textMuted text-right">
          {msg.created_at ? new Date(msg.created_at).toLocaleTimeString() : "now"}
        </div>
      </div>
    </motion.div>
  );
}

const SUGGESTIONS = [
  "What can you do?",
  "Analyze RELIANCE stock",
  "Build a React todo app",
  "Search for latest AI news",
  "Show system status",
  "Remember that I prefer TypeScript",
];

export default function ChatPanel() {
  const {
    messages, isStreaming, activeConversationId, streamingContent,
    addMessage, setStreaming, setStreamingContent, appendStreamChunk,
    updateLastMessage, setActiveConversation, isListening, currentTranscript,
  } = useStore();

  const [input, setInput] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  // Auto-fill from voice transcript
  useEffect(() => {
    if (currentTranscript) {
      setInput(currentTranscript);
    }
  }, [currentTranscript]);

  const handleSend = useCallback(async (text?: string) => {
    const msg = (text || input).trim();
    if (!msg || isStreaming) return;

    setInput("");
    const convId = activeConversationId || genId();
    if (!activeConversationId) setActiveConversation(convId);

    // Add user message
    addMessage({ id: genId(), role: "user", content: msg, created_at: new Date().toISOString() });

    // Add streaming placeholder
    const assistantId = genId();
    addMessage({ id: assistantId, role: "assistant", content: "", created_at: new Date().toISOString(), isStreaming: true });

    setStreaming(true);
    setStreamingContent("");

    let fullContent = "";
    try {
      for await (const chunk of chatAPI.streamMessage(msg, convId)) {
        fullContent += chunk;
        appendStreamChunk(chunk);
        // Update the streaming message
        useStore.getState().updateLastMessage(fullContent);
      }
    } catch (e: any) {
      updateLastMessage(`*Error: ${e.message}. Make sure the backend is running.*`);
    } finally {
      setStreaming(false);
      setStreamingContent("");
      if (fullContent) updateLastMessage(fullContent);
    }
  }, [input, isStreaming, activeConversationId]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const startVoice = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      const chunks: BlobPart[] = [];
      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());
        const { voiceAPI } = await import("@/lib/api");
        const result = await voiceAPI.transcribe(blob);
        if (result.text) {
          setInput(result.text);
          handleSend(result.text);
        }
        setIsRecording(false);
      };
      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
    } catch (e) {
      console.error("Mic access denied:", e);
    }
  };

  const stopVoice = () => {
    mediaRecorder?.stop();
    setIsRecording(false);
  };

  const newConversation = () => {
    setActiveConversation(genId());
    useStore.getState().setMessages([]);
  };

  return (
    <div className="flex flex-col h-full bg-jay-bg">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-jay-border/50">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-jay-accent animate-pulse" />
          <span className="text-xs font-mono text-jay-textDim tracking-widest">CONVERSATION</span>
        </div>
        <button
          onClick={newConversation}
          className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono text-jay-textDim hover:text-jay-accent border border-jay-border/40 hover:border-jay-accent/40 rounded transition-colors"
        >
          <Plus size={11} /> NEW
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scrollbar-thin scrollbar-thumb-jay-border scrollbar-track-transparent">
        {messages.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center h-full gap-6 py-12"
          >
            <div className="text-center">
              <div className="text-2xl font-display font-bold text-jay-text mb-1">J.A.Y.</div>
              <div className="text-sm text-jay-textDim">Just Assists You</div>
            </div>
            <div className="grid grid-cols-2 gap-2 max-w-md w-full">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handleSend(s)}
                  className="group flex items-center gap-2 px-3 py-2.5 text-left text-xs text-jay-textDim hover:text-jay-text border border-jay-border/40 hover:border-jay-accent/40 rounded-lg bg-jay-surface/30 hover:bg-jay-surface/60 transition-all"
                >
                  <ChevronRight size={10} className="text-jay-accent/50 group-hover:text-jay-accent flex-shrink-0" />
                  {s}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Voice visualizer (when active) */}
      {(isRecording || isListening) && (
        <div className="px-4 py-2 border-t border-jay-border/30">
          <VoiceVisualizer height={40} />
        </div>
      )}

      {/* Input */}
      <div className="px-4 py-3 border-t border-jay-border/50">
        <div className="flex items-end gap-2 bg-jay-surface border border-jay-border/60 hover:border-jay-accent/40 rounded-xl p-2 transition-colors focus-within:border-jay-accent/60">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask J.A.Y. anything…"
            rows={1}
            disabled={isStreaming}
            className="flex-1 bg-transparent resize-none text-sm text-jay-text placeholder-jay-textMuted outline-none min-h-[24px] max-h-32 py-1 px-2 scrollbar-thin scrollbar-thumb-jay-border"
            style={{ lineHeight: "1.5" }}
            onInput={(e) => {
              const t = e.currentTarget;
              t.style.height = "auto";
              t.style.height = Math.min(t.scrollHeight, 128) + "px";
            }}
          />

          {/* Voice button */}
          <button
            onClick={isRecording ? stopVoice : startVoice}
            disabled={isStreaming}
            className={`p-2 rounded-lg transition-all ${
              isRecording
                ? "bg-red-500/20 border border-red-500/50 text-red-400"
                : "text-jay-textDim hover:text-jay-accent hover:bg-jay-accent/10 border border-transparent hover:border-jay-accent/30"
            }`}
          >
            {isRecording ? (
              <motion.div animate={{ scale: [1, 1.2, 1] }} transition={{ duration: 0.8, repeat: Infinity }}>
                <MicOff size={16} />
              </motion.div>
            ) : (
              <Mic size={16} />
            )}
          </button>

          {/* Send button */}
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isStreaming}
            className="p-2 rounded-lg bg-jay-accent/10 border border-jay-accent/30 text-jay-accent hover:bg-jay-accent/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
          >
            {isStreaming ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                className="w-4 h-4 border-2 border-jay-accent border-t-transparent rounded-full"
              />
            ) : (
              <Send size={16} />
            )}
          </button>
        </div>
        <div className="mt-1.5 px-2 text-[10px] text-jay-textMuted font-mono">
          Enter to send · Shift+Enter for new line · Click mic for voice
        </div>
      </div>
    </div>
  );
}
