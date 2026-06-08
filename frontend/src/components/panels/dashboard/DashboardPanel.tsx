"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useStore } from "@/store";
import { systemAPI, memoryAPI, projectsAPI } from "@/lib/api";
import { Bot, Brain, Wrench, TrendingUp, Activity, Clock, CheckCircle2, AlertTriangle } from "lucide-react";

function StatCard({ icon: Icon, label, value, sub, color = "#00d4ff" }: any) {
  return (
    <div className="bg-jay-surface/30 border border-jay-border/40 rounded-xl p-4 hover:border-jay-accent/30 transition-colors">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-[10px] font-mono text-jay-textDim tracking-widest mb-2">{label}</div>
          <div className="text-2xl font-display font-bold" style={{ color }}>{value}</div>
          {sub && <div className="text-[11px] text-jay-textMuted mt-1">{sub}</div>}
        </div>
        <div className="p-2 rounded-lg" style={{ background: color + "15", border: `1px solid ${color}30` }}>
          <Icon size={18} style={{ color }} />
        </div>
      </div>
    </div>
  );
}

function AgentCard({ agent }: { agent: any }) {
  const isActive = agent.status !== "idle";
  return (
    <div className={`flex items-center gap-3 p-2.5 rounded-lg border transition-all ${
      isActive ? "border-jay-accent/30 bg-jay-accent/5" : "border-jay-border/30 bg-jay-surface/20"
    }`}>
      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${isActive ? "bg-jay-accent animate-pulse" : "bg-jay-textMuted"}`} />
      <div className="min-w-0">
        <div className="text-xs font-mono text-jay-text capitalize">{agent.name}</div>
        <div className="text-[10px] text-jay-textMuted truncate">{agent.description}</div>
      </div>
      <div className={`text-[9px] font-mono ml-auto px-1.5 py-0.5 rounded uppercase ${
        isActive ? "text-jay-accent" : "text-jay-textMuted"
      }`}>
        {agent.status}
      </div>
    </div>
  );
}

export default function DashboardPanel() {
  const { status, agents, agentThoughts, toolActivity, activeAgents } = useStore();
  const [memStats, setMemStats] = useState<Record<string, number>>({});
  const [taskCount, setTaskCount] = useState(0);
  const [projectCount, setProjectCount] = useState(0);

  useEffect(() => {
    Promise.all([
      memoryAPI.getStats().then((s) => setMemStats(s.namespaces || {})).catch(() => {}),
      projectsAPI.listTasks().then((t) => setTaskCount(t.length)).catch(() => {}),
      projectsAPI.list().then((p) => setProjectCount(p.length)).catch(() => {}),
    ]);
  }, []);

  const totalMemories = Object.values(memStats).reduce((a, b) => a + b, 0);
  const availableProviders = status?.providers?.filter((p) => p.available).length || 0;

  return (
    <div className="space-y-6 overflow-y-auto">
      {/* Stats grid */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard
          icon={Bot}
          label="AI PROVIDERS"
          value={availableProviders}
          sub={`${status?.providers?.length || 0} configured`}
          color="#00d4ff"
        />
        <StatCard
          icon={Brain}
          label="MEMORIES"
          value={totalMemories}
          sub="across all namespaces"
          color="#a855f7"
        />
        <StatCard
          icon={CheckCircle2}
          label="TASKS"
          value={taskCount}
          sub={`${projectCount} projects`}
          color="#22c55e"
        />
        <StatCard
          icon={Activity}
          label="ACTIVE AGENTS"
          value={activeAgents.length}
          sub={`${agents.length} total agents`}
          color="#f97316"
        />
      </div>

      {/* System metrics */}
      {status && (
        <div className="bg-jay-surface/30 border border-jay-border/40 rounded-xl p-4">
          <div className="text-[10px] font-mono text-jay-textDim tracking-widest mb-3">SYSTEM RESOURCES</div>
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: "CPU", value: status.cpu_percent, color: status.cpu_percent > 80 ? "#ef4444" : "#00d4ff" },
              { label: "RAM", value: status.ram_percent, color: status.ram_percent > 80 ? "#ef4444" : "#22c55e" },
            ].map(({ label, value, color }) => (
              <div key={label}>
                <div className="flex justify-between text-[11px] font-mono mb-1">
                  <span className="text-jay-textDim">{label}</span>
                  <span style={{ color }}>{value.toFixed(1)}%</span>
                </div>
                <div className="h-2 bg-jay-border/40 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: color }}
                    animate={{ width: `${value}%` }}
                    transition={{ duration: 0.8 }}
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 text-[11px] font-mono text-jay-textDim">
            {status.os} · J.A.Y. {status.version}
          </div>
        </div>
      )}

      {/* Agents */}
      <div className="bg-jay-surface/30 border border-jay-border/40 rounded-xl p-4">
        <div className="text-[10px] font-mono text-jay-textDim tracking-widest mb-3">AGENT STATUS</div>
        <div className="grid grid-cols-2 gap-2">
          {agents.map((agent) => (
            <AgentCard key={agent.name} agent={agent} />
          ))}
        </div>
      </div>

      {/* Activity feed */}
      <div className="grid grid-cols-2 gap-3">
        {/* Agent thoughts */}
        <div className="bg-jay-surface/30 border border-jay-border/40 rounded-xl p-4">
          <div className="text-[10px] font-mono text-jay-textDim tracking-widest mb-3">AGENT ACTIVITY</div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {agentThoughts.length === 0 ? (
              <div className="text-xs text-jay-textMuted text-center py-4">No recent activity</div>
            ) : agentThoughts.map((t, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-start gap-2 text-xs"
              >
                <span className="text-jay-accent font-mono text-[10px] capitalize flex-shrink-0 mt-0.5">{t.agent}</span>
                <span className="text-jay-textDim truncate">{t.thought}</span>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Tool activity */}
        <div className="bg-jay-surface/30 border border-jay-border/40 rounded-xl p-4">
          <div className="text-[10px] font-mono text-jay-textDim tracking-widest mb-3">TOOL ACTIVITY</div>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {toolActivity.length === 0 ? (
              <div className="text-xs text-jay-textMuted text-center py-4">No tools used yet</div>
            ) : toolActivity.map((t, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-1.5">
                  <Wrench size={10} className="text-jay-textMuted" />
                  <span className="font-mono text-jay-text">{t.tool}</span>
                </div>
                <span className={`text-[10px] font-mono ${t.status === "success" ? "text-jay-green" : t.status === "error" ? "text-jay-red" : "text-jay-orange"}`}>
                  {t.status}
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Providers */}
      {status?.providers && (
        <div className="bg-jay-surface/30 border border-jay-border/40 rounded-xl p-4">
          <div className="text-[10px] font-mono text-jay-textDim tracking-widest mb-3">AI PROVIDERS</div>
          <div className="grid grid-cols-2 gap-2">
            {status.providers.map((p) => (
              <div key={p.name} className={`flex items-center justify-between p-2 rounded-lg border ${
                p.available ? "border-jay-green/30 bg-jay-green/5" : "border-jay-border/30 bg-jay-surface/10"
              }`}>
                <span className="text-xs font-mono capitalize text-jay-text">{p.name}</span>
                <div className={`flex items-center gap-1.5 text-[10px] font-mono ${p.available ? "text-jay-green" : "text-jay-textMuted"}`}>
                  <div className={`w-1.5 h-1.5 rounded-full ${p.available ? "bg-jay-green" : "bg-jay-textMuted"}`} />
                  {p.available ? "ONLINE" : "OFFLINE"}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
