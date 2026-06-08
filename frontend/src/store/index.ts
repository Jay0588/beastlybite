// J.A.Y. Global State Store — Zustand

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  Message, Conversation, AgentStatus, SystemStatus,
  Notification, ApprovalRequest, PanelId, WSEvent
} from "@/types";

interface ChatState {
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;

  setConversations: (convs: Conversation[]) => void;
  setActiveConversation: (id: string | null) => void;
  setMessages: (msgs: Message[]) => void;
  addMessage: (msg: Message) => void;
  updateLastMessage: (content: string) => void;
  setStreaming: (v: boolean) => void;
  setStreamingContent: (v: string) => void;
  appendStreamChunk: (chunk: string) => void;
}

interface UIState {
  activePanel: PanelId;
  sidebarOpen: boolean;
  notifications: Notification[];
  approvalRequests: ApprovalRequest[];
  pendingApproval: ApprovalRequest | null;

  setActivePanel: (panel: PanelId) => void;
  toggleSidebar: () => void;
  addNotification: (n: Omit<Notification, "id" | "timestamp" | "read">) => void;
  markNotificationRead: (id: string) => void;
  clearNotifications: () => void;
  addApprovalRequest: (r: ApprovalRequest) => void;
  resolveApproval: (id: string) => void;
  setPendingApproval: (r: ApprovalRequest | null) => void;
}

interface VoiceState {
  isListening: boolean;
  isWakeWordActive: boolean;
  isSpeaking: boolean;
  currentTranscript: string;
  voiceLevel: number;
  waveformData: number[];

  setListening: (v: boolean) => void;
  setWakeWordActive: (v: boolean) => void;
  setSpeaking: (v: boolean) => void;
  setTranscript: (t: string) => void;
  setVoiceLevel: (v: number) => void;
  setWaveformData: (d: number[]) => void;
}

interface AgentState {
  agents: AgentStatus[];
  activeAgents: string[];
  agentThoughts: Array<{ agent: string; thought: string; ts: string }>;
  toolActivity: Array<{ tool: string; status: string; result?: string; ts: string }>;

  setAgents: (a: AgentStatus[]) => void;
  setAgentActive: (name: string, active: boolean) => void;
  addAgentThought: (agent: string, thought: string) => void;
  addToolActivity: (activity: { tool: string; status: string; result?: string }) => void;
  clearActivity: () => void;
}

interface SystemState {
  status: SystemStatus | null;
  wsConnected: boolean;
  wsError: string | null;

  setStatus: (s: SystemStatus) => void;
  setWsConnected: (v: boolean) => void;
  setWsError: (e: string | null) => void;
}

interface TradingState {
  watchlist: any[];
  portfolio: any | null;
  activeSymbol: string;
  activeExchange: string;

  setWatchlist: (w: any[]) => void;
  setPortfolio: (p: any) => void;
  setActiveSymbol: (s: string, exchange?: string) => void;
}

type Store = ChatState & UIState & VoiceState & AgentState & SystemState & TradingState;

let notifId = 0;

