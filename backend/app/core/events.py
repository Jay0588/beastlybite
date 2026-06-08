"""
J.A.Y. Event Bus — internal pub/sub for cross-module communication
"""
import asyncio
from typing import Dict, List, Callable, Any
import logging

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event: str, handler: Callable):
        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(handler)

    def unsubscribe(self, event: str, handler: Callable):
        if event in self._subscribers:
            self._subscribers[event].remove(handler)

    async def publish(self, event: str, data: Any = None):
        handlers = self._subscribers.get(event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Event handler error for {event}: {e}")

    def publish_sync(self, event: str, data: Any = None):
        handlers = self._subscribers.get(event, [])
        for handler in handlers:
            try:
                if not asyncio.iscoroutinefunction(handler):
                    handler(data)
            except Exception as e:
                logger.error(f"Sync event handler error for {event}: {e}")


# Global event bus instance
event_bus = EventBus()

# Standard events
class Events:
    # Conversation
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"
    STREAM_CHUNK = "stream.chunk"
    STREAM_COMPLETE = "stream.complete"

    # Voice
    WAKE_WORD_DETECTED = "voice.wake_word"
    SPEECH_STARTED = "voice.speech_started"
    SPEECH_ENDED = "voice.speech_ended"
    TRANSCRIPT_READY = "voice.transcript"
    TTS_STARTED = "voice.tts_started"
    TTS_COMPLETE = "voice.tts_complete"

    # Agents
    AGENT_STARTED = "agent.started"
    AGENT_THINKING = "agent.thinking"
    AGENT_COMPLETED = "agent.completed"
    AGENT_ERROR = "agent.error"
    TOOL_CALLED = "tool.called"
    TOOL_COMPLETED = "tool.completed"

    # Memory
    MEMORY_STORED = "memory.stored"
    MEMORY_RETRIEVED = "memory.retrieved"

    # Desktop
    APP_OPENED = "desktop.app_opened"
    FILE_OPERATION = "desktop.file_op"

    # System
    APPROVAL_REQUIRED = "system.approval_required"
    APPROVAL_RESOLVED = "system.approval_resolved"
    NOTIFICATION = "system.notification"
    ERROR = "system.error"
