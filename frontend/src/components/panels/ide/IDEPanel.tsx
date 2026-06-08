"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FolderOpen, FileText, ChevronRight, ChevronDown, X, Save,
  RefreshCw, Send, Bot, Folder, File, FolderPlus, FilePlus,
  Code2, Eye, MessageSquare, GitBranch, AlertCircle,
} from "lucide-react";
import { toolsAPI, chatAPI } from "@/lib/api";
import type { FSEntry, OpenTab } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Language detection ────────────────────────────────────────────────────────

function detectLanguage(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  const map: Record<string, string> = {
    ts: "typescript", tsx: "typescript", js: "javascript", jsx: "javascript",
    py: "python", rs: "rust", go: "go", java: "java", cpp: "cpp", c: "c",
    css: "css", scss: "scss", html: "html", json: "json", yaml: "yaml",
    yml: "yaml", md: "markdown", sh: "bash", bash: "bash", toml: "toml",
    sql: "sql", rb: "ruby", php: "php", swift: "swift", kt: "kotlin",
    env: "ini", gitignore: "ini", dockerfile: "dockerfile",
  };
  return map[ext] ?? "plaintext";
}

function fileIcon(name: string) {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  const colors: Record<string, string> = {
    ts: "#3178c6", tsx: "#3178c6", js: "#f7df1e", jsx: "#61dafb",
    py: "#3776ab", rs: "#f74c00", go: "#00add8", json: "#f97316",
    md: "#7ea8cc", css: "#264de4", html: "#e34c26", sh: "#22c55e",
    toml: "#9c4221", yaml: "#cc3e44", yml: "#cc3e44",
  };
  return colors[ext] ?? "#7ea8cc";
}

// ── Syntax highlighting (basic token coloring) ────────────────────────────────

