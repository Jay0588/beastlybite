"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Plus, Trash2, Brain, RefreshCw } from "lucide-react";
import { memoryAPI } from "@/lib/api";

const CATEGORIES = ["all", "fact", "preference", "habit", "project", "lesson", "research", "contact"];
const NAMESPACES = ["general", "conversations", "projects", "trading", "research", "code"];

function MemoryCard({ memory, onDelete }: { memory: any; onDelete: () => void }) {
  const cat = memory.metadata?.category || "fact";
  const catColor: Record<string, string> = {
    fact: "#00d4ff", preference: "#a855f7", habit: "#22c55e",
    project: "#f97316", lesson: "#fbbf24", research: "#06b6d4",
    contact: "#ec4899",
  };
  const color = catColor[cat] || "#00d4ff";

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="group relative bg-jay-surface/30 border border-jay-border/30 hover:border-jay-accent/30 rounded-xl p-3 transition-all"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span
              className="text-[9px] font-mono px-1.5 py-0.5 rounded border uppercase tracking-wider"
              style={{ color, borderColor: color + "44", background: color + "11" }}
            >
              {cat}
            </span>
            {memory.score !== undefined && (
              <span className="text-[9px] font-mono text-jay-textMuted">
                {(memory.score * 100).toFixed(0)}% match
              </span>
            )}
          </div>
          <p className="text-xs text-jay-text leading-relaxed">{memory.content}</p>
          {memory.metadata?.timestamp && (
            <div className="text-[10px] text-jay-textMuted mt-1.5">
              {new Date(memory.metadata.timestamp).toLocaleDateString()}
            </div>
          )}
        </div>
        <button
          onClick={onDelete}
          className="opacity-0 group-hover:opacity-100 p-1 text-jay-textMuted hover:text-jay-red transition-all flex-shrink-0"
        >
          <Trash2 size={12} />
        </button>
      </div>
    </motion.div>
  );
}

export default function MemoryPanel() {
  const [memories, setMemories] = useState<any[]>([]);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [query, setQuery] = useState("");
  const [activeNs, setActiveNs] = useState("general");
  const [activeCat, setActiveCat] = useState("all");
  const [loading, setLoading] = useState(false);
  const [newMemory, setNewMemory] = useState("");
  const [newCat, setNewCat] = useState("fact");

  const loadMemories = async () => {
    setLoading(true);
    try {
      if (query.trim()) {
        const result = await memoryAPI.search(query, activeNs, 20);
        setMemories(result.results || []);
      } else {
        const result = await memoryAPI.getAll(activeNs, activeCat === "all" ? undefined : activeCat);
        setMemories(result.memories || []);
      }
      const s = await memoryAPI.getStats();
      setStats(s.namespaces || {});
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadMemories(); }, [activeNs, activeCat]);

  const handleSearch = async () => { loadMemories(); };

  const handleStore = async () => {
    if (!newMemory.trim()) return;
    await memoryAPI.store(newMemory, newCat, activeNs);
    setNewMemory("");
    loadMemories();
  };

  const handleDelete = async (id: string) => {
    await memoryAPI.delete(id, activeNs);
    setMemories((m) => m.filter((x) => x.id !== id));
  };

  return (
    <div className="flex flex-col h-full gap-3">
      {/* Stats bar */}
      <div className="grid grid-cols-6 gap-2">
        {NAMESPACES.map((ns) => (
          <button
            key={ns}
            onClick={() => setActiveNs(ns)}
            className={`p-2 rounded-lg border text-center transition-all ${
              activeNs === ns
                ? "bg-jay-accent/10 border-jay-accent/40 text-jay-accent"
                : "bg-jay-surface/20 border-jay-border/30 text-jay-textDim hover:border-jay-border"
            }`}
          >
            <div className="text-sm font-mono font-bold">{stats[ns] || 0}</div>
            <div className="text-[9px] tracking-wider mt-0.5">{ns.toUpperCase()}</div>
          </button>
        ))}
      </div>

      {/* Search & add */}
      <div className="flex gap-2">
        <div className="flex-1 flex gap-2 bg-jay-surface border border-jay-border/50 rounded-lg px-3 py-2 focus-within:border-jay-accent/50">
          <Search size={14} className="text-jay-textMuted flex-shrink-0 mt-0.5" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Search memories semantically…"
            className="flex-1 bg-transparent text-sm text-jay-text placeholder-jay-textMuted outline-none"
          />
        </div>
        <button
          onClick={loadMemories}
          className="p-2 text-jay-textDim hover:text-jay-accent border border-jay-border/40 hover:border-jay-accent/40 rounded-lg transition-colors"
        >
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Category filter */}
      <div className="flex gap-1 flex-wrap">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCat(cat)}
            className={`px-2 py-0.5 text-[10px] font-mono rounded transition-all ${
              activeCat === cat
                ? "bg-jay-accent/15 text-jay-accent border border-jay-accent/30"
                : "text-jay-textMuted hover:text-jay-textDim"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Add memory */}
      <div className="flex gap-2">
        <input
          value={newMemory}
          onChange={(e) => setNewMemory(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleStore()}
          placeholder="Add a memory…"
          className="flex-1 bg-jay-surface border border-jay-border/50 rounded-lg px-3 py-1.5 text-sm text-jay-text placeholder-jay-textMuted outline-none focus:border-jay-accent/50"
        />
        <select
          value={newCat}
          onChange={(e) => setNewCat(e.target.value)}
          className="bg-jay-surface border border-jay-border/50 rounded-lg px-2 text-xs font-mono text-jay-textDim outline-none"
        >
          {CATEGORIES.slice(1).map((c) => <option key={c}>{c}</option>)}
        </select>
        <button
          onClick={handleStore}
          className="px-3 py-1.5 bg-jay-accent/10 border border-jay-accent/30 text-jay-accent hover:bg-jay-accent/20 rounded-lg text-xs font-mono transition-colors"
        >
          <Plus size={14} />
        </button>
      </div>

      {/* Memory list */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
              className="w-6 h-6 border-2 border-jay-accent border-t-transparent rounded-full"
            />
          </div>
        ) : memories.length === 0 ? (
          <div className="flex flex-col items-center gap-3 py-12 text-center">
            <Brain size={28} className="text-jay-textMuted" />
            <div className="text-sm text-jay-textDim">
              {query ? "No memories matching your query" : "No memories stored yet"}
            </div>
            <div className="text-xs text-jay-textMuted">
              J.A.Y. automatically remembers important things from conversations
            </div>
          </div>
        ) : (
          <AnimatePresence>
            {memories.map((m) => (
              <MemoryCard key={m.id} memory={m} onDelete={() => handleDelete(m.id)} />
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
