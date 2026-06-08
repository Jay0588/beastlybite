"use client";

import { useEffect, Suspense, lazy } from "react";
import { motion, AnimatePresence } from "framer-motion";
import HUDBackground from "@/components/hud/particles/HUDBackground";
import Sidebar from "@/components/ui/layout/Sidebar";
import PanelHeader from "@/components/ui/layout/PanelHeader";
import ApprovalModal from "@/components/ui/modals/ApprovalModal";
import { useStore } from "@/store";
import { jayWS } from "@/lib/websocket";
import { systemAPI } from "@/lib/api";

// Lazy-load panels for fast initial render
const ChatPanel       = lazy(() => import("@/components/panels/chat/ChatPanel"));
const VoicePanel      = lazy(() => import("@/components/panels/voice/VoicePanel"));
const DashboardPanel  = lazy(() => import("@/components/panels/dashboard/DashboardPanel"));
const TradingPanel    = lazy(() => import("@/components/panels/trading/TradingPanel"));
const MemoryPanel     = lazy(() => import("@/components/panels/memory/MemoryPanel"));
const TerminalPanel   = lazy(() => import("@/components/panels/terminal/TerminalPanel"));
const SettingsPanel   = lazy(() => import("@/components/panels/settings/SettingsPanel"));
const ProjectsPanel   = lazy(() => import("@/components/panels/projects/ProjectsPanel"));
const ResearchPanel   = lazy(() => import("@/components/panels/research/ResearchPanel"));
const NotificationsPanel = lazy(() => import("@/components/panels/notifications/NotificationsPanel"));

function PanelLoader() {
  return (
    <div className="flex-1 flex items-center justify-center">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        className="w-8 h-8 border-2 border-jay-accent/30 border-t-jay-accent rounded-full"
      />
    </div>
  );
}

function ActivePanel() {
  const { activePanel } = useStore();

  const panels: Record<string, React.ReactNode> = {
    chat:          <ChatPanel />,
    voice:         <VoicePanel />,
    dashboard:     <DashboardPanel />,
    trading:       <TradingPanel />,
    memory:        <MemoryPanel />,
    projects:      <ProjectsPanel />,
    terminal:      <TerminalPanel />,
    research:      <ResearchPanel />,
    notifications: <NotificationsPanel />,
    settings:      <SettingsPanel />,
  };

  return (
    <Suspense fallback={<PanelLoader />}>
      <AnimatePresence mode="wait">
        <motion.div
          key={activePanel}
          initial={{ opacity: 0, x: 8 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -8 }}
          transition={{ duration: 0.2 }}
          className="flex-1 overflow-hidden p-4"
        >
          {panels[activePanel] || <div className="text-jay-textDim text-center mt-20">Panel not found</div>}
        </motion.div>
      </AnimatePresence>
    </Suspense>
  );
}

export default function Home() {
  const { setAgents } = useStore();

  useEffect(() => {
    // Connect WebSocket
    jayWS.connect();

    // Load initial system status
    systemAPI.getStatus()
      .then((s) => {
        useStore.getState().setStatus(s);
        if (s.agents) setAgents(s.agents);
      })
      .catch(() => {});

    // Ping every 30s to keep WS alive
    const pingInterval = setInterval(() => jayWS.ping(), 30000);

    return () => {
      clearInterval(pingInterval);
      jayWS.disconnect();
    };
  }, []);

  return (
    <div className="relative h-screen w-screen overflow-hidden flex bg-jay-bg">
      {/* Animated background */}
      <HUDBackground />

      {/* HUD corner decorations */}
      <div className="fixed inset-0 pointer-events-none z-[1]">
        <div className="absolute top-0 left-0 w-16 h-16 border-l-2 border-t-2 border-jay-accent/20" />
        <div className="absolute top-0 right-0 w-16 h-16 border-r-2 border-t-2 border-jay-accent/20" />
        <div className="absolute bottom-0 left-0 w-16 h-16 border-l-2 border-b-2 border-jay-accent/20" />
        <div className="absolute bottom-0 right-0 w-16 h-16 border-r-2 border-b-2 border-jay-accent/20" />
      </div>

      {/* Main layout */}
      <div className="relative z-10 flex w-full h-full">
        {/* Sidebar */}
        <Sidebar />

        {/* Content area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Top header */}
          <PanelHeader />

          {/* Panel content */}
          <ActivePanel />
        </div>
      </div>

      {/* Approval modal */}
      <ApprovalModal />
    </div>
  );
}
