"""
J.A.Y. Provider Manager — Intelligent routing, fallback chain, quota tracking
─────────────────────────────────────────────────────────────────────────────

Routing logic (per request):

  1. Classify the task  (TaskClassifier)
  2. Pick best Ollama model for that task that fits in RAM
  3. If Ollama unavailable / model not installed → try OpenRouter (free first)
  4. If OpenRouter free quota exhausted → try next free OpenRouter model
  5. If all free OpenRouter exhausted → try paid OpenRouter (if key set)
  6. If everything fails → raise with clear message

Priority table:
  ┌──────────────────┬──────────────────────────────────────────────────┐
  │ Task             │ Primary              → Fallback chain             │
  ├──────────────────┼──────────────────────────────────────────────────┤
  │ QUICK / VOICE    │ llama3.2:3b (2GB)   → mistral:7b → OR free       │
  │ CHAT             │ llama3.1:8b (4.7GB) → mistral:7b → OR free       │
  │ CODE             │ deepseek-coder (5GB)→ codellama  → OR free       │
  │ CODE_HEAVY       │ deepseek-coder (5GB)→ OR deepseek-r1:free        │
  │ PLAN / ANALYSIS  │ llama3.1:8b (4.7GB) → mixtral q2 → OR 70B free  │
  │ TRADING          │ mistral:7b (4.1GB)  → llama3.1:8b → OR 70B free │
  │ RESEARCH         │ llama3.1:8b (4.7GB) → OR gemma-3-27b:free        │
  │ CREATIVE         │ mistral:7b (4.1GB)  → OR llama-3.3-70b:free      │
  └──────────────────┴──────────────────────────────────────────────────┘
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import AsyncGenerator, Dict, List, Optional, Tuple

from app.core.config import settings
from app.providers.base import (
    BaseProvider,
    ChatMessage,
    CompletionRequest,
    CompletionResponse,
    MessageRole,
)
from app.providers.gemini_provider import GeminiProvider
from app.providers.model_registry import (
    ModelSpec,
    TaskType,
    best_ollama_for_task,
    best_openrouter_for_task,
    get_model,
    models_for_provider,
    OPENROUTER_MODELS,
)
from app.providers.ollama_provider import OllamaProvider
from app.providers.openai_provider import OpenAIProvider, OpenRouterProvider
from app.providers.task_classifier import classify, task_label

logger = logging.getLogger(__name__)


# ── Routing decision record ────────────────────────────────────────────────────

@dataclass
class RoutingDecision:
    task_type: TaskType
    provider: str
    model_id: str
    model_name: str
    reason: str
    fallback_used: bool = False
    fallback_reason: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        return {
            "task_type": self.task_type.value,
            "task_label": task_label(self.task_type),
            "provider": self.provider,
            "model_id": self.model_id,
            "model_name": self.model_name,
            "reason": self.reason,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "timestamp": self.timestamp,
        }


# ── Per-model usage stats (in-memory, reset on restart) ───────────────────────

@dataclass
class ModelUsageStats:
    model_id: str
    requests: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    errors: int = 0
    last_used: Optional[str] = None
    avg_latency_ms: float = 0.0
    _latency_sum: float = field(default=0.0, repr=False)

    def record(self, tokens_in: int = 0, tokens_out: int = 0,
               latency_ms: float = 0, error: bool = False):
        self.requests += 1
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        self.last_used = datetime.utcnow().isoformat()
        if error:
            self.errors += 1
        if latency_ms > 0:
            self._latency_sum += latency_ms
            self.avg_latency_ms = round(self._latency_sum / self.requests, 1)

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "requests": self.requests,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "errors": self.errors,
            "last_used": self.last_used,
            "avg_latency_ms": self.avg_latency_ms,
        }


class ProviderManager:
    """
    Central AI brain for J.A.Y.
    Classifies tasks → selects optimal model → executes with full fallback chain.
    """

    def __init__(self):
        # Provider instances (one per backend type)
        self._ollama   = OllamaProvider()
        self._openrouter = OpenRouterProvider()
        self._openai   = OpenAIProvider()
        self._gemini   = GeminiProvider()

        self._provider_map: Dict[str, BaseProvider] = {
            "ollama":      self._ollama,
            "openrouter":  self._openrouter,
            "openai":      self._openai,
            "gemini":      self._gemini,
        }

        # Usage tracking
        self._usage: Dict[str, ModelUsageStats] = {}

        # Last routing decision (for UI display)
        self.last_decision: Optional[RoutingDecision] = None

        # Availability cache: {provider_name: (is_available, expires_at)}
        self._avail_cache: Dict[str, Tuple[bool, float]] = {}
        self._avail_ttl = 30.0  # seconds

        # Installed Ollama model cache
        self._installed_ollama: List[str] = []
        self._installed_cache_expires = 0.0

    # ── Public API ─────────────────────────────────────────────────────────────

    async def complete(
        self,
        request: CompletionRequest,
        *,
        task_hint: Optional[TaskType] = None,
        force_provider: Optional[str] = None,
        force_model: Optional[str] = None,
    ) -> CompletionResponse:
        """
        Smart completion: classify → route → execute → fallback on error.
        """
        decision, provider, model_id = await self._resolve(
            request, task_hint, force_provider, force_model
        )
        self.last_decision = decision
        logger.info(
            f"[ROUTE] {decision.task_label if hasattr(decision,'task_label') else decision.task_type.value}"
            f" → {decision.provider}/{decision.model_id}"
            + (f" (fallback: {decision.fallback_reason})" if decision.fallback_used else "")
        )

        request = request.model_copy(update={"model": model_id})
        t0 = time.monotonic()
        try:
            response = await provider.complete(request)
            latency = (time.monotonic() - t0) * 1000
            self._stats(model_id).record(
                tokens_out=response.tokens_used, latency_ms=latency
            )
            return response
        except Exception as e:
            self._stats(model_id).record(error=True)
            logger.warning(f"[ROUTE] {decision.provider}/{model_id} failed: {e} — trying fallbacks")
            return await self._fallback_complete(request, decision, skip_model=model_id)

    async def stream(
        self,
        request: CompletionRequest,
        *,
        task_hint: Optional[TaskType] = None,
        force_provider: Optional[str] = None,
        force_model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Smart streaming: classify → route → stream → fallback to non-stream on error.
        """
        decision, provider, model_id = await self._resolve(
            request, task_hint, force_provider, force_model
        )
        self.last_decision = decision
        logger.info(
            f"[STREAM] {decision.task_type.value} → {decision.provider}/{decision.model_id}"
        )

        request = request.model_copy(update={"model": model_id, "stream": True})
        try:
            async for chunk in provider.stream(request):
                yield chunk
            self._stats(model_id).record()
        except Exception as e:
            self._stats(model_id).record(error=True)
            logger.warning(f"[STREAM] {model_id} failed mid-stream: {e} — falling back")
            # Fall back to non-streaming complete, yield full response at once
            try:
                fb_resp = await self._fallback_complete(
                    request, decision, skip_model=model_id
                )
                yield fb_resp.content
            except Exception as fe:
                yield f"\n\n*[J.A.Y.] All AI providers failed: {fe}*"

    async def classify_request(self, message: str) -> TaskType:
        return classify(message)

    async def list_available(self) -> List[dict]:
        """List all providers with their availability and installed models."""
        result = []
        for name, provider in self._provider_map.items():
            available = await self._is_available(name)
            entry: dict = {
                "name": name,
                "available": available,
                "supports_streaming": provider.supports_streaming,
                "supports_tools": provider.supports_tools,
            }
            if name == "ollama" and available:
                entry["installed_models"] = await self._get_installed_ollama()
                entry["recommended_models"] = [
                    m.id for m in models_for_provider("ollama")
                    if m.fits_12gb and m.id in entry["installed_models"]
                ]
            if name == "openrouter":
                entry["free_models"] = [
                    m.id for m in OPENROUTER_MODELS if m.is_free
                ]
                entry["quota_stats"] = self._openrouter_quota_summary()
            result.append(entry)
        return result

    def get_usage_stats(self) -> List[dict]:
        return [s.to_dict() for s in self._usage.values() if s.requests > 0]

    def get_last_decision(self) -> Optional[dict]:
        return self.last_decision.to_dict() if self.last_decision else None

    def get_provider(self, name: str) -> Optional[BaseProvider]:
        return self._provider_map.get(name)

    # ── Routing core ───────────────────────────────────────────────────────────

    async def _resolve(
        self,
        request: CompletionRequest,
        task_hint: Optional[TaskType],
        force_provider: Optional[str],
        force_model: Optional[str],
    ) -> Tuple[RoutingDecision, BaseProvider, str]:
        """
        Determine the best (provider, model) pair for this request.
        Returns (RoutingDecision, provider_instance, model_id).
        """
        # Forced override — trust the caller
        if force_provider and force_model:
            provider = self._provider_map.get(force_provider)
            if not provider:
                raise ValueError(f"Unknown provider: {force_provider}")
            decision = RoutingDecision(
                task_type=task_hint or TaskType.CHAT,
                provider=force_provider,
                model_id=force_model,
                model_name=force_model,
                reason="Forced by caller",
            )
            return decision, provider, force_model

        # Classify task
        last_user_msg = next(
            (m.content for m in reversed(request.messages) if m.role == MessageRole.USER),
            "",
        )
        task = task_hint or classify(last_user_msg)

        # Build candidate chain for this task
        chain = await self._build_candidate_chain(task)

        for candidate_provider, candidate_model, reason in chain:
            provider_inst = self._provider_map.get(candidate_provider)
            if not provider_inst:
                continue
            if not await self._is_available(candidate_provider):
                continue
            # For Ollama: verify model is actually installed
            if candidate_provider == "ollama":
                installed = await self._get_installed_ollama()
                if candidate_model not in installed:
                    logger.debug(f"[ROUTE] Ollama model {candidate_model} not installed — skipping")
                    continue

            decision = RoutingDecision(
                task_type=task,
                provider=candidate_provider,
                model_id=candidate_model,
                model_name=get_model(candidate_model).display_name
                           if get_model(candidate_model) else candidate_model,
                reason=reason,
            )
            return decision, provider_inst, candidate_model

        raise RuntimeError(
            "No AI provider available.\n"
            "• For local AI: install Ollama (ollama.ai) and run: ollama pull llama3.2:3b\n"
            "• For cloud AI: set OPENROUTER_API_KEY in backend/.env"
        )

    async def _build_candidate_chain(
        self, task: TaskType
    ) -> List[Tuple[str, str, str]]:
        """
        Returns ordered list of (provider, model_id, reason) to try for a task.
        Ollama first (local, free, private), then OpenRouter free, then paid.
        """
        chain: List[Tuple[str, str, str]] = []

        # ── 1. Best Ollama model for this task ──────────────────────────────
        ollama_spec = best_ollama_for_task(task, max_ram_gb=7.0)
        if ollama_spec:
            chain.append((
                "ollama",
                ollama_spec.id,
                f"Best local model for {task_label(task)} "
                f"(score {ollama_spec.scores.get(task, 0)}/10, {ollama_spec.ram_gb}GB RAM)",
            ))

        # ── 2. Second-best Ollama (in case first not installed) ─────────────
        installed = await self._get_installed_ollama()
        for spec in self._rank_ollama_for_task(task):
            if spec.id != (ollama_spec.id if ollama_spec else "") and spec.id in installed:
                chain.append((
                    "ollama",
                    spec.id,
                    f"Fallback local model for {task_label(task)}",
                ))
                break

        # ── 3. Best FREE OpenRouter model ───────────────────────────────────
        if await self._is_available("openrouter"):
            from app.providers.quota_tracker import quota_tracker

            or_free = best_openrouter_for_task(task, free_only=True)
            if or_free:
                avail, reason = await quota_tracker.is_available(or_free.id)
                if avail:
                    chain.append((
                        "openrouter",
                        or_free.id,
                        f"Best free cloud model for {task_label(task)} (score {or_free.scores.get(task,0)}/10)",
                    ))
                else:
                    logger.debug(f"[ROUTE] OR/{or_free.id} skipped: {reason}")

            # ── 4. All other free OpenRouter models as deeper fallbacks ─────
            for spec in self._rank_openrouter_for_task(task, free_only=True):
                if spec.id == (or_free.id if or_free else ""):
                    continue
                avail, reason = await quota_tracker.is_available(spec.id)
                if avail:
                    chain.append((
                        "openrouter",
                        spec.id,
                        f"Free cloud fallback for {task_label(task)}",
                    ))
                else:
                    logger.debug(f"[ROUTE] OR/{spec.id} skipped: {reason}")

            # ── 5. Paid OpenRouter — only if OPENROUTER_API_KEY is set ──────
            if settings.OPENROUTER_API_KEY:
                or_paid = best_openrouter_for_task(task, free_only=False)
                if or_paid and not or_paid.is_free:
                    chain.append((
                        "openrouter",
                        or_paid.id,
                        f"Paid cloud model — all free options exhausted",
                    ))

        # ── 6. Gemini as last resort ─────────────────────────────────────────
        if settings.GOOGLE_API_KEY and await self._is_available("gemini"):
            chain.append(("gemini", "gemini-1.5-flash", "Gemini last resort"))

        return chain

    async def _fallback_complete(
        self,
        request: CompletionRequest,
        original_decision: RoutingDecision,
        skip_model: str,
    ) -> CompletionResponse:
        """Try every remaining candidate after primary failed."""
        chain = await self._build_candidate_chain(original_decision.task_type)
        for candidate_provider, candidate_model, reason in chain:
            if candidate_model == skip_model:
                continue
            provider_inst = self._provider_map.get(candidate_provider)
            if not provider_inst:
                continue
            if not await self._is_available(candidate_provider):
                continue
            try:
                req = request.model_copy(update={"model": candidate_model})
                t0 = time.monotonic()
                resp = await provider_inst.complete(req)
                latency = (time.monotonic() - t0) * 1000
                self._stats(candidate_model).record(latency_ms=latency)

                # Update decision record
                self.last_decision = RoutingDecision(
                    task_type=original_decision.task_type,
                    provider=candidate_provider,
                    model_id=candidate_model,
                    model_name=get_model(candidate_model).display_name
                               if get_model(candidate_model) else candidate_model,
                    reason=reason,
                    fallback_used=True,
                    fallback_reason=f"Primary {skip_model} failed",
                )
                logger.info(f"[FALLBACK] Success with {candidate_provider}/{candidate_model}")
                return resp
            except Exception as e:
                self._stats(candidate_model).record(error=True)
                logger.warning(f"[FALLBACK] {candidate_model} also failed: {e}")
                continue

        raise RuntimeError(
            f"All providers failed for task '{original_decision.task_type.value}'. "
            "Check that Ollama is running or OpenRouter key is set."
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _is_available(self, provider_name: str) -> bool:
        """Cached availability check (30s TTL)."""
        now = time.monotonic()
        cached = self._avail_cache.get(provider_name)
        if cached and now < cached[1]:
            return cached[0]

        provider = self._provider_map.get(provider_name)
        if not provider:
            return False
        try:
            result = await asyncio.wait_for(provider.is_available(), timeout=4.0)
        except Exception:
            result = False

        self._avail_cache[provider_name] = (result, now + self._avail_ttl)
        return result

    async def _get_installed_ollama(self) -> List[str]:
        """Cached list of installed Ollama models."""
        now = time.monotonic()
        if now < self._installed_cache_expires:
            return self._installed_ollama
        try:
            models = await self._ollama.list_models()
            self._installed_ollama = models
            self._installed_cache_expires = now + 60.0  # refresh every 60s
        except Exception:
            pass
        return self._installed_ollama

    def _rank_ollama_for_task(self, task: TaskType) -> List[ModelSpec]:
        from app.providers.model_registry import OLLAMA_MODELS
        candidates = [m for m in OLLAMA_MODELS if m.fits_12gb and m.ram_gb <= 7.0]
        speed_order = {"fast": 0, "medium": 1, "slow": 2}
        candidates.sort(key=lambda m: (-m.scores.get(task, 0), speed_order.get(m.speed, 1)))
        return candidates

    def _rank_openrouter_for_task(
        self, task: TaskType, free_only: bool = True
    ) -> List[ModelSpec]:
        candidates = [
            m for m in OPENROUTER_MODELS if not free_only or m.is_free
        ]
        speed_order = {"fast": 0, "medium": 1, "slow": 2}
        candidates.sort(key=lambda m: (-m.scores.get(task, 0), speed_order.get(m.speed, 1)))
        return candidates

    def _stats(self, model_id: str) -> ModelUsageStats:
        if model_id not in self._usage:
            self._usage[model_id] = ModelUsageStats(model_id=model_id)
        return self._usage[model_id]

    def _openrouter_quota_exceeded(self, model_id: str) -> bool:
        """Delegate to the real quota tracker (sync convenience wrapper)."""
        from app.providers.quota_tracker import quota_tracker
        # Use the cached status dict rather than firing an async call here
        for entry in quota_tracker.get_status():
            if entry["model_id"] == model_id:
                return not entry["available"]
        return False

    def _openrouter_quota_summary(self) -> dict:
        from app.providers.quota_tracker import quota_tracker
        return {
            entry["model_id"]: {
                "available":      entry["available"],
                "daily_requests": entry["daily_requests"],
                "daily_req_pct":  entry["daily_req_pct"],
                "daily_token_pct": entry["daily_token_pct"],
                "rpm_current":    entry["rpm_current"],
                "blocked":        entry["blocked"],
                "exhausted_reason": entry["exhausted_reason"],
            }
            for entry in quota_tracker.get_status()
        }

    def invalidate_availability_cache(self):
        """Force re-check on next request (call after config change)."""
        self._avail_cache.clear()
        self._installed_cache_expires = 0.0


# ── Global singleton ───────────────────────────────────────────────────────────
provider_manager = ProviderManager()
