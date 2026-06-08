"""
J.A.Y. WebSocket — Real-time events, voice streaming, live updates
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set, Dict
import json
import logging
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.add(ws)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, ws: WebSocket):
        self.active_connections.discard(ws)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, data: Dict):
        if not self.active_connections:
            return
        message = json.dumps({"type": event_type, "data": data})
        dead = set()
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active_connections.discard(ws)

    async def send_to(self, ws: WebSocket, event_type: str, data: Dict):
        try:
            await ws.send_text(json.dumps({"type": event_type, "data": data}))
        except Exception as e:
            logger.error(f"Send failed: {e}")
            self.active_connections.discard(ws)


ws_manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time J.A.Y. events."""
    await ws_manager.connect(websocket)

    # Subscribe to internal events and broadcast to this client
    from app.core.events import event_bus, Events

    async def on_event(data, event_type: str):
        await ws_manager.send_to(websocket, event_type, data or {})

    # Subscribe to all relevant events
    subscriptions = [
        (Events.AGENT_THINKING, lambda d: on_event(d, "agent_thinking")),
        (Events.AGENT_STARTED, lambda d: on_event(d, "agent_started")),
        (Events.AGENT_COMPLETED, lambda d: on_event(d, "agent_completed")),
        (Events.TOOL_CALLED, lambda d: on_event(d, "tool_called")),
        (Events.TOOL_COMPLETED, lambda d: on_event(d, "tool_completed")),
        (Events.WAKE_WORD_DETECTED, lambda d: on_event(d, "wake_word_detected")),
        (Events.TRANSCRIPT_READY, lambda d: on_event(d, "transcript_ready")),
        (Events.TTS_STARTED, lambda d: on_event(d, "tts_started")),
        (Events.TTS_COMPLETE, lambda d: on_event(d, "tts_complete")),
        (Events.MEMORY_STORED, lambda d: on_event(d, "memory_stored")),
        (Events.NOTIFICATION, lambda d: on_event(d, "notification")),
        (Events.APPROVAL_REQUIRED, lambda d: on_event(d, "approval_required")),
        (Events.ERROR, lambda d: on_event(d, "error")),
    ]

    for event, handler in subscriptions:
        event_bus.subscribe(event, handler)

    # Send initial status
    await ws_manager.send_to(websocket, "connected", {
        "message": "J.A.Y. connected",
        "version": "0.1.0",
    })

    try:
        while True:
            # Receive messages from frontend
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                msg_type = msg.get("type", "")

                if msg_type == "ping":
                    await ws_manager.send_to(websocket, "pong", {"ts": msg.get("ts")})

                elif msg_type == "voice_audio":
                    # Handle voice audio chunk
                    audio_b64 = msg.get("audio", "")
                    if audio_b64:
                        import base64
                        audio_bytes = base64.b64decode(audio_b64)
                        from app.voice.stt import stt
                        text = await stt.transcribe_audio(audio_bytes)
                        await ws_manager.send_to(websocket, "transcript", {"text": text})

                elif msg_type == "approve_action":
                    from app.core.security import approval_manager
                    action_id = msg.get("action_id")
                    if action_id:
                        approval_manager.approve(action_id)
                        await ws_manager.send_to(websocket, "action_approved", {"id": action_id})

                elif msg_type == "deny_action":
                    from app.core.security import approval_manager
                    action_id = msg.get("action_id")
                    if action_id:
                        approval_manager.deny(action_id)
                        await ws_manager.send_to(websocket, "action_denied", {"id": action_id})

            except json.JSONDecodeError:
                pass
            except Exception as e:
                logger.error(f"WS message error: {e}")

    except WebSocketDisconnect:
        for event, handler in subscriptions:
            event_bus.unsubscribe(event, handler)
        ws_manager.disconnect(websocket)
