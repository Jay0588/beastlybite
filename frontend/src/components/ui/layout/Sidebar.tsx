"use client";

import { motion } from "framer-motion";
import {
  MessageSquare, Mic, Brain, FolderOpen, Terminal,
  TrendingUp, Search, Settings, LayoutDashboard, Bell
} from "lucide-react";
import { useStore } from "@/store";
import type { PanelId } from "@/types";
import JayOrb from "@/components/hud/orb/JayOrb";

const NAV_ITEMS: { id: PanelId; icon: any; label: string; badge?: number }[] = [
  { id: "chat",         icon: MessageSquare,  label: "Chat" },
  { id: "voice",        icon: Mic,            label: "Voice" },
  { id: "dashboard",    icon: LayoutDashboard,label: "Dashboard" },
  { id: "trading",      icon: TrendingUp,     label: "Trading" },
  { id: "memory",       icon: Brain,          label: "Memory" },
  { id: "projects",     icon: FolderOpen,     label: "Projects" },
  { id: "terminal",     icon: Terminal,       label: "Terminal" },
  { id: "research",     icon: Search,         label: "Research" },
  { id: "notifications",icon: Bell,           label: "Alerts" },
  { id: "settings",     icon: Settings,       label: "Settings" },
];

export default function Sidebar() {
  const { activePanel, setActivePanel, notifications, wsConnected } = useStore();
  const unread = notifications.filter((n) => !n.read).length;

  return (
    <motion.aside
      initial={{ x: -80, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="w-[72px] flex-shrink-0 flex flex-col items-center py-4 gap-2 border-r border-jay-border/40 bg-jay-surface/20 relative z-10"
    >
      {/* Logo / Orb (mini) */}
      <div className="mb-2 px-2">
        <div className="w-10 h-10 rounded-full border border-jay-accent/30 bg-jay-accent/5 flex items-center justify-center">
          <div className={`w-3 h-3 rounded-full transition-colors ${wsConnected ? "bg-jay-accent animate-pulse" : "bg-jay-textMuted"}`} />
        </div>
        <div className="text-[8px] font-mono text-center mt-1 text-jay-textMuted tracking-widest">J.A.Y.</div>
      </div>

      {/* Divider */}
      <div className="w-8 h-px bg-jay-border/50 mb-1" />

      {/* Nav items */}
      <nav className="flex-1 flex flex-col items-center gap-1 w-full px-2">
        {NAV_ITEMS.map(({ id, icon: Icon, label, badge }) => {
          const isActive = activePanel === id;
          const showBadge = id === "notifications" && unread > 0;

          return (
            <div key={id} className="relative w-full group">
              <button
                onClick={() => setActivePanel(id)}
                className={`w-full flex flex-col items-center gap-1 py-2.5 px-1 rounded-xl transition-all relative ${
                  isActive
                    ? "bg-jay-accent/15 text-jay-accent border border-jay-accent/25"
                    : "text-jay-textMuted hover:text-jay-textDim hover:bg-jay-surface/40"
                }`}
              >
                <Icon size={18} strokeWidth={isActive ? 2 : 1.5} />
                <span className="text-[9px] font-mono tracking-wider leading-none">{label.toUpperCase()}</span>

                {/* Badge */}
                {showBadge && (
                  <span className="absolute top-1.5 right-1.5 w-4 h-4 bg-jay-red rounded-full text-[9px] flex items-center justify-center text-white font-mono">
                    {unread > 9 ? "9+" : unread}
                  </span>
                )}

                {/* Active indicator */}
                {isActive && (
                  <motion.div
                    layoutId="sidebar-active"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-jay-accent rounded-r-full"
                  />
                )}
              </button>

              {/* Tooltip */}
              <div className="absolute left-full top-1/2 -translate-y-1/2 ml-2 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity z-50 whitespace-nowrap">
                <div className="bg-jay-panel border border-jay-border/60 rounded-lg px-2.5 py-1 text-xs font-mono text-jay-text shadow-lg">
                  {label}
                </div>
              </div>
            </div>
          );
        })}
      </nav>

      {/* Bottom: version */}
      <div className="text-[8px] font-mono text-jay-textMuted opacity-50 rotate-90 mb-2">v0.1</div>
    </motion.aside>
  );
}
