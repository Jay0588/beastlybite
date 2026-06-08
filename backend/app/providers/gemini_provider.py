"""
J.A.Y. Google Gemini Provider
"""
from typing import AsyncGenerator, List
import logging
import google.generativeai as genai
from app.providers.base import BaseProvider, CompletionRequest, CompletionResponse
from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    name = "gemini"
    supports_streaming = True
    supports_tools = True

    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def _get_model(self, model_name: str = None):
        name = model_name or "gemini-1.5-flash"
        return genai.GenerativeModel(name)

    def _build_history(self, request: CompletionRequest):
        history = []
        system = request.system_prompt or ""
        messages = request.messages

        for msg in messages[:-1]:  # all but last
            role = "user" if msg.role.value == "user" else "model"
            history.append({"role": role, "parts": [msg.content]})

        last = messages[-1].content if messages else ""
        if system:
            last = f"{system}\n\n{last}"
        return history, last

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        model_name = request.model or "gemini-1.5-flash"
        model = self._get_model(model_name)
        history, last_msg = self._build_history(request)

        chat = model.start_chat(history=history)
        response = await chat.send_message_async(last_msg)
        content = response.text or ""

        return CompletionResponse(
            content=content,
            model=model_name,
            provider=self.name,
            finish_reason="stop",
        )

    async def stream(self, request: CompletionRequest) -> AsyncGenerator[str, None]:
        model_name = request.model or "gemini-1.5-flash"
        model = self._get_model(model_name)
        history, last_msg = self._build_history(request)

        chat = model.start_chat(history=history)
        async for chunk in await chat.send_message_async(last_msg, stream=True):
            if chunk.text:
                yield chunk.text

    async def is_available(self) -> bool:
        return bool(self.api_key)
