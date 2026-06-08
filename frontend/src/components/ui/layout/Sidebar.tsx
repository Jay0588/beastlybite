"use client";

import { motion } from "framer-motion";
import {
  MessageSquare, Mic, Brain, FolderOpen, Terminal,
  TrendingUp, Search, Settings, LayoutDashboard, Bell, Code2
} from "lucide-react";
import { useStore } from "@/store";
import type { PanelId } from "@/types";
import JayOrb from "@/components/hud/orb/JayOrb";

// IDE added to nav
const NAV_TOP: { id: PanelId; icon: any; label: string }[] = [
  { id: "chat",      icon: MessageSquare,  label: "Chat"      },
  { id: "voice",     icon: Mic,            label: "Voice"     },
  { id: "dashboard", icon: LayoutDashboard,label: "Dashboard" },
  { id: "ide",       icon: Code2,          label: "IDE"       },
  { id: "trading",   icon: TrendingUp,     label: "Trading"   },
];

const NAV_BOTTOM: { id: PanelId; icon: any; label: string }[] = [
  { id: "memory",        icon: Brain,       label: "Memory"   },
  { id: "projects",      icon: FolderOpen,  label: "Projects" },
  { id: "terminal",      icon: Terminal,    label: "Terminal" },
  { id: "research",      icon: Search,      label: "Research" },
  { id: "notifications", icon: Bell,        label: "Alerts"   },
  { id: "settings",      icon: Settings,    label: "Settings" },
];

function NavBtn({ id, icon: Icon, label }: { id: PanelId; icon: any; label: string }) {
  const { activePanel, setActivePanel, notifications } = useStore();
  const isActive = activePanel === id;
  const unread = id === "notifications" ? notifications.filter((n) => !n.read).length : 0;

  return (
    <div className="relative w-full group">
      <button
        onClick={() => setActivePanel(id)}
        className={`w-full flex flex-col items-center gap-1 py-2.5 px-1 rounded-xl transition-all relative ${
          isActive
            ? "bg-jay-accent/15 text-jay-accent border border-jay-accent/25"
            : "text-jay-textMuted hover:text-jay-textDim hover:bg-jay-surface/40"
        }`}
      >
        <Icon size={17} strokeWidth={isActive ? 2 : 1.5} />
        <span className="text-[8px] font-mono tracking-wider leading-none">{label.toUpperCase()}</span>

        {unread > 0 && (
          <span className="absolute top-1 right-1 w-3.5 h-3.5 bg-jay-red rounded-full text-[8px] flex items-center justify-center text-white font-mono">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
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
}

export default function Sidebar() {
  const { wsConnected } = useStore();

  return (
    <motion.aside
      initial={{ x: -80, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="w-[72px] flex-shrink-0 flex flex-col items-center py-3 border-r border-jay-border/40 bg-jay-surface/20 relative z-10"
    >
      {/* ── Top nav ────────────────────────────────────── */}
      <nav className="flex flex-col items-center gap-0.5 w-full px-2">
        {NAV_TOP.map((item) => (
          <NavBtn key={item.id} {...item} />
        ))}
      </nav>

      {/* ── ORB — always visible, centred ──────────────── */}
      <div className="flex-1 flex items-center justify-center py-2">
        <div className="scale-[0.48] origin-center">
          <JayOrb />
        </div>
      </div>

      {/* ── Bottom nav ─────────────────────────────────── */}
      <nav className="flex flex-col items-center gap-0.5 w-full px-2 mb-1">
        {NAV_BOTTOM.map((item) => (
          <NavBtn key={item.id} {...item} />
        ))}
      </nav>

      {/* Connection dot */}
      <div className="flex flex-col items-center gap-0.5 mb-1">
        <div className={`w-1.5 h-1.5 rounded-full ${wsConnected ? "bg-jay-green animate-pulse" : "bg-jay-red"}`} />
        <span className="text-[7px] font-mono text-jay-textMuted rotate-0">v0.1</span>
      </div>
    </motion.aside>
  );
}
