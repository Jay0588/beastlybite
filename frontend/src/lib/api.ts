// J.A.Y. API Client

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "APIError";
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new APIError(res.status, text);
  }
  return res.json();
}

// ─── Chat ───────────────────────────────────────────────────────────────────

export const chatAPI = {
  async sendMessage(message: string, conversationId?: string, stream = true) {
    return request<{ conversation_id: string; content: string }>("/api/chat/message", {
      method: "POST",
      body: JSON.stringify({ message, conversation_id: conversationId, stream: false }),
    });
  },

  async *streamMessage(message: string, conversationId?: string): AsyncGenerator<string> {
    const res = await fetch(`${API_URL}/api/chat/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, conversation_id: conversationId, stream: true }),
    });
    if (!res.ok || !res.body) throw new APIError(res.status, "Stream failed");
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.chunk) yield data.chunk;
            if (data.done) return;
            if (data.error) throw new Error(data.error);
          } catch { /* skip malformed */ }
        }
      }
    }
  },

  listConversations: () => request<any[]>("/api/chat/conversations"),
  getMessages: (id: string) => request<any[]>(`/api/chat/conversations/${id}/messages`),
  deleteConversation: (id: string) =>
    request<void>(`/api/chat/conversations/${id}`, { method: "DELETE" }),
};

// ─── System ─────────────────────────────────────────────────────────────────

export const systemAPI = {
  getStatus: () => request<any>("/api/system/status"),
  getSettings: () => request<any>("/api/system/settings"),
  updateSetting: (key: string, value: unknown) =>
    request<any>("/api/system/settings", {
      method: "POST",
      body: JSON.stringify({ key, value }),
    }),
  getProviders: () => request<any>("/api/system/providers"),
  getAgents: () => request<any>("/api/system/agents"),
};

// ─── Voice ──────────────────────────────────────────────────────────────────

export const voiceAPI = {
  transcribe: async (audioBlob: Blob) => {
    const formData = new FormData();
    formData.append("file", audioBlob, "audio.webm");
    const res = await fetch(`${API_URL}/api/voice/transcribe`, {
      method: "POST",
      body: formData,
    });
    return res.json();
  },

  speak: (text: string, stream = false) =>
    fetch(`${API_URL}/api/voice/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, stream }),
    }),

  startWakeWord: () => request<any>("/api/voice/wake-word/start", { method: "POST" }),
  stopWakeWord: () => request<any>("/api/voice/wake-word/stop", { method: "POST" }),
  getStatus: () => request<any>("/api/voice/status"),
  listVoices: () => request<any>("/api/voice/voices"),
};

// ─── Trading ────────────────────────────────────────────────────────────────

export const tradingAPI = {
  getQuote: (symbol: string, exchange = "NSE") =>
    request<any>(`/api/trading/quote/${symbol}?exchange=${exchange}`),
  getHistorical: (symbol: string, exchange = "NSE", period = "3mo", interval = "1d") =>
    request<any>(`/api/trading/historical/${symbol}?exchange=${exchange}&period=${period}&interval=${interval}`),
  getIndicators: (symbol: string, exchange = "NSE") =>
    request<any>(`/api/trading/indicators/${symbol}?exchange=${exchange}`),
  getWatchlist: () => request<any>("/api/trading/watchlist"),
  addToWatchlist: (symbol: string, exchange: string) =>
    request<any>("/api/trading/watchlist", {
      method: "POST",
      body: JSON.stringify({ symbol, exchange }),
    }),
  removeFromWatchlist: (symbol: string) =>
    request<any>(`/api/trading/watchlist/${symbol}`, { method: "DELETE" }),
  openTrade: (data: any) =>
    request<any>("/api/trading/paper/trade", { method: "POST", body: JSON.stringify(data) }),
  closeTrade: (id: string) =>
    request<any>(`/api/trading/paper/close/${id}`, { method: "POST" }),
  getPortfolio: () => request<any>("/api/trading/paper/portfolio"),
  runBacktest: (data: any) =>
    request<any>("/api/trading/backtest", { method: "POST", body: JSON.stringify(data) }),
  getNews: (symbol: string) => request<any>(`/api/trading/news/${symbol}`),
};

// ─── Memory ─────────────────────────────────────────────────────────────────

export const memoryAPI = {
  store: (content: string, category = "fact", namespace = "general") =>
    request<any>("/api/memory/store", {
      method: "POST",
      body: JSON.stringify({ content, category, namespace }),
    }),
  search: (query: string, namespace = "general", n = 10) =>
    request<any>("/api/memory/search", {
      method: "POST",
      body: JSON.stringify({ query, namespace, n }),
    }),
  getAll: (namespace = "general") => request<any>(`/api/memory/all?namespace=${namespace}`),
  delete: (id: string, namespace = "general") =>
    request<any>(`/api/memory/${id}?namespace=${namespace}`, { method: "DELETE" }),
  getStats: () => request<any>("/api/memory/stats"),
  getProfile: () => request<any>("/api/memory/profile"),
};

// ─── Projects ───────────────────────────────────────────────────────────────

export const projectsAPI = {
  list: () => request<any[]>("/api/projects/"),
  create: (data: any) =>
    request<any>("/api/projects/", { method: "POST", body: JSON.stringify(data) }),
  scan: (path: string) =>
    request<any>(`/api/projects/scan?path=${encodeURIComponent(path)}`),
  listTasks: (projectId?: string) =>
    request<any[]>(`/api/projects/tasks${projectId ? `?project_id=${projectId}` : ""}`),
  createTask: (data: any) =>
    request<any>("/api/projects/tasks", { method: "POST", body: JSON.stringify(data) }),
  updateTaskStatus: (id: string, status: string) =>
    request<any>(`/api/projects/tasks/${id}/status?status=${status}`, { method: "PUT" }),
};

// ─── Tools ──────────────────────────────────────────────────────────────────

export const toolsAPI = {
  list: () => request<any>("/api/tools/"),
  execute: (tool: string, params: Record<string, unknown>, approved = false) =>
    request<any>("/api/tools/execute", {
      method: "POST",
      body: JSON.stringify({ tool, params, approved }),
    }),
  getPendingApprovals: () => request<any>("/api/tools/pending-approvals"),
  approve: (id: string) =>
    request<any>(`/api/tools/approve/${id}`, { method: "POST" }),
  deny: (id: string) =>
    request<any>(`/api/tools/deny/${id}`, { method: "POST" }),
  getAuditLog: (limit = 50) => request<any>(`/api/tools/audit-log?limit=${limit}`),
};

export { API_URL };
