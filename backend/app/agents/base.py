"""
J.A.Y. Base Agent — All agents inherit from this
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator
from pydantic import BaseModel
from enum import Enum
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETE = "complete"
    ERROR = "error"


class AgentMessage(BaseModel):
    id: str = ""
    agent: str
    content: str
    type: str = "thought"  # thought, action, result, error
    metadata: Dict = {}
    timestamp: str = ""

    def __init__(self, **data):
        if not data.get("id"):
            data["id"] = str(uuid.uuid4())
        if not data.get("timestamp"):
            data["timestamp"] = datetime.utcnow().isoformat()
        super().__init__(**data)


class AgentContext(BaseModel):
    conversation_id: str
    user_query: str
    messages: List[Dict] = []
    memory_context: str = ""
    project_context: Optional[Dict] = None
    available_tools: List[str] = []
    metadata: Dict = {}


class AgentResult(BaseModel):
    agent: str
    success: bool
    output: Any
    messages: List[AgentMessage] = []
    tools_used: List[str] = []
    tokens_used: int = 0
    error: Optional[str] = None


class BaseAgent(ABC):
    name: str = "base"
    description: str = "Base agent"
    capabilities: List[str] = []

    def __init__(self, provider_manager=None, tool_registry=None, memory_manager=None):
        self.provider_manager = provider_manager
        self.tool_registry = tool_registry
        self.memory_manager = memory_manager
        self.status = AgentStatus.IDLE
        self._messages: List[AgentMessage] = []

    def _emit(self, content: str, type_: str = "thought", metadata: Dict = {}):
        msg = AgentMessage(agent=self.name, content=content, type=type_, metadata=metadata)
        self._messages.append(msg)
        logger.debug(f"[{self.name}] {type_}: {content[:100]}")
        return msg

    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResult:
        pass

    async def _llm(
        self,
        messages: List[Dict],
        system: Optional[str] = None,
        temperature: float = 0.7,
        tools: Optional[List[Dict]] = None,
    ) -> str:
        from app.providers.base import CompletionRequest, ChatMessage, MessageRole
        chat_messages = []
        for m in messages:
            role = MessageRole.USER if m["role"] == "user" else MessageRole.ASSISTANT
            if m["role"] == "system":
                role = MessageRole.SYSTEM
            chat_messages.append(ChatMessage(role=role, content=m["content"]))

        req = CompletionRequest(
            messages=chat_messages,
            system_prompt=system,
            temperature=temperature,
            tools=tools,
        )
        response = await self.provider_manager.complete(req)
        return response.content

    async def _stream_llm(
        self,
        messages: List[Dict],
        system: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        from app.providers.base import CompletionRequest, ChatMessage, MessageRole
        chat_messages = []
        for m in messages:
            role_val = m["role"]
            if role_val == "user":
                role = MessageRole.USER
            elif role_val == "assistant":
                role = MessageRole.ASSISTANT
            else:
                role = MessageRole.SYSTEM
            chat_messages.append(ChatMessage(role=role, content=m["content"]))

        req = CompletionRequest(
            messages=chat_messages,
            system_prompt=system,
            temperature=temperature,
            stream=True,
        )
        async for chunk in self.provider_manager.stream(req):
            yield chunk
