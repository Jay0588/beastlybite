"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Cpu, Cloud, Zap, Brain, RefreshCw, Download, Trash2,
  CheckCircle, XCircle, AlertTriangle, ChevronRight,
  BarChart2, Shield, Mic, Database, Sliders, Info,
  RotateCcw, Unlock,
} from "lucide-react";
import { systemAPI } from "@/lib/api";
import { useStore } from "@/store";

// ── API helpers ────────────────────────────────────────────────────────────────

const api = (path: string, opts?: RequestInit) =>
  fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  }).then((r) => r.json());

// ── Sub-tab type ───────────────────────────────────────────────────────────────

type Tab = "routing" | "models" | "quota" | "voice" | "security" | "about";

const TABS: { id: Tab; label: string; icon: any }[] = [
  { id: "routing",  label: "Routing",  icon: Zap },
  { id: "models",   label: "Models",   icon: Cpu },
  { id: "quota",    label: "Quota",    icon: BarChart2 },
  { id: "voice",    label: "Voice",    icon: Mic },
  { id: "security", label: "Security", icon: Shield },
  { id: "about",    label: "About",    icon: Info },
];

// ── Tiny reusable atoms ────────────────────────────────────────────────────────

function StatusDot({ ok, pulse = false }: { ok: boolean; pulse?: boolean }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${
        ok ? "bg-jay-green" : "bg-jay-red"
      } ${ok && pulse ? "animate-pulse" : ""}`}
    />
  );
}

function Badge({
  children, color = "accent",
}: { children: React.ReactNode; color?: "accent" | "green" | "red" | "orange" | "purple" }) {
  const cls: Record<string, string> = {
    accent: "text-jay-accent  border-jay-accent/30  bg-jay-accent/10",
    green:  "text-jay-green   border-jay-green/30   bg-jay-green/10",
    red:    "text-jay-red     border-jay-red/30     bg-jay-red/10",
    orange: "text-jay-orange  border-jay-orange/30  bg-jay-orange/10",
    purple: "text-jay-purple  border-jay-purple/30  bg-jay-purple/10",
  };
  return (
    <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border uppercase tracking-wider ${cls[color]}`}>
      {children}
    </span>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className="w-3 h-px bg-jay-accent/60" />
      <span className="text-[10px] font-mono text-jay-accent tracking-[0.2em] uppercase">
        {children}
      </span>
    </div>
  );
}

function ProgressBar({ pct, color = "#00d4ff" }: { pct: number; color?: string }) {
  const safe = Math.min(100, Math.max(0, pct));
  const c = safe > 90 ? "#ef4444" : safe > 70 ? "#f97316" : color;
  return (
    <div className="h-1 w-full bg-jay-border/30 rounded-full overflow-hidden">
      <motion.div
        className="h-full rounded-full"
        style={{ background: c }}
        animate={{ width: `${safe}%` }}
        transition={{ duration: 0.6 }}
      />
    </div>
  );
}

