"use client";

import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { Terminal, ChevronRight, Trash2 } from "lucide-react";
import { toolsAPI } from "@/lib/api";

interface TerminalLine {
  type: "input" | "output" | "error" | "info";
  content: string;
  ts: string;
}

const INITIAL_LINES: TerminalLine[] = [
  { type: "info", content: "J.A.Y. Terminal v0.1.0", ts: new Date().toISOString() },
  { type: "info", content: 'Type "help" for available commands', ts: new Date().toISOString() },
  { type: "info", content: "─────────────────────────────────────", ts: new Date().toISOString() },
];

export default function TerminalPanel() {
  const [lines, setLines] = useState<TerminalLine[]>(INITIAL_LINES);
  const [input, setInput] = useState("");
  const [cwd, setCwd] = useState("~");
  const [history, setHistory] = useState<string[]>([]);
  const [histIdx, setHistIdx] = useState(-1);
  const [running, setRunning] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  const addLine = (type: TerminalLine["type"], content: string) => {
    setLines((l) => [...l, { type, content, ts: new Date().toISOString() }]);
  };

  const runCommand = async (cmd: string) => {
    if (!cmd.trim()) return;
    const trimmed = cmd.trim();

    addLine("input", `${cwd} $ ${trimmed}`);
    setHistory((h) => [trimmed, ...h.slice(0, 49)]);
    setHistIdx(-1);
    setInput("");
    setRunning(true);

    try {
      // Built-in commands
      if (trimmed === "help") {
        const helpText = [
          "Available commands:",
          "  cd <path>       — Change directory",
          "  ls [path]       — List directory",
          "  cat <file>      — Read file",
          "  clear           — Clear terminal",
          "  sysinfo         — System information",
          "  apps            — List running applications",
          "  Any shell command is executed directly",
        ];
        helpText.forEach((l) => addLine("output", l));
        setRunning(false);
        return;
      }

      if (trimmed === "clear") {
        setLines(INITIAL_LINES);
        setRunning(false);
        return;
      }

      if (trimmed === "sysinfo") {
        const result = await toolsAPI.execute("get_system_info", {});
        if (result.success) {
          const info = result.output;
          addLine("output", `OS: ${info.os}`);
          addLine("output", `CPU: ${info.cpu_percent}% (${info.cpu_cores} cores)`);
          addLine("output", `RAM: ${info.ram_used_gb}GB / ${info.ram_total_gb}GB (${info.ram_percent}%)`);
          addLine("output", `Disk: ${info.disk_used_gb}GB / ${info.disk_total_gb}GB (${info.disk_percent}%)`);
        }
        setRunning(false);
        return;
      }

      if (trimmed === "apps") {
        const result = await toolsAPI.execute("list_running_apps", {});
        if (result.success) {
          const apps = result.output.slice(0, 10);
          apps.forEach((a: any) => addLine("output", `${a.name.padEnd(30)} ${a.memory_mb}MB`));
        }
        setRunning(false);
        return;
      }

      if (trimmed.startsWith("ls")) {
        const path = trimmed.replace("ls", "").trim() || cwd;
        const result = await toolsAPI.execute("list_directory", { path: path === "~" ? "~" : path });
        if (result.success) {
          result.output.forEach((item: any) => {
            const icon = item.type === "directory" ? "📁" : "📄";
            const size = item.size ? ` (${(item.size / 1024).toFixed(1)}KB)` : "";
            addLine("output", `${icon} ${item.name}${size}`);
          });
        } else {
          addLine("error", result.error || "Error");
        }
        setRunning(false);
        return;
      }

      if (trimmed.startsWith("cat ")) {
        const file = trimmed.slice(4).trim();
        const result = await toolsAPI.execute("read_file", { path: file });
        if (result.success) {
          result.output.split("\n").slice(0, 100).forEach((l: string) => addLine("output", l));
        } else {
          addLine("error", result.error || "Cannot read file");
        }
        setRunning(false);
        return;
      }

      if (trimmed.startsWith("cd ")) {
        const path = trimmed.slice(3).trim();
        setCwd(path === "~" ? "~" : path);
        addLine("output", `Changed to: ${path}`);
        setRunning(false);
        return;
      }

      // Generic shell command
      const result = await toolsAPI.execute("run_terminal_command", {
        command: trimmed,
        cwd: cwd === "~" ? undefined : cwd,
      });

      if (result.blocked) {
        addLine("error", `⛔ Blocked: ${result.error}`);
      } else if (result.success) {
        const output = String(result.output || "");
        output.split("\n").forEach((l: string) => addLine("output", l));
      } else {
        const err = String(result.error || result.output || "Command failed");
        err.split("\n").forEach((l: string) => addLine("error", l));
      }
    } catch (e: any) {
      addLine("error", `Error: ${e.message}`);
    } finally {
      setRunning(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      runCommand(input);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const newIdx = Math.min(histIdx + 1, history.length - 1);
      setHistIdx(newIdx);
      setInput(history[newIdx] || "");
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      const newIdx = Math.max(histIdx - 1, -1);
      setHistIdx(newIdx);
      setInput(newIdx === -1 ? "" : history[newIdx] || "");
    }
  };

  const lineColor: Record<TerminalLine["type"], string> = {
    input: "#00d4ff",
    output: "#e2f0ff",
    error: "#ef4444",
    info: "#7ea8cc",
  };

  return (
    <div className="flex flex-col h-full bg-jay-bg rounded-lg overflow-hidden font-mono">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-jay-border/40 bg-jay-surface/30">
        <div className="flex items-center gap-2">
          <Terminal size={13} className="text-jay-accent" />
          <span className="text-[11px] text-jay-textDim tracking-widest">TERMINAL</span>
          <span className="text-[10px] text-jay-textMuted">{cwd}</span>
        </div>
        <div className="flex items-center gap-2">
          {running && (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
              className="w-3 h-3 border border-jay-accent/60 border-t-transparent rounded-full"
            />
          )}
          <button
            onClick={() => setLines(INITIAL_LINES)}
            className="text-jay-textMuted hover:text-jay-red transition-colors"
          >
            <Trash2 size={12} />
          </button>
        </div>
      </div>

      {/* Output */}
      <div
        className="flex-1 overflow-y-auto px-4 py-3 space-y-0.5 cursor-text text-sm leading-relaxed"
        onClick={() => inputRef.current?.focus()}
      >
        {lines.map((line, i) => (
          <div key={i} style={{ color: lineColor[line.type] }} className="whitespace-pre-wrap break-all">
            {line.content}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="flex items-center gap-2 px-4 py-2 border-t border-jay-border/40 bg-jay-surface/20">
        <span className="text-jay-accent text-sm flex-shrink-0">{cwd} $</span>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={running}
          placeholder={running ? "Running…" : "Enter command…"}
          autoFocus
          className="flex-1 bg-transparent text-sm text-jay-text placeholder-jay-textMuted outline-none"
        />
        {running && (
          <motion.div
            animate={{ opacity: [1, 0] }}
            transition={{ duration: 0.5, repeat: Infinity }}
            className="w-0.5 h-4 bg-jay-accent"
          />
        )}
      </div>
    </div>
  );
}
