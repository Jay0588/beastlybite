// J.A.Y. Core Types

export type MessageRole = "user" | "assistant" | "system" | "tool";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  created_at?: string;
  tool_calls?: ToolCall[];
  isStreaming?: boolean;
}

export interface Conversation {
  id: string;
  title?: string;
  context_type?: string;
  created_at?: string;
  updated_at?: string;
  messages?: Message[];
}

export interface ToolCall {
  id: string;
  tool: string;
  params: Record<string, unknown>;
  result?: unknown;
  status: "pending" | "running" | "success" | "error";
}

export interface AgentStatus {
  name: string;
  description: string;
  status: "idle" | "thinking" | "executing" | "complete" | "error";
  capabilities: string[];
}

export interface ProviderStatus {
  name: string;
  available: boolean;
  supports_streaming: boolean;
  supports_tools: boolean;
  models?: string[];
}

export interface SystemStatus {
  name: string;
  version: string;
  status: string;
  os: string;
  cpu_percent: number;
  ram_percent: number;
  providers: ProviderStatus[];
  agents: AgentStatus[];
}

export interface MemoryEntry {
  id: string;
  content: string;
  category: string;
  metadata: Record<string, unknown>;
  score?: number;
}

// Trading
export interface Quote {
  symbol: string;
  exchange: string;
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  high: number;
  low: number;
  open: number;
  timestamp?: string;
}

export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TechnicalIndicators {
  symbol: string;
  price: number;
  rsi_14: number;
  macd: number;
  macd_signal: number;
  macd_hist: number;
  ema_20: number;
  ema_50: number;
  bb_upper: number;
  bb_lower: number;
  atr_14: number;
  vwap: number;
  signals: Signal[];
}

export interface Signal {
  indicator: string;
  signal: string;
  strength: "STRONG" | "MODERATE" | "WEAK";
  value?: number;
}

export interface PaperTrade {
  id: string;
  symbol: string;
  direction: "long" | "short";
  entry_price: number;
  exit_price?: number;
  quantity: number;
  stop_loss?: number;
  take_profit?: number;
  pnl?: number;
  pnl_pct?: number;
  status: "open" | "closed";
}

export interface Portfolio {
  capital: number;
  cash: number;
  total_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  open_positions: number;
  positions: PaperTrade[];
}

// Projects
export interface Project {
  id: string;
  name: string;
  description?: string;
  type: string;
  status: string;
  path?: string;
  tech_stack: string[];
  created_at?: string;
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: "todo" | "in_progress" | "done" | "blocked" | "cancelled";
  priority: "low" | "medium" | "high" | "critical";
  project_id?: string;
  tags: string[];
  created_at?: string;
}

// File system
export interface FSEntry {
  name: string;
  path: string;
  type: "file" | "directory";
  size?: number;
  modified?: number;
  children?: FSEntry[];
  isOpen?: boolean;
}

export interface OpenTab {
  path: string;
  name: string;
  content: string;
  language: string;
  isDirty: boolean;
  originalContent: string;
}

export interface UploadedFile {
  id: string;
  name: string;
  content: string;
  size: number;
  type: string;
  uploadedAt: string;
}

// WebSocket Events
export type WSEventType =
  | "connected" | "pong"
  | "agent_thinking" | "agent_started" | "agent_completed"
  | "tool_called" | "tool_completed"
  | "wake_word_detected" | "transcript_ready" | "tts_started" | "tts_complete"
  | "memory_stored" | "notification" | "approval_required" | "error"
  | "action_approved" | "action_denied";

export interface WSEvent {
  type: WSEventType;
  data: Record<string, unknown>;
}

// UI
export type PanelId =
  | "chat" | "voice" | "memory" | "projects" | "terminal"
  | "trading" | "research" | "settings" | "dashboard" | "notifications"
  | "ide";

export interface Notification {
  id: string;
  title: string;
  message: string;
  type: "info" | "success" | "warning" | "error";
  timestamp: string;
  read: boolean;
}

export interface ApprovalRequest {
  id: string;
  tool: string;
  description: string;
  params: Record<string, unknown>;
  risk: string;
  level: string;
  created_at: string;
}
