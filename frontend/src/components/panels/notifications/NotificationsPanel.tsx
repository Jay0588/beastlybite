"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Bell, Check, Trash2, Info, AlertTriangle, CheckCircle, XCircle } from "lucide-react";
import { useStore } from "@/store";

const TYPE_CONFIG = {
  info:    { icon: Info,          color: "#00d4ff" },
  success: { icon: CheckCircle,   color: "#22c55e" },
  warning: { icon: AlertTriangle, color: "#f97316" },
  error:   { icon: XCircle,       color: "#ef4444" },
};

export default function NotificationsPanel() {
  const { notifications, markNotificationRead, clearNotifications } = useStore();

  if (notifications.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <Bell size={40} className="text-jay-textMuted/40" />
        <div className="text-jay-textDim text-sm">No notifications</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="text-[10px] font-mono text-jay-textDim tracking-widest">
          {notifications.filter((n) => !n.read).length} UNREAD
        </div>
        <button
          onClick={clearNotifications}
          className="flex items-center gap-1.5 text-[11px] font-mono text-jay-textMuted hover:text-jay-red transition-colors"
        >
          <Trash2 size={12} /> CLEAR ALL
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2">
        <AnimatePresence>
          {notifications.map((n) => {
            const { icon: Icon, color } = TYPE_CONFIG[n.type] || TYPE_CONFIG.info;
            return (
              <motion.div
                key={n.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                onClick={() => markNotificationRead(n.id)}
                className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                  n.read
                    ? "border-jay-border/20 bg-jay-surface/10 opacity-60"
                    : "border-jay-border/40 bg-jay-surface/30 hover:border-jay-border"
                }`}
              >
                <div className="p-1.5 rounded-lg flex-shrink-0 mt-0.5" style={{ background: color + "15" }}>
                  <Icon size={14} style={{ color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-jay-text">{n.title}</div>
                  <div className="text-xs text-jay-textDim mt-0.5">{n.message}</div>
                  <div className="text-[10px] text-jay-textMuted mt-1">
                    {new Date(n.timestamp).toLocaleString()}
                  </div>
                </div>
                {!n.read && (
                  <div className="w-2 h-2 rounded-full flex-shrink-0 mt-1.5" style={{ background: color }} />
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