function SavedFlash({ show }: { show: boolean }) {
  return (
    <AnimatePresence>
      {show && (
        <motion.span
          initial={{ opacity: 0, x: 6 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0 }}
          className="text-[10px] font-mono text-jay-green"
        >
          ✓ saved
        </motion.span>
      )}
    </AnimatePresence>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function SettingsPanel() {
  const [tab, setTab] = useState<Tab>("routing");
  const [modelStatus, setModelStatus] = useState<any>(null);
  const [settings, setSettings] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [savedKey, setSavedKey] = useState<string | null>(null);
  const [pulling, setPulling] = useState<string | null>(null);
  const [unloading, setUnloading] = useState<string | null>(null);
  const [testMsg, setTestMsg] = useState("");
  const [testResult, setTestResult] = useState<any>(null);

  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      const [ms, sett] = await Promise.all([
        api("/api/system/model-status"),
        api("/api/system/settings"),
      ]);
      setModelStatus(ms);
      setSettings(sett);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async (key: string, value: unknown) => {
    await api("/api/system/settings", {
      method: "POST",
      body: JSON.stringify({ key, value }),
    });
    setSavedKey(key);
    setTimeout(() => setSavedKey(null), 2000);
    setSettings((s: any) => ({ ...s, [key]: value }));
    // Re-fetch model status since routing may have changed
    if (["routing_mode", "routing_fallback_order", "ollama_ram_budget_gb"].includes(key)) {
      await load();
    }
  };

  const pullModel = async (modelId: string) => {
    setPulling(modelId);
    await api(`/api/system/ollama/pull/${encodeURIComponent(modelId)}`, { method: "POST" });
    useStore.getState().addNotification({
      title: "Pulling model",
      message: `${modelId} — watch notifications for progress`,
      type: "info",
    });
    // Poll until installed
    const poll = setInterval(async () => {
      const ms = await api("/api/system/model-status");
      setModelStatus(ms);
      const installed = ms.installed_models?.some((m: any) => m.id === modelId);
      if (installed) {
        clearInterval(poll);
        setPulling(null);
        useStore.getState().addNotification({
          title: "Model ready",
          message: `${modelId} installed`,
          type: "success",
        });
      }
    }, 4000);
    setTimeout(() => { clearInterval(poll); setPulling(null); }, 300_000);
  };

  const unloadModel = async (modelId: string) => {
    setUnloading(modelId);
    await api(`/api/system/ollama/unload/${encodeURIComponent(modelId)}`, { method: "POST" });
    await load();
    setUnloading(null);
  };

  const unblockModel = async (modelId: string) => {
    await api(`/api/system/openrouter/quota/unblock/${encodeURIComponent(modelId)}`, { method: "POST" });
    await load();
  };

  const resetAllQuota = async () => {
    await api("/api/system/openrouter/quota/reset", { method: "POST" });
    await load();
    useStore.getState().addNotification({ title: "Quota reset", message: "All OpenRouter counters cleared", type: "success" });
  };

  const testClassify = async () => {
    if (!testMsg.trim()) return;
    const r = await api("/api/system/classify", { method: "POST", body: JSON.stringify({ message: testMsg }) });
    setTestResult(r);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          className="w-8 h-8 border-2 border-jay-accent border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full gap-0">
      {/* Tab bar */}
      <div className="flex items-center gap-1 pb-3 border-b border-jay-border/30 flex-shrink-0">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-mono transition-all ${
              tab === id
                ? "bg-jay-accent/10 text-jay-accent border border-jay-accent/30"
                : "text-jay-textDim hover:text-jay-text hover:bg-jay-surface/40"
            }`}
          >
            <Icon size={12} />
            {label.toUpperCase()}
          </button>
        ))}
        <div className="flex-1" />
        <button
          onClick={load}
          disabled={refreshing}
          className="p-1.5 text-jay-textMuted hover:text-jay-accent transition-colors"
          title="Refresh"
        >
          <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto pt-4 pr-1 space-y-5">

        {/* ── ROUTING tab ─────────────────────────────────────────────────── */}
        {tab === "routing" && (
          <>
            {/* Last decision banner */}
            {modelStatus?.last_decision && (
              <motion.div
                initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}
                className="flex items-start gap-3 p-3 bg-jay-accent/5 border border-jay-accent/20 rounded-xl"
              >
                <Zap size={14} className="text-jay-accent mt-0.5 flex-shrink-0" />
                <div className="min-w-0">
                  <div className="text-[10px] font-mono text-jay-textDim mb-0.5">LAST ROUTING DECISION</div>
                  <div className="text-sm text-jay-text font-mono">
                    <span className="text-jay-accent">{modelStatus.last_decision.task_label}</span>
                    {" → "}
                    <span className="text-jay-text">{modelStatus.last_decision.model_id}</span>
                    <span className="text-jay-textMuted text-[10px] ml-1.5">
                      via {modelStatus.last_decision.provider}
                    </span>
                    {modelStatus.last_decision.fallback_used && (
                      <Badge color="orange">fallback</Badge>
                    )}
                  </div>
                  <div className="text-[10px] text-jay-textMuted mt-0.5">{modelStatus.last_decision.reason}</div>
                </div>
              </motion.div>
            )}

            {/* Routing mode */}
            <div>
              <SectionLabel>Routing Mode</SectionLabel>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { value: "auto",        label: "Auto",        desc: "Smart task-based routing (recommended)" },
                  { value: "ollama",      label: "Ollama Only", desc: "Always use local Ollama — fully offline" },
                  { value: "openrouter",  label: "OpenRouter",  desc: "Always use OpenRouter cloud" },
                  { value: "gemini",      label: "Gemini",      desc: "Always use Google Gemini" },
                ].map(({ value, label, desc }) => (
                  <button
                    key={value}
                    onClick={() => save("routing_mode", value)}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      settings.routing_mode === value
                        ? "border-jay-accent/50 bg-jay-accent/10"
                        : "border-jay-border/40 bg-jay-surface/20 hover:border-jay-border"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="text-sm font-mono text-jay-text">{label}</span>
                      {settings.routing_mode === value && (
                        <CheckCircle size={13} className="text-jay-accent" />
                      )}
                    </div>
                    <div className="text-[10px] text-jay-textMuted">{desc}</div>
                  </button>
                ))}
              </div>
              <SavedFlash show={savedKey === "routing_mode"} />
            </div>

            {/* RAM budget */}
            <div>
              <SectionLabel>Ollama RAM Budget</SectionLabel>
              <div className="flex items-center gap-3">
                <input
                  type="range" min={2} max={12} step={0.5}
                  value={settings.ollama_ram_budget_gb ?? 7}
                  onChange={(e) => save("ollama_ram_budget_gb", parseFloat(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm font-mono text-jay-accent w-14 text-right">
                  {settings.ollama_ram_budget_gb ?? 7} GB
                </span>
                <SavedFlash show={savedKey === "ollama_ram_budget_gb"} />
              </div>
              <div className="flex justify-between text-[10px] text-jay-textMuted mt-1">
                <span>2 GB (tiny models)</span>
                <span className="text-jay-textDim">Recommended: 7 GB on 12 GB RAM</span>
                <span>12 GB</span>
              </div>
            </div>

            {/* Per-task routing table */}
            <div>
              <SectionLabel>Per-Task Routing Preview</SectionLabel>
              <div className="space-y-1.5">
                {modelStatus?.task_routing?.map((row: any) => (
                  <div
                    key={row.task}
                    className="flex items-center gap-2 px-3 py-2 bg-jay-surface/20 border border-jay-border/20 rounded-lg hover:border-jay-border/40 transition-colors"
                  >
                    {/* Task label */}
                    <span className="text-[11px] font-mono text-jay-textDim w-28 flex-shrink-0">
                      {row.task_label}
                    </span>

                    {/* Effective model */}
                    <ChevronRight size={10} className="text-jay-textMuted flex-shrink-0" />
                    <span className={`text-[11px] font-mono flex-1 truncate ${
                      row.effective_model ? "text-jay-text" : "text-jay-red/70"
                    }`}>
                      {row.effective_model ?? "no model available"}
                    </span>

                    {/* Provider badge */}
                    {row.effective_provider && (
                      <Badge color={
                        row.effective_provider === "ollama"      ? "accent"  :
                        row.effective_provider === "openrouter"  ? "purple"  : "green"
                      }>
                        {row.effective_provider}
                      </Badge>
                    )}

                    {/* Override indicator */}
                    {row.override && <Badge color="orange">override</Badge>}

                    {/* Ollama installed */}
                    {row.ollama_candidate && (
                      <StatusDot ok={row.ollama_installed} />
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Test classifier */}
            <div>
              <SectionLabel>Test Classifier</SectionLabel>
              <div className="flex gap-2">
                <input
                  value={testMsg}
                  onChange={(e) => setTestMsg(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && testClassify()}
                  placeholder="Type a message to see how it's classified…"
                  className="flex-1 bg-jay-surface border border-jay-border/50 rounded-lg px-3 py-1.5 text-sm text-jay-text placeholder-jay-textMuted outline-none focus:border-jay-accent/50"
                />
                <button
                  onClick={testClassify}
                  className="px-3 py-1.5 bg-jay-accent/10 border border-jay-accent/30 text-jay-accent rounded-lg text-xs font-mono hover:bg-jay-accent/20 transition-colors"
                >
                  TEST
                </button>
              </div>
              {testResult && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
                  className="mt-2 flex items-center gap-3 p-2.5 bg-jay-surface/30 border border-jay-border/30 rounded-lg"
                >
                  <div className="text-[10px] text-jay-textDim font-mono">CLASSIFIED AS</div>
                  <Badge color="accent">{testResult.task_type}</Badge>
                  <span className="text-xs text-jay-textDim">{testResult.task_label}</span>
                </motion.div>
              )}
            </div>
          </>
        )}

        {/* ── MODELS tab ──────────────────────────────────────────────────── */}
        {tab === "models" && (
          <>
            {/* Active model banner */}
            <div className="flex items-center gap-3 p-3 bg-jay-surface/30 border border-jay-border/40 rounded-xl">
              <div className="w-2 h-2 rounded-full bg-jay-accent animate-pulse flex-shrink-0" />
              <div>
                <div className="text-[10px] font-mono text-jay-textDim">ACTIVE IN OLLAMA MEMORY</div>
                <div className="text-sm font-mono text-jay-text mt-0.5">
                  {modelStatus?.active_model ?? "none"}
                </div>
              </div>
              <div className="ml-auto text-[10px] font-mono text-jay-textMuted">
                Budget: {modelStatus?.ram_budget_gb} GB
              </div>
            </div>

            {/* Installed models */}
            <div>
              <SectionLabel>Installed Ollama Models</SectionLabel>
              {(!modelStatus?.installed_models?.length) ? (
                <div className="text-sm text-jay-textMuted text-center py-6">
                  No models installed. Install Ollama then pull a model below.
                </div>
              ) : (
                <div className="space-y-2">
                  {modelStatus.installed_models.map((m: any) => (
                    <motion.div
                      key={m.id}
                      initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                      className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
                        m.is_active
                          ? "border-jay-accent/40 bg-jay-accent/5"
                          : "border-jay-border/30 bg-jay-surface/20 hover:border-jay-border/50"
                      }`}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-mono text-jay-text truncate">{m.id}</span>
                          {m.is_active && <Badge color="accent">loaded</Badge>}
                          {!m.fits_budget && <Badge color="red">over budget</Badge>}
                        </div>
                        <div className="text-[10px] text-jay-textMuted mt-0.5 flex items-center gap-3">
                          <span>{m.size_gb} GB</span>
                          {m.family    && <span>{m.family}</span>}
                          {m.parameters && <span>{m.parameters}</span>}
                          {m.quantization && <span>{m.quantization}</span>}
                        </div>
                      </div>
                      {/* Unload button — only for the active model */}
                      {m.is_active && (
                        <button
                          onClick={() => unloadModel(m.id)}
                          disabled={unloading === m.id}
                          title="Unload from RAM"
                          className="p-1.5 text-jay-textMuted hover:text-jay-orange transition-colors"
                        >
                          {unloading === m.id
                            ? <RefreshCw size={13} className="animate-spin" />
                            : <Trash2 size={13} />}
                        </button>
                      )}
                    </motion.div>
                  ))}
                </div>
              )}
            </div>

            {/* Not-installed recommended models */}
            {modelStatus?.not_installed?.length > 0 && (
              <div>
                <SectionLabel>Recommended — Not Yet Installed</SectionLabel>
                <div className="space-y-2">
                  {modelStatus.not_installed.map((m: any) => (
                    <div
                      key={m.id}
                      className="flex items-center gap-3 p-3 border border-jay-border/20 bg-jay-surface/10 rounded-xl hover:border-jay-border/40 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-mono text-jay-textDim truncate">{m.id}</span>
                          <Badge color={m.fits_budget ? "green" : "orange"}>
                            {m.ram_gb} GB
                          </Badge>
                          {m.tags?.includes("recommended") && <Badge color="accent">⭐</Badge>}
                        </div>
                        <div className="text-[10px] text-jay-textMuted mt-0.5 truncate">{m.description}</div>
                      </div>
                      <button
                        onClick={() => pullModel(m.id)}
                        disabled={pulling === m.id || !m.fits_budget}
                        title={!m.fits_budget ? "Exceeds RAM budget" : "Pull model"}
                        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-mono transition-colors ${
                          m.fits_budget
                            ? "bg-jay-accent/10 border border-jay-accent/30 text-jay-accent hover:bg-jay-accent/20"
                            : "bg-jay-surface/30 border border-jay-border/30 text-jay-textMuted cursor-not-allowed"
                        }`}
                      >
                        {pulling === m.id
                          ? <><RefreshCw size={11} className="animate-spin" /> PULLING</>
                          : <><Download size={11} /> PULL</>}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Usage stats */}
            {modelStatus?.usage_stats?.length > 0 && (
              <div>
                <SectionLabel>Usage This Session</SectionLabel>
                <div className="space-y-1.5">
                  {modelStatus.usage_stats.map((s: any) => (
                    <div key={s.model_id} className="flex items-center gap-3 px-3 py-2 bg-jay-surface/20 rounded-lg border border-jay-border/20">
                      <span className="text-[11px] font-mono text-jay-textDim flex-1 truncate">{s.model_id}</span>
                      <span className="text-[11px] font-mono text-jay-text">{s.requests} req</span>
                      {s.errors > 0 && (
                        <span className="text-[11px] font-mono text-jay-red">{s.errors} err</span>
                      )}
                      <span className="text-[11px] font-mono text-jay-textMuted">{s.avg_latency_ms}ms avg</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* ── QUOTA tab ───────────────────────────────────────────────────── */}
        {tab === "quota" && (
          <>
            {!modelStatus?.openrouter_key_set ? (
              <div className="flex flex-col items-center gap-3 py-10 text-center">
                <Cloud size={32} className="text-jay-textMuted/40" />
                <div className="text-sm text-jay-textDim">OpenRouter key not configured</div>
                <div className="text-xs text-jay-textMuted max-w-xs">
                  Add <code className="text-jay-accent">OPENROUTER_API_KEY=sk-or-v1-...</code> to{" "}
                  <code className="text-jay-accent">backend/.env</code> to enable cloud AI with free models.
                </div>
              </div>
            ) : (
              <>
                {/* Header */}
                <div className="flex items-center justify-between">
                  <div className="text-xs text-jay-textDim">
                    Free-tier limits per model: {modelStatus ? (
                      <>
                        {settings.or_free_daily_limit} req/day ·{" "}
                        {settings.or_free_rpm_limit} req/min ·{" "}
                        {(settings.or_free_tokens_per_day / 1000).toFixed(0)}K tokens/day
                      </>
                    ) : "loading…"}
                  </div>
                  <button
                    onClick={resetAllQuota}
                    className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-mono text-jay-textDim hover:text-jay-orange border border-jay-border/30 hover:border-jay-orange/30 rounded-lg transition-colors"
                  >
                    <RotateCcw size={10} /> RESET ALL
                  </button>
                </div>

                {/* Per-model cards */}
                {!modelStatus?.quota_status?.length ? (
                  <div className="text-sm text-jay-textMuted text-center py-8">
                    No OpenRouter models used yet this session.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {modelStatus.quota_status.map((q: any) => (
                      <div
                        key={q.model_id}
                        className={`p-3 rounded-xl border transition-all ${
                          q.blocked
                            ? "border-jay-red/30 bg-jay-red/5"
                            : q.available
                              ? "border-jay-border/30 bg-jay-surface/20"
                              : "border-jay-orange/30 bg-jay-orange/5"
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <StatusDot ok={q.available} />
                          <span className="text-[11px] font-mono text-jay-text flex-1 truncate">
                            {q.display_name ?? q.model_id}
                          </span>
                          {q.is_free && <Badge color="green">FREE</Badge>}
                          {q.blocked  && <Badge color="red">BLOCKED</Badge>}
                          {!q.available && !q.blocked && <Badge color="orange">EXHAUSTED</Badge>}
                          {q.blocked && (
                            <button
                              onClick={() => unblockModel(q.model_id)}
                              className="flex items-center gap-1 text-[10px] font-mono text-jay-accent hover:text-jay-text transition-colors"
                            >
                              <Unlock size={10} /> unblock
                            </button>
                          )}
                        </div>

                        {/* Exhaustion reason */}
                        {q.exhausted_reason && (
                          <div className="text-[10px] text-jay-orange/80 mb-2 flex items-center gap-1.5">
                            <AlertTriangle size={10} /> {q.exhausted_reason}
                          </div>
                        )}

                        {/* Progress bars */}
                        <div className="space-y-1.5">
                          <div>
                            <div className="flex justify-between text-[9px] font-mono text-jay-textMuted mb-0.5">
                              <span>Requests today</span>
                              <span>{q.daily_requests} / {q.daily_req_limit}</span>
                            </div>
                            <ProgressBar pct={q.daily_req_pct} />
                          </div>
                          <div>
                            <div className="flex justify-between text-[9px] font-mono text-jay-textMuted mb-0.5">
                              <span>Tokens today</span>
                              <span>{(q.daily_tokens / 1000).toFixed(1)}K / {(q.daily_token_limit / 1000).toFixed(0)}K</span>
                            </div>
                            <ProgressBar pct={q.daily_token_pct} color="#a855f7" />
                          </div>
                          <div className="flex items-center justify-between text-[9px] font-mono text-jay-textMuted">
                            <span>RPM now</span>
                            <span>{q.rpm_current} / {q.rpm_limit}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Quota settings */}
                <div>
                  <SectionLabel>Quota Limits</SectionLabel>
                  <div className="space-y-3">
                    {[
                      { key: "or_free_daily_limit",    label: "Daily request limit per model",   min: 0, max: 1000, step: 10 },
                      { key: "or_free_rpm_limit",      label: "Requests per minute per model",   min: 0, max: 60,   step: 1 },
                      { key: "or_free_tokens_per_day", label: "Daily token budget per model",    min: 0, max: 200000, step: 5000 },
                    ].map(({ key, label, min, max, step }) => (
                      <div key={key}>
                        <div className="flex justify-between text-[10px] font-mono text-jay-textDim mb-1">
                          <span>{label}</span>
                          <span className="text-jay-accent">{settings[key]?.toLocaleString()}</span>
                        </div>
                        <input
                          type="range" min={min} max={max} step={step}
                          value={settings[key] ?? 0}
                          onChange={(e) => save(key, parseInt(e.target.value))}
                          className="w-full"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </>
        )}

        {/* ── VOICE tab ───────────────────────────────────────────────────── */}
        {tab === "voice" && (
          <>
            <div>
              <SectionLabel>Text-to-Speech Voice</SectionLabel>
              <select
                value={settings.tts_voice ?? "en-US-AriaNeural"}
                onChange={(e) => save("tts_voice", e.target.value)}
                className="w-full bg-jay-surface border border-jay-border/50 rounded-xl px-3 py-2 text-sm text-jay-text outline-none focus:border-jay-accent/60"
              >
                {[
                  ["en-US-AriaNeural",    "Aria (US Female — default)"],
                  ["en-US-GuyNeural",     "Guy (US Male)"],
                  ["en-US-JennyNeural",   "Jenny (US Female)"],
                  ["en-US-DavisNeural",   "Davis (US Male)"],
                  ["en-GB-SoniaNeural",   "Sonia (UK Female)"],
                  ["en-GB-RyanNeural",    "Ryan (UK Male)"],
                  ["en-IN-NeerjaNeural",  "Neerja (India Female)"],
                  ["en-IN-PrabhatNeural", "Prabhat (India Male)"],
                ].map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
              <SavedFlash show={savedKey === "tts_voice"} />
            </div>

            <div>
              <SectionLabel>Speech Recognition Model</SectionLabel>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { v: "tiny",   size: "75 MB",   note: "fastest" },
                  { v: "base",   size: "142 MB",  note: "recommended" },
                  { v: "small",  size: "466 MB",  note: "better accuracy" },
                  { v: "medium", size: "1.5 GB",  note: "high accuracy" },
                  { v: "large",  size: "3 GB",    note: "best (slow)" },
                ].map(({ v, size, note }) => (
                  <button
                    key={v}
                    onClick={() => save("stt_model", v)}
                    className={`p-2.5 rounded-xl border text-center transition-all ${
                      settings.stt_model === v
                        ? "border-jay-accent/50 bg-jay-accent/10"
                        : "border-jay-border/30 bg-jay-surface/20 hover:border-jay-border"
                    }`}
                  >
                    <div className="text-sm font-mono capitalize text-jay-text">{v}</div>
                    <div className="text-[9px] text-jay-textMuted mt-0.5">{size}</div>
                    <div className="text-[9px] text-jay-accent mt-0.5">{note}</div>
                  </button>
                ))}
              </div>
              <SavedFlash show={savedKey === "stt_model"} />
            </div>
          </>
        )}

        {/* ── SECURITY tab ────────────────────────────────────────────────── */}
        {tab === "security" && (
          <>
            <div>
              <SectionLabel>Dangerous Action Approval</SectionLabel>
              <div
                onClick={() => save("require_approval_for_dangerous", !settings.require_approval_for_dangerous)}
                className={`flex items-center justify-between p-4 rounded-xl border cursor-pointer transition-all ${
                  settings.require_approval_for_dangerous
                    ? "border-jay-accent/30 bg-jay-accent/5"
                    : "border-jay-border/40 bg-jay-surface/20"
                }`}
              >
                <div>
                  <div className="text-sm text-jay-text">Require approval before dangerous actions</div>
                  <div className="text-[11px] text-jay-textMuted mt-0.5">
                    File deletion, code execution, Git push, system commands
                  </div>
                </div>
                <div className={`w-11 h-6 rounded-full relative transition-colors flex-shrink-0 ${
                  settings.require_approval_for_dangerous ? "bg-jay-accent/70" : "bg-jay-border/50"
                }`}>
                  <motion.div
                    animate={{ x: settings.require_approval_for_dangerous ? 22 : 2 }}
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                    className="absolute top-1 w-4 h-4 bg-white rounded-full shadow"
                  />
                </div>
              </div>
              <SavedFlash show={savedKey === "require_approval_for_dangerous"} />
            </div>

            <div>
              <SectionLabel>Memory Recall Sensitivity</SectionLabel>
              <div className="flex items-center gap-3">
                <input
                  type="range" min={0.3} max={0.99} step={0.05}
                  value={settings.memory_similarity_threshold ?? 0.7}
                  onChange={(e) => save("memory_similarity_threshold", parseFloat(e.target.value))}
                  className="flex-1"
                />
                <span className="text-sm font-mono text-jay-accent w-10 text-right">
                  {settings.memory_similarity_threshold ?? 0.7}
                </span>
                <SavedFlash show={savedKey === "memory_similarity_threshold"} />
              </div>
              <div className="flex justify-between text-[10px] text-jay-textMuted mt-1">
                <span>Fuzzy (0.3) — recalls more</span>
                <span>Strict (0.99) — recalls less, more precise</span>
              </div>
            </div>

            <div>
              <SectionLabel>API Keys Location</SectionLabel>
              <div className="p-3 bg-jay-surface/20 border border-jay-border/30 rounded-xl font-mono text-xs text-jay-textDim space-y-1">
                {[
                  "OPENROUTER_API_KEY=sk-or-v1-...",
                  "GOOGLE_API_KEY=AIzaSy...",
                  "OPENAI_API_KEY=sk-proj-...",
                  "PVPORCUPINE_ACCESS_KEY=...  (wake word)",
                ].map((l) => <div key={l}>{l}</div>)}
              </div>
              <p className="text-[11px] text-jay-textMuted mt-1.5">
                Edit <code className="text-jay-accent">backend/.env</code> → restart backend to apply.
              </p>
            </div>
          </>
        )}

        {/* ── ABOUT tab ───────────────────────────────────────────────────── */}
        {tab === "about" && (
          <div className="space-y-4">
            <div className="flex items-center gap-4 p-4 bg-jay-surface/30 border border-jay-border/40 rounded-xl">
              <div className="w-12 h-12 rounded-full bg-jay-accent/10 border border-jay-accent/30 flex items-center justify-center flex-shrink-0">
                <span className="text-jay-accent font-display font-bold text-sm">J.A.Y</span>
              </div>
              <div>
                <div className="text-base font-display font-bold text-jay-text">Just Assists You</div>
                <div className="text-xs text-jay-textDim mt-0.5">Personal AI Operating System</div>
                <div className="text-[10px] font-mono text-jay-textMuted mt-1">v0.1.0</div>
              </div>
            </div>

            <div>
              <SectionLabel>Intelligent Routing Summary</SectionLabel>
              <div className="space-y-2 text-xs text-jay-textDim leading-relaxed">
                {[
                  ["Quick / Voice",    "llama3.2:3b",                                      "2 GB RAM — ultra-fast"],
                  ["Chat",             "llama3.1:8b-instruct-q4_K_M",                      "4.7 GB RAM — strong general"],
                  ["Code",             "deepseek-coder-v2:16b-lite-instruct-q4_K_M",       "4.9 GB RAM — code specialist"],
                  ["Heavy Code",       "deepseek/deepseek-r1:free",                         "OpenRouter free — reasoning"],
                  ["Trading",          "mistral:7b-instruct-q4_K_M",                       "4.1 GB RAM — analytical"],
                  ["Research",         "meta-llama/llama-3.3-70b-instruct:free",            "OpenRouter free — 70B"],
                  ["Creative",         "google/gemma-3-27b-it:free",                        "OpenRouter free — creative"],
                  ["Plan / Analysis",  "llama3.1:8b → mixtral:8x7b → OR 70B",              "progressive fallback"],
                ].map(([task, model, note]) => (
                  <div key={task} className="flex gap-2">
                    <span className="w-24 flex-shrink-0 text-jay-textMuted">{task}</span>
                    <span className="flex-1 font-mono text-[11px] text-jay-text truncate">{model}</span>
                    <span className="text-jay-textMuted text-[10px] flex-shrink-0">{note}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-3 bg-jay-surface/20 border border-jay-border/30 rounded-xl text-[11px] text-jay-textMuted space-y-1">
              <div>Built with FastAPI · Next.js · Tauri · ChromaDB · Ollama</div>
              <div>Voice: faster-whisper (STT) · Edge TTS (TTS)</div>
              <div>Trading: yfinance · pandas-ta · CCXT</div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
