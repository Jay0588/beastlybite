// J.A.Y. WebSocket Client — real-time event bridge

import { useStore } from "@/store";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

class JAYWebSocket {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 2000;
  private maxDelay = 30000;
  private alive = false;

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    try {
      this.ws = new WebSocket(WS_URL);

      this.ws.onopen = () => {
        this.alive = true;
        this.reconnectDelay = 2000;
        useStore.getState().setWsConnected(true);
        useStore.getState().setWsError(null);
        console.log("[J.A.Y. WS] Connected");
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          this.handleMessage(msg.type, msg.data || {});
        } catch (e) {
          console.error("[J.A.Y. WS] Parse error:", e);
        }
      };

      this.ws.onclose = () => {
        this.alive = false;
        useStore.getState().setWsConnected(false);
        this.scheduleReconnect();
      };

      this.ws.onerror = (e) => {
        useStore.getState().setWsError("Connection error");
      };
    } catch (e) {
      this.scheduleReconnect();
    }
  }

  private handleMessage(type: string, data: Record<string, unknown>) {
    const store = useStore.getState();

    switch (type) {
      case "connected":
        store.addNotification({ title: "J.A.Y. Online", message: "System connected", type: "success" });
        break;

      case "agent_thinking":
        if (data.agent) {
          store.setAgentActive(data.agent as string, true);
          store.addAgentThought(data.agent as string, (data.query as string) || "Processing...");
        }
        break;

      case "agent_started":
        if (data.agent) store.setAgentActive(data.agent as string, true);
        break;

      case "agent_completed":
        if (data.agent) store.setAgentActive(data.agent as string, false);
        break;

      case "tool_called":
        store.addToolActivity({ tool: (data.tool as string) || "unknown", status: "running" });
        break;

      case "tool_completed":
        store.addToolActivity({
          tool: (data.tool as string) || "unknown",
          status: "success",
          result: data.result as string,
        });
        break;

      case "wake_word_detected":
        store.setListening(true);
        store.addNotification({ title: "Wake Word", message: "Hey J.A.Y. detected!", type: "info" });
        break;

      case "transcript_ready":
        store.setTranscript((data.text as string) || "");
        store.setListening(false);
        break;

      case "tts_started":
        store.setSpeaking(true);
        break;

      case "tts_complete":
        store.setSpeaking(false);
        break;

      case "memory_stored":
        store.addNotification({ title: "Memory Stored", message: "New information remembered", type: "info" });
        break;

      case "notification":
        store.addNotification({
          title: (data.title as string) || "Notification",
          message: (data.message as string) || "",
          type: (data.level as "info" | "success" | "warning" | "error") || "info",
        });
        break;

      case "approval_required":
        store.addApprovalRequest(data as any);
        store.addNotification({
          title: "Approval Required",
          message: `Action "${data.tool}" needs your approval`,
          type: "warning",
        });
        break;

      case "error":
        store.addNotification({
          title: "Error",
          message: (data.message as string) || "An error occurred",
          type: "error",
        });
        break;
    }
  }

  send(type: string, data: Record<string, unknown> = {}) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, ...data }));
    }
  }

  ping() {
    this.send("ping", { ts: Date.now() });
  }

  approveAction(actionId: string) {
    this.send("approve_action", { action_id: actionId });
  }

  denyAction(actionId: string) {
    this.send("deny_action", { action_id: actionId });
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      console.log(`[J.A.Y. WS] Reconnecting in ${this.reconnectDelay}ms...`);
      this.connect();
      this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxDelay);
    }, this.reconnectDelay);
  }

  disconnect() {
    this.alive = false;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
  }
}

export const jayWS = new JAYWebSocket();
