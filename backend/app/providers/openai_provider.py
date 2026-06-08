"""
J.A.Y. OpenAI-Compatible Provider  (OpenAI  +  OpenRouter)
────────────────────────────────────────────────────────────────────────────────
OpenRouterProvider extends OpenAIProvider with:
  • Quota pre-check  — refuses a request before it hits the API if exhausted
  • Quota recording  — increments daily/RPM counters on every success
  • Error detection  — marks a model exhausted on 429 / quota phrases
  • X-Title header   — required by OpenRouter for free-tier access
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator, List, Optional

from openai import AsyncOpenAI, APIStatusError

from app.providers.base import (
    BaseProvider,
    CompletionRequest,
    CompletionResponse,
    MessageRole,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


# ── OpenAI Provider ────────────────────────────────────────────────────────────

class OpenAIProvider(BaseProvider):
    name = "openai"
    supports_streaming = True
    supports_tools = True

    def __init__(
        self,
        api_key:  Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key  = api_key  or settings.OPENAI_API_KEY or "sk-none"
        self.base_url = base_url
        self.client   = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _build_messages(self, request: CompletionRequest) -> List[dict]:
        messages: List[dict] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        for msg in request.messages:
            m: dict = {"role": msg.role.value, "content": msg.content}
            if msg.tool_calls:
                m["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                m["tool_call_id"] = msg.tool_call_id
                m["role"] = "tool"
            messages.append(m)
        return messages

    # ── Completion ─────────────────────────────────────────────────────────────

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        model    = request.model or "gpt-4o"
        messages = self._build_messages(request)

        kwargs: dict = dict(
            model=model,
            messages=messages,
            temperature=request.temperature,
            stream=False,
        )
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        if request.tools:
            kwargs["tools"]       = request.tools
            kwargs["tool_choice"] = request.tool_choice or "auto"

        response = await self.client.chat.completions.create(**kwargs)
        choice   = response.choices[0]
        content  = choice.message.content or ""

        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name":      tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in choice.message.tool_calls
            ]

        return CompletionResponse(
            content=content,
            model=model,
            provider=self.name,
            tokens_used=response.usage.total_tokens if response.usage else 0,
            finish_reason=choice.finish_reason or "stop",
            tool_calls=tool_calls,
        )

    async def stream(self, request: CompletionRequest) -> AsyncGenerator[str, None]:
        model    = request.model or "gpt-4o"
        messages = self._build_messages(request)

        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=request.temperature,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    async def is_available(self) -> bool:
        if not self.api_key or self.api_key == "sk-none":
            return False
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False


# ── OpenRouter Provider ────────────────────────────────────────────────────────

class OpenRouterProvider(OpenAIProvider):
    """
    OpenRouter-specific subclass that:
      1. Injects required headers (X-Title, HTTP-Referer)
      2. Runs quota pre-checks before every request
      3. Records usage / errors in the quota tracker after every request
    """

    name = "openrouter"

    # These headers are required by OpenRouter for free-tier models
    _EXTRA_HEADERS = {
        "X-Title":      "J.A.Y. Personal AI OS",
        "HTTP-Referer": "https://github.com/jay-ai-os",
    }

    def __init__(self):
        super().__init__(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )
        # Re-create client with extra headers
        self.client = AsyncOpenAI(
            api_key=self.api_key or "sk-none",
            base_url="https://openrouter.ai/api/v1",
            default_headers=self._EXTRA_HEADERS,
        )

    # ── Availability ───────────────────────────────────────────────────────────

    async def is_available(self) -> bool:
        """Available as long as the API key is configured — no live ping needed."""
        return bool(self.api_key and self.api_key != "sk-none")

    async def is_model_available(self, model_id: str) -> tuple[bool, str]:
        """
        Full availability check for a specific model:
        key present  AND  quota not exhausted.
        """
        if not await self.is_available():
            return False, "OpenRouter API key not configured"
        from app.providers.quota_tracker import quota_tracker
        return await quota_tracker.is_available(model_id)

    # ── Completion with quota tracking ─────────────────────────────────────────

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        model = request.model or "meta-llama/llama-3.1-8b-instruct:free"

        # Pre-check quota
        await self._pre_check(model)

        try:
            response = await super().complete(request)
            # Record success
            await self._record_success(
                model,
                tokens_in=0,                         # OpenAI client doesn't expose prompt tokens separately here
                tokens_out=response.tokens_used,
            )
            return response

        except APIStatusError as e:
            await self._handle_api_error(model, e.status_code, e.message)
            raise

        except Exception as e:
            await self._record_error(model, is_quota=False)
            raise

    async def stream(self, request: CompletionRequest) -> AsyncGenerator[str, None]:
        model = request.model or "meta-llama/llama-3.1-8b-instruct:free"

        # Pre-check quota
        await self._pre_check(model)

        total_chunks = 0
        try:
            async for chunk in super().stream(request):
                total_chunks += 1
                yield chunk
            await self._record_success(model, tokens_out=total_chunks)

        except APIStatusError as e:
            await self._handle_api_error(model, e.status_code, e.message)
            raise

        except Exception as e:
            await self._record_error(model, is_quota=False)
            raise

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _pre_check(self, model_id: str) -> None:
        """Raise immediately if the model quota is exhausted."""
        from app.providers.quota_tracker import quota_tracker
        available, reason = await quota_tracker.is_available(model_id)
        if not available:
            raise RuntimeError(
                f"OpenRouter/{model_id} quota exhausted: {reason}"
            )

    async def _record_success(
        self, model_id: str, tokens_in: int = 0, tokens_out: int = 0
    ) -> None:
        from app.providers.quota_tracker import quota_tracker
        await quota_tracker.record_success(model_id, tokens_in, tokens_out)

    async def _record_error(self, model_id: str, is_quota: bool) -> None:
        from app.providers.quota_tracker import quota_tracker
        await quota_tracker.record_error(model_id, is_quota_error=is_quota)

    async def _handle_api_error(
        self, model_id: str, status_code: int, body: str
    ) -> None:
        from app.providers.quota_tracker import quota_tracker
        is_quota = quota_tracker.is_quota_error_response(status_code, body)
        await quota_tracker.record_error(model_id, is_quota_error=is_quota)
        if is_quota:
            logger.warning(
                f"[OpenRouter] Quota/rate-limit error for {model_id} "
                f"(HTTP {status_code}) — model blocked for 1h"
            )
        else:
            logger.error(
                f"[OpenRouter] API error for {model_id}: HTTP {status_code} — {body[:200]}"
            )
