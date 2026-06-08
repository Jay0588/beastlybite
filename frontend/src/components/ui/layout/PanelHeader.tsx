"use client";

import { useStore } from "@/store";
import SystemMetrics from "@/components/hud/status/SystemMetrics";
import { Bell, X } from "lucide-react";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const PANEL_LABELS: Record<string, string> = {
  chat: "CONVERSATION",
  voice: "VOICE INTERFACE",
  dashboard: "SYSTEM DASHBOARD",
  trading: "TRADING WORKSPACE",
  memory: "LONG-TERM MEMORY",
  projects: "PROJECT EXPLORER",
  terminal: "TERMINAL CONSOLE",
  research: "RESEARCH WORKSPACE",
  notifications: "NOTIFICATIONS",
  settings: "SETTINGS",
};

export default function PanelHeader() {
  const { activePanel, notifications, markNotificationRead, clearNotifications } = useStore();
  const [showNotifs, setShowNotifs] = useState(false);
  const unread = notifications.filter((n) => !n.read).length;

  return (
    <header className="flex items-center justify-between px-5 py-2.5 border-b border-jay-border/40 bg-jay-surface/10 z-20 relative flex-shrink-0">
      {/* Left: panel name */}
      <div className="flex items-center gap-3">
        <div className="flex gap-1">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="w-1.5 h-1.5 rounded-sm bg-jay-border/60" />
          ))}
        </div>
        <h1 className="text-[11px] font-mono text-jay-textDim tracking-[0.2em]">
          {PANEL_LABELS[activePanel] || activePanel.toUpperCase()}
        </h1>
        <div className="w-px h-3 bg-jay-border/50" />
        <div className="text-[10px] font-mono text-jay-textMuted">
          {new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>

      {/* Right: metrics + notifications */}
      <div className="flex items-center gap-4">
        <SystemMetrics />

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifs((v) => !v)}
            className="relative p-1.5 text-jay-textMuted hover:text-jay-accent transition-colors"
          >
            <Bell size={14} />
            {unread > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-jay-red rounded-full text-[8px] flex items-center justify-center text-white">
                {unread}
              </span>
            )}
          </button>

          <AnimatePresence>
            {showNotifs && (
              <motion.div
                initial={{ opacity: 0, y: 8, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.95 }}
                className="absolute right-0 top-full mt-2 w-72 bg-jay-panel border border-jay-border/60 rounded-xl shadow-2xl z-50 overflow-hidden"
              >
                <div className="flex items-center justify-between px-3 py-2 border-b border-jay-border/40">
                  <span className="text-[10px] font-mono text-jay-textDim tracking-widest">NOTIFICATIONS</span>
                  <button
                    onClick={() => { clearNotifications(); setShowNotifs(false); }}
                    className="text-[10px] font-mono text-jay-textMuted hover:text-jay-red"
                  >
                    CLEAR ALL
                  </button>
                </div>
                <div className="max-h-80 overflow-y-auto">
                  {notifications.length === 0 ? (
                    <div className="text-xs text-jay-textMuted text-center py-6">No notifications</div>
                  ) : (
                    notifications.slice(0, 15).map((n) => (
                      <div
                        key={n.id}
                        onClick={() => markNotificationRead(n.id)}
                        className={`px-3 py-2.5 border-b border-jay-border/20 cursor-pointer hover:bg-jay-surface/40 transition-colors ${!n.read ? "bg-jay-accent/5" : ""}`}
                      >
                        <div className="flex items-start gap-2">
                          <div className={`w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0 ${
                            n.type === "success" ? "bg-jay-green" :
                            n.type === "error"   ? "bg-jay-red" :
                            n.type === "warning" ? "bg-jay-orange" : "bg-jay-accent"
                          }`} />
                          <div>
                            <div className="text-xs font-semibold text-jay-text">{n.title}</div>
                            <div className="text-[11px] text-jay-textDim">{n.message}</div>
                            <div className="text-[10px] text-jay-textMuted mt-0.5">
                              {new Date(n.timestamp).toLocaleTimeString()}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
}