function highlight(code: string, lang: string): string {
  if (lang === "plaintext" || lang === "markdown") return escHtml(code);
  let s = escHtml(code);

  // Keywords
  const kw = {
    python:     /\b(def|class|import|from|return|if|elif|else|for|while|with|as|try|except|finally|pass|break|continue|lambda|yield|async|await|True|False|None|and|or|not|in|is)\b/g,
    typescript: /\b(const|let|var|function|class|interface|type|import|export|from|return|if|else|for|while|do|switch|case|break|continue|new|this|extends|implements|async|await|void|null|undefined|true|false|typeof|keyof)\b/g,
    javascript: /\b(const|let|var|function|class|import|export|from|return|if|else|for|while|do|switch|case|break|continue|new|this|async|await|null|undefined|true|false|typeof)\b/g,
    rust:       /\b(fn|let|mut|use|mod|pub|struct|enum|impl|trait|for|while|loop|if|else|match|return|self|Self|async|await|move|ref|const|static)\b/g,
    go:         /\b(func|var|const|type|struct|interface|import|package|return|if|else|for|range|switch|case|go|defer|chan|map|make|new|nil|true|false)\b/g,
  } as Record<string, RegExp>;

  const kwRe = kw[lang];
  if (kwRe) s = s.replace(kwRe, '<span class="c-kw">$1</span>');

  // Strings
  s = s.replace(/(&#39;[^&#]*&#39;|&quot;[^&quot;]*&quot;|`[^`]*`)/g, '<span class="c-str">$1</span>');

  // Numbers
  s = s.replace(/\b(\d+\.?\d*)\b/g, '<span class="c-num">$1</span>');

  // Comments
  s = s.replace(/(\/\/[^\n]*|#[^\n]*)/g, '<span class="c-cmt">$1</span>');

  return s;
}

function escHtml(s: string) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

// ── File tree node ─────────────────────────────────────────────────────────────

function TreeNode({
  entry,
  depth,
  onOpen,
  onToggle,
}: {
  entry: FSEntry;
  depth: number;
  onOpen: (e: FSEntry) => void;
  onToggle: (e: FSEntry) => void;
}) {
  const isDir = entry.type === "directory";
  const indent = depth * 12;
  const color = isDir ? "#7ea8cc" : fileIcon(entry.name);

  return (
    <div>
      <button
        onClick={() => (isDir ? onToggle(entry) : onOpen(entry))}
        className="w-full flex items-center gap-1.5 px-2 py-0.5 hover:bg-jay-surface/60 rounded text-left group"
        style={{ paddingLeft: 8 + indent }}
      >
        {isDir ? (
          entry.isOpen
            ? <ChevronDown size={11} className="text-jay-textMuted flex-shrink-0" />
            : <ChevronRight size={11} className="text-jay-textMuted flex-shrink-0" />
        ) : (
          <span className="w-3 flex-shrink-0" />
        )}
        {isDir
          ? <Folder size={13} style={{ color: "#e6b800" }} className="flex-shrink-0" />
          : <File   size={13} style={{ color }}           className="flex-shrink-0" />}
        <span className="text-[11px] font-mono text-jay-textDim group-hover:text-jay-text truncate">
          {entry.name}
        </span>
      </button>

      {isDir && entry.isOpen && entry.children && (
        <div>
          {entry.children.map((child) => (
            <TreeNode key={child.path} entry={child} depth={depth + 1} onOpen={onOpen} onToggle={onToggle} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Code editor with line numbers ─────────────────────────────────────────────

function CodeEditor({
  tab,
  onChange,
}: {
  tab: OpenTab;
  onChange: (content: string) => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const preRef = useRef<HTMLPreElement>(null);
  const lines = tab.content.split("\n");

  // Sync scroll between textarea and highlight overlay
  const syncScroll = () => {
    if (textareaRef.current && preRef.current) {
      preRef.current.scrollTop  = textareaRef.current.scrollTop;
      preRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  };

  const handleTab = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const el = e.currentTarget;
      const start = el.selectionStart;
      const end   = el.selectionEnd;
      const next  = tab.content.substring(0, start) + "  " + tab.content.substring(end);
      onChange(next);
      requestAnimationFrame(() => {
        el.selectionStart = el.selectionEnd = start + 2;
      });
    }
  };

  const highlighted = highlight(tab.content, tab.language);

  return (
    <div className="flex-1 flex overflow-hidden font-mono text-xs">
      {/* Line numbers */}
      <div className="flex-shrink-0 w-10 bg-jay-bg/80 border-r border-jay-border/30 overflow-hidden select-none">
        <div className="pt-3 pb-3">
          {lines.map((_, i) => (
            <div key={i} className="text-right pr-2 leading-5 text-jay-textMuted/40 text-[10px]">
              {i + 1}
            </div>
          ))}
        </div>
      </div>

      {/* Editor area — stacked textarea + highlight pre */}
      <div className="flex-1 relative overflow-hidden">
        {/* Syntax highlight overlay (pointer-events:none) */}
        <pre
          ref={preRef}
          aria-hidden="true"
          className="absolute inset-0 p-3 leading-5 overflow-auto pointer-events-none whitespace-pre text-[12px] text-jay-text"
          style={{ tabSize: 2 }}
          dangerouslySetInnerHTML={{ __html: highlighted }}
        />

        {/* Actual textarea (transparent text so highlight shows through) */}
        <textarea
          ref={textareaRef}
          value={tab.content}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleTab}
          onScroll={syncScroll}
          spellCheck={false}
          className="absolute inset-0 w-full h-full p-3 leading-5 bg-transparent resize-none outline-none text-transparent caret-jay-accent text-[12px] selection:bg-jay-accent/20"
          style={{ tabSize: 2 }}
        />
      </div>

      <style jsx global>{`
        .c-kw  { color: #c792ea; }
        .c-str { color: #c3e88d; }
        .c-num { color: #f78c6c; }
        .c-cmt { color: #546e7a; font-style: italic; }
      `}</style>
    </div>
  );
}

// ── J.A.Y. file chat ──────────────────────────────────────────────────────────

function FileChat({ tab }: { tab: OpenTab | null }) {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");

    const fileCtx = tab
      ? `\n\nContext — file: ${tab.path}\n\`\`\`${tab.language}\n${tab.content.slice(0, 8000)}\n\`\`\``
      : "";

    const fullMsg = q + fileCtx;
    setMessages((m) => [...m, { role: "user", content: q }]);
    setLoading(true);

    let reply = "";
    try {
      for await (const chunk of chatAPI.streamMessage(fullMsg)) {
        reply += chunk;
        setMessages((m) => {
          const last = m[m.length - 1];
          if (last?.role === "assistant") {
            return [...m.slice(0, -1), { role: "assistant", content: reply }];
          }
          return [...m, { role: "assistant", content: reply }];
        });
      }
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", content: `Error: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b border-jay-border/30 flex items-center gap-2">
        <Bot size={13} className="text-jay-accent" />
        <span className="text-[10px] font-mono text-jay-textDim tracking-widest">J.A.Y. ASSISTANT</span>
        {tab && (
          <span className="text-[9px] font-mono text-jay-textMuted ml-auto truncate max-w-[120px]">
            ctx: {tab.name}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {messages.length === 0 && (
          <div className="text-[11px] text-jay-textMuted text-center mt-6 px-2 leading-relaxed">
            {tab
              ? `Ask me anything about ${tab.name} — I can review, debug, explain, or refactor it.`
              : "Open a file and ask me about it."}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`text-[11px] rounded-lg px-2.5 py-2 ${
            m.role === "user"
              ? "bg-jay-accent/10 border border-jay-accent/20 text-jay-text ml-4"
              : "bg-jay-surface/40 border border-jay-border/20 text-jay-textDim mr-4"
          }`}>
            <div className="text-[9px] font-mono mb-1 text-jay-textMuted">
              {m.role === "user" ? "YOU" : "J.A.Y."}
            </div>
            <div className="whitespace-pre-wrap leading-relaxed">{m.content}</div>
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-1.5 px-2 text-[11px] text-jay-textMuted">
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
              className="w-3 h-3 border border-jay-accent border-t-transparent rounded-full" />
            Thinking…
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="p-2 border-t border-jay-border/30 flex gap-1.5">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="Ask about this file…"
          className="flex-1 bg-jay-surface/50 border border-jay-border/40 rounded-lg px-2.5 py-1.5 text-[11px] text-jay-text placeholder-jay-textMuted outline-none focus:border-jay-accent/50"
        />
        <button
          onClick={send}
          disabled={!input.trim() || loading}
          className="p-1.5 bg-jay-accent/10 border border-jay-accent/30 text-jay-accent rounded-lg hover:bg-jay-accent/20 disabled:opacity-30 transition-colors"
        >
          <Send size={12} />
        </button>
      </div>
    </div>
  );
}

// ── Main IDE panel ────────────────────────────────────────────────────────────

export default function IDEPanel() {
  const [rootPath, setRootPath]   = useState("");
  const [tree, setTree]           = useState<FSEntry[]>([]);
  const [tabs, setTabs]           = useState<OpenTab[]>([]);
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [chatOpen, setChatOpen]   = useState(true);
  const [saving, setSaving]       = useState(false);
  const [loadingDir, setLoadingDir] = useState(false);

  const currentTab = tabs.find((t) => t.path === activeTab) ?? null;

  // ── Load directory ──────────────────────────────────────────────────────────

  const loadDir = useCallback(async (path: string) => {
    if (!path.trim()) return;
    setLoadingDir(true);
    try {
      const res = await toolsAPI.execute("list_directory", { path }, true);
      if (!res.success) { alert(res.error); return; }
      const entries: FSEntry[] = (res.output ?? []).map((item: any) => ({
        name:     item.name,
        path:     path.replace(/\/$/, "") + "/" + item.name,
        type:     item.type === "directory" ? "directory" : "file",
        size:     item.size,
        modified: item.modified,
        children: item.type === "directory" ? [] : undefined,
        isOpen:   false,
      }));
      setTree(entries);
    } finally {
      setLoadingDir(false);
    }
  }, []);

  // ── Toggle directory ────────────────────────────────────────────────────────

  const toggleDir = useCallback(async (entry: FSEntry) => {
    const expand = !entry.isOpen;

    const updateTree = (nodes: FSEntry[]): FSEntry[] =>
      nodes.map((n) => {
        if (n.path === entry.path) {
          return { ...n, isOpen: expand };
        }
        if (n.children) return { ...n, children: updateTree(n.children) };
        return n;
      });

    setTree((t) => updateTree(t));

    // Load children if expanding and empty
    if (expand && (!entry.children || entry.children.length === 0)) {
      const res = await toolsAPI.execute("list_directory", { path: entry.path }, true);
      if (!res.success) return;
      const children: FSEntry[] = (res.output ?? []).map((item: any) => ({
        name:     item.name,
        path:     entry.path + "/" + item.name,
        type:     item.type === "directory" ? "directory" : "file",
        size:     item.size,
        modified: item.modified,
        children: item.type === "directory" ? [] : undefined,
        isOpen:   false,
      }));

      const withChildren = (nodes: FSEntry[]): FSEntry[] =>
        nodes.map((n) => {
          if (n.path === entry.path) return { ...n, children };
          if (n.children) return { ...n, children: withChildren(n.children) };
          return n;
        });

      setTree((t) => withChildren(t));
    }
  }, []);

  // ── Open file ────────────────────────────────────────────────────────────────

  const openFile = useCallback(async (entry: FSEntry) => {
    // Already open?
    if (tabs.find((t) => t.path === entry.path)) {
      setActiveTab(entry.path);
      return;
    }
    const res = await toolsAPI.execute("read_file", { path: entry.path }, true);
    if (!res.success) { alert(res.error); return; }
    const content = res.output ?? "";
    const lang    = detectLanguage(entry.name);
    const tab: OpenTab = {
      path:            entry.path,
      name:            entry.name,
      content,
      language:        lang,
      isDirty:         false,
      originalContent: content,
    };
    setTabs((t) => [...t, tab]);
    setActiveTab(entry.path);
  }, [tabs]);

  // ── Edit file ────────────────────────────────────────────────────────────────

  const editFile = (path: string, content: string) => {
    setTabs((t) =>
      t.map((tab) =>
        tab.path === path
          ? { ...tab, content, isDirty: content !== tab.originalContent }
          : tab
      )
    );
  };

  // ── Save file ────────────────────────────────────────────────────────────────

  const saveFile = async () => {
    if (!currentTab) return;
    setSaving(true);
    const res = await toolsAPI.execute("write_file", {
      path:    currentTab.path,
      content: currentTab.content,
    }, true);
    if (res.success) {
      setTabs((t) =>
        t.map((tab) =>
          tab.path === currentTab.path
            ? { ...tab, isDirty: false, originalContent: currentTab.content }
            : tab
        )
      );
    } else {
      alert("Save failed: " + res.error);
    }
    setSaving(false);
  };

  // ── Close tab ────────────────────────────────────────────────────────────────

  const closeTab = (path: string) => {
    const idx  = tabs.findIndex((t) => t.path === path);
    const next = tabs.filter((t) => t.path !== path);
    setTabs(next);
    if (activeTab === path) {
      setActiveTab(next[Math.max(0, idx - 1)]?.path ?? null);
    }
  };

  // ── Keyboard shortcut Ctrl+S ──────────────────────────────────────────────

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        saveFile();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [currentTab]);

  return (
    <div className="flex flex-col h-full gap-0 bg-jay-bg font-mono">

      {/* ── Toolbar ──────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-jay-border/40 bg-jay-surface/10 flex-shrink-0">
        <Code2 size={13} className="text-jay-accent flex-shrink-0" />
        <span className="text-[10px] font-mono text-jay-textDim tracking-widest mr-2">IDE</span>

        <input
          value={rootPath}
          onChange={(e) => setRootPath(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && loadDir(rootPath)}
          placeholder="Enter folder path  e.g. C:\Users\Jay\project  or  ~/project"
          className="flex-1 bg-jay-surface border border-jay-border/50 rounded-lg px-3 py-1 text-[11px] text-jay-text placeholder-jay-textMuted outline-none focus:border-jay-accent/50"
        />
        <button
          onClick={() => loadDir(rootPath)}
          disabled={loadingDir}
          className="flex items-center gap-1.5 px-2.5 py-1 bg-jay-accent/10 border border-jay-accent/30 text-jay-accent hover:bg-jay-accent/20 rounded-lg text-[11px] transition-colors disabled:opacity-50"
        >
          {loadingDir
            ? <RefreshCw size={11} className="animate-spin" />
            : <FolderOpen size={11} />}
          OPEN
        </button>

        {currentTab && (
          <>
            <div className="h-4 w-px bg-jay-border/50" />
            <button
              onClick={saveFile}
              disabled={saving || !currentTab.isDirty}
              className="flex items-center gap-1.5 px-2.5 py-1 bg-jay-green/10 border border-jay-green/30 text-jay-green hover:bg-jay-green/20 rounded-lg text-[11px] transition-colors disabled:opacity-40"
              title="Save (Ctrl+S)"
            >
              {saving ? <RefreshCw size={11} className="animate-spin" /> : <Save size={11} />}
              SAVE
            </button>
          </>
        )}

        <button
          onClick={() => setChatOpen((v) => !v)}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] border transition-colors ml-auto ${
            chatOpen
              ? "bg-jay-accent/10 border-jay-accent/30 text-jay-accent"
              : "border-jay-border/30 text-jay-textDim hover:border-jay-border"
          }`}
        >
          <MessageSquare size={11} />
          J.A.Y.
        </button>
      </div>

      {/* ── Main work area ───────────────────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">

        {/* ── File tree ────────────────────────────────────────────────────── */}
        <div className="w-48 flex-shrink-0 border-r border-jay-border/40 flex flex-col overflow-hidden bg-jay-bg/60">
          <div className="flex items-center justify-between px-3 py-1.5 border-b border-jay-border/30">
            <span className="text-[9px] font-mono text-jay-textMuted tracking-widest uppercase">Explorer</span>
          </div>
          <div className="flex-1 overflow-y-auto py-1">
            {tree.length === 0 ? (
              <div className="text-[10px] text-jay-textMuted text-center mt-8 px-3 leading-relaxed">
                Enter a folder path above and click OPEN to browse your files
              </div>
            ) : (
              tree.map((entry) => (
                <TreeNode
                  key={entry.path}
                  entry={entry}
                  depth={0}
                  onOpen={openFile}
                  onToggle={toggleDir}
                />
              ))
            )}
          </div>
        </div>

        {/* ── Editor area ──────────────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col overflow-hidden">

          {/* Tab bar */}
          {tabs.length > 0 && (
            <div className="flex items-end gap-0 overflow-x-auto border-b border-jay-border/40 bg-jay-surface/10 flex-shrink-0">
              {tabs.map((tab) => (
                <button
                  key={tab.path}
                  onClick={() => setActiveTab(tab.path)}
                  className={`flex items-center gap-2 px-3 py-2 text-[11px] border-r border-jay-border/30 transition-colors whitespace-nowrap group flex-shrink-0 ${
                    activeTab === tab.path
                      ? "bg-jay-bg text-jay-text border-t-2 border-t-jay-accent"
                      : "text-jay-textMuted hover:text-jay-textDim hover:bg-jay-surface/30"
                  }`}
                >
                  <File size={11} style={{ color: fileIcon(tab.name) }} />
                  <span className="font-mono">{tab.name}</span>
                  {tab.isDirty && (
                    <span className="w-1.5 h-1.5 rounded-full bg-jay-orange flex-shrink-0" title="Unsaved changes" />
                  )}
                  <span
                    onClick={(e) => { e.stopPropagation(); closeTab(tab.path); }}
                    className="opacity-0 group-hover:opacity-100 ml-0.5 text-jay-textMuted hover:text-jay-red transition-all"
                  >
                    <X size={10} />
                  </span>
                </button>
              ))}
            </div>
          )}

          {/* Editor / empty state */}
          {currentTab ? (
            <div className="flex-1 flex overflow-hidden bg-jay-bg">
              <CodeEditor tab={currentTab} onChange={(c) => editFile(currentTab.path, c)} />
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center gap-4 text-center bg-jay-bg">
              <div className="w-14 h-14 rounded-2xl bg-jay-surface/30 border border-jay-border/30 flex items-center justify-center">
                <Code2 size={24} className="text-jay-textMuted/50" />
              </div>
              <div>
                <div className="text-sm font-mono text-jay-textDim">No file open</div>
                <div className="text-xs text-jay-textMuted mt-1">
                  Open a folder above, then click any file to edit it
                </div>
              </div>
              <div className="flex flex-wrap gap-2 justify-center max-w-xs">
                {["Review this file", "Fix bugs", "Add comments", "Refactor", "Write tests"].map((s) => (
                  <span key={s} className="text-[10px] font-mono px-2 py-1 border border-jay-border/30 text-jay-textMuted rounded-lg">
                    "{s}"
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Status bar */}
          {currentTab && (
            <div className="flex items-center gap-4 px-3 py-1 border-t border-jay-border/30 bg-jay-surface/10 text-[9px] font-mono text-jay-textMuted flex-shrink-0">
              <span style={{ color: fileIcon(currentTab.name) }}>{currentTab.language}</span>
              <span>{currentTab.content.split("\n").length} lines</span>
              <span>{currentTab.content.length} chars</span>
              {currentTab.isDirty && (
                <span className="text-jay-orange flex items-center gap-1">
                  <AlertCircle size={9} /> unsaved
                </span>
              )}
              <span className="ml-auto truncate max-w-[300px] text-jay-textMuted/60">{currentTab.path}</span>
            </div>
          )}
        </div>

        {/* ── J.A.Y. chat panel ─────────────────────────────────────────────── */}
        <AnimatePresence>
          {chatOpen && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 260, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="flex-shrink-0 border-l border-jay-border/40 overflow-hidden"
            >
              <FileChat tab={currentTab} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
