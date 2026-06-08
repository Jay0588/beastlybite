"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useStore } from "@/store";
import { systemAPI } from "@/lib/api";
import { Cpu, MemoryStick, Wifi, WifiOff } from "lucide-react";

function MetricBar({ value, color = "#00d4ff" }: { value: number; color?: string }) {
  return (
    <div className="w-20 h-1 bg-jay-border/50 rounded-full overflow-hidden">
      <motion.div
        className="h-full rounded-full"
        style={{ background: color }}
        animate={{ width: `${value}%` }}
        transition={{ duration: 0.5 }}
      />
    </div>
  );
}

export default function SystemMetrics() {
  const { status, wsConnected } = useStore();
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const s = await systemAPI.getStatus();
        useStore.getState().setStatus(s);
      } catch {}
      setTick((t) => t + 1);
    }, 10000);
    // Initial load
    systemAPI.getStatus().then((s) => useStore.getState().setStatus(s)).catch(() => {});
    return () => clearInterval(id);
  }, []);

  const cpu = status?.cpu_percent ?? 0;
  const ram = status?.ram_percent ?? 0;
  const cpuColor = cpu > 80 ? "#ef4444" : cpu > 60 ? "#f97316" : "#00d4ff";
  const ramColor = ram > 80 ? "#ef4444" : ram > 60 ? "#f97316" : "#22c55e";

  return (
    <div className="flex items-center gap-4 text-jay-textMuted">
      {/* WS status */}
      <div className="flex items-center gap-1.5">
        {wsConnected ? (
          <Wifi size={12} className="text-jay-green" />
        ) : (
          <WifiOff size={12} className="text-jay-red" />
        )}
        <span className="text-[10px] font-mono">
          {wsConnected ? "CONNECTED" : "OFFLINE"}
        </span>
      </div>

      {/* CPU */}
      <div className="flex items-center gap-2">
        <Cpu size={11} style={{ color: cpuColor }} />
        <MetricBar value={cpu} color={cpuColor} />
        <span className="text-[10px] font-mono w-7" style={{ color: cpuColor }}>
          {cpu.toFixed(0)}%
        </span>
      </div>

      {/* RAM */}
      <div className="flex items-center gap-2">
        <MemoryStick size={11} style={{ color: ramColor }} />
        <MetricBar value={ram} color={ramColor} />
        <span className="text-[10px] font-mono w-7" style={{ color: ramColor }}>
          {ram.toFixed(0)}%
        </span>
      </div>

      {/* Provider */}
      {status && (
        <div className="text-[10px] font-mono text-jay-textDim">
          {status.providers?.find((p) => p.available)?.name?.toUpperCase() || "NO PROVIDER"}
        </div>
      )}
    </div>
  );
}