export const useStore = create<Store>()(
  persist(
    (set, get) => ({
      // ─── Chat ───────────────────────────────────────────────────────
      conversations: [],
      activeConversationId: null,
      messages: [],
      isStreaming: false,
      streamingContent: "",

      setConversations: (conversations) => set({ conversations }),
      setActiveConversation: (id) => set({ activeConversationId: id, messages: [] }),
      setMessages: (messages) => set({ messages }),
      addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
      updateLastMessage: (content) =>
        set((s) => {
          const msgs = [...s.messages];
          const last = msgs[msgs.length - 1];
          if (last && last.role === "assistant") {
            msgs[msgs.length - 1] = { ...last, content, isStreaming: false };
          }
          return { messages: msgs };
        }),
      setStreaming: (isStreaming) => set({ isStreaming }),
      setStreamingContent: (streamingContent) => set({ streamingContent }),
      appendStreamChunk: (chunk) =>
        set((s) => ({ streamingContent: s.streamingContent + chunk })),

      // ─── UI ─────────────────────────────────────────────────────────
      activePanel: "chat",
      sidebarOpen: true,
      notifications: [],
      approvalRequests: [],
      pendingApproval: null,

      setActivePanel: (activePanel) => set({ activePanel }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      addNotification: (n) =>
        set((s) => ({
          notifications: [
            {
              id: String(++notifId),
              timestamp: new Date().toISOString(),
              read: false,
              ...n,
            },
            ...s.notifications.slice(0, 49),
          ],
        })),
      markNotificationRead: (id) =>
        set((s) => ({
          notifications: s.notifications.map((n) =>
            n.id === id ? { ...n, read: true } : n
          ),
        })),
      clearNotifications: () => set({ notifications: [] }),
      addApprovalRequest: (r) =>
        set((s) => ({ approvalRequests: [...s.approvalRequests, r], pendingApproval: r })),
      resolveApproval: (id) =>
        set((s) => ({
          approvalRequests: s.approvalRequests.filter((r) => r.id !== id),
          pendingApproval: null,
        })),
      setPendingApproval: (pendingApproval) => set({ pendingApproval }),

      // ─── Voice ──────────────────────────────────────────────────────
      isListening: false,
      isWakeWordActive: false,
      isSpeaking: false,
      currentTranscript: "",
      voiceLevel: 0,
      waveformData: new Array(32).fill(0),

      setListening: (isListening) => set({ isListening }),
      setWakeWordActive: (isWakeWordActive) => set({ isWakeWordActive }),
      setSpeaking: (isSpeaking) => set({ isSpeaking }),
      setTranscript: (currentTranscript) => set({ currentTranscript }),
      setVoiceLevel: (voiceLevel) => set({ voiceLevel }),
      setWaveformData: (waveformData) => set({ waveformData }),

      // ─── Agents ─────────────────────────────────────────────────────
      agents: [],
      activeAgents: [],
      agentThoughts: [],
      toolActivity: [],

      setAgents: (agents) => set({ agents }),
      setAgentActive: (name, active) =>
        set((s) => ({
          activeAgents: active
            ? [...new Set([...s.activeAgents, name])]
            : s.activeAgents.filter((a) => a !== name),
        })),
      addAgentThought: (agent, thought) =>
        set((s) => ({
          agentThoughts: [
            { agent, thought, ts: new Date().toISOString() },
            ...s.agentThoughts.slice(0, 19),
          ],
        })),
      addToolActivity: (activity) =>
        set((s) => ({
          toolActivity: [
            { ...activity, ts: new Date().toISOString() },
            ...s.toolActivity.slice(0, 29),
          ],
        })),
      clearActivity: () => set({ agentThoughts: [], toolActivity: [] }),

      // ─── System ─────────────────────────────────────────────────────
      status: null,
      wsConnected: false,
      wsError: null,

      setStatus: (status) => set({ status }),
      setWsConnected: (wsConnected) => set({ wsConnected }),
      setWsError: (wsError) => set({ wsError }),

      // ─── Trading ────────────────────────────────────────────────────
      watchlist: [],
      portfolio: null,
      activeSymbol: "RELIANCE",
      activeExchange: "NSE",

      setWatchlist: (watchlist) => set({ watchlist }),
      setPortfolio: (portfolio) => set({ portfolio }),
      setActiveSymbol: (activeSymbol, activeExchange = "NSE") =>
        set({ activeSymbol, activeExchange }),
    }),
    {
      name: "jay-store",
      partialize: (state) => ({
        activePanel: state.activePanel,
        sidebarOpen: state.sidebarOpen,
        activeSymbol: state.activeSymbol,
        activeExchange: state.activeExchange,
        conversations: state.conversations.slice(0, 20),
      }),
    }
  )
);
