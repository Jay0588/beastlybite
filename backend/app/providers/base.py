"""
J.A.Y. AI Provider Base — Abstraction layer for all LLM providers
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None


class CompletionRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    tools: Optional[List[Dict]] = None
    tool_choice: Optional[str] = None
    system_prompt: Optional[str] = None


class CompletionResponse(BaseModel):
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    finish_reason: str = "stop"
    tool_calls: Optional[List[Dict]] = None


class BaseProvider(ABC):
    name: str = "base"
    supports_streaming: bool = True
    supports_tools: bool = True

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        pass

    @abstractmethod
    async def stream(self, request: CompletionRequest) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        pass

    async def embed(self, text: str) -> List[float]:
        raise NotImplementedError(f"{self.name} does not support embeddings")
