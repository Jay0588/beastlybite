"""
J.A.Y. Ollama Provider
──────────────────────────────────────────────────────────────────
Enhancements over original:
  • Dynamic model switching — swaps model per request, no restart
  • RAM guard — refuses to load a model that exceeds the 12 GB budget
  • Pull-on-demand — auto-pulls a missing model (with progress events)
  • Running-model tracker — knows which model Ollama currently has loaded
  • Detailed model info (size, family, parameter count)
  • Graceful unload — can explicitly eject a model to free RAM
  • Structured logging of every switch for the UI activity feed
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Dict, List, Optional

import httpx

from app.providers.base import (
    BaseProvider,
    CompletionRequest,
    CompletionResponse,
    MessageRole,
)
from app.core.config import settings
from app.core.events import event_bus, Events

logger = logging.getLogger(__name__)

# Maximum RAM we're willing to let a single Ollama model consume (GB).
# On a 12 GB machine: OS ~3 GB + backend ~0.8 GB → budget ≈ 7 GB
_RAM_BUDGET_GB: float = 7.0

# How long (seconds) to wait for a model to load before timing out
_LOAD_TIMEOUT: float = 180.0
# How long to wait for a normal completion
_COMPLETE_TIMEOUT: float = 120.0
# How long to wait for a streaming response to start
_STREAM_TIMEOUT: float = 180.0


class OllamaProvider(BaseProvider):
    """
    Full-featured Ollama provider with per-request model routing,
    RAM safety checks, and pull-on-demand.
    """

    name = "ollama"
    supports_streaming = True
    supports_tools = False  # tool support depends on the loaded model

    def __init__(self):
        self.base_url: str = settings.OLLAMA_BASE_URL
        self.default_model: str = settings.DEFAULT_MODEL

        # Track what Ollama currently has in memory
        self._active_model: Optional[str] = None
        self._active_model_ram_gb: float = 0.0

        # Cache: model_id → info dict from /api/show
        self._model_info_cache: Dict[str, dict] = {}

        # Set of models currently being pulled (to avoid duplicate pulls)
        self._pulling: set[str] = set()

    # ── Core completion ────────────────────────────────────────────────────────

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        model = request.model or self.default_model
        await self._ensure_model_ready(model)

        messages = self._build_messages(request)
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens or 4096,
                "num_ctx": self._context_size_for(model),
            },
        }

        async with httpx.AsyncClient(timeout=_COMPLETE_TIMEOUT) as client:
            try:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
            except httpx.TimeoutException:
                raise RuntimeError(f"Ollama/{model} timed out after {_COMPLETE_TIMEOUT}s")
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"Ollama/{model} HTTP {e.response.status_code}: {e.response.text[:200]}")

        data = resp.json()
        content = data.get("message", {}).get("content", "")
        self._active_model = model

        return CompletionResponse(
            content=content,
            model=model,
            provider=self.name,
            tokens_used=data.get("eval_count", 0),
            finish_reason="stop",
        )

    async def stream(self, request: CompletionRequest) -> AsyncGenerator[str, None]:
        model = request.model or self.default_model
        await self._ensure_model_ready(model)

        messages = self._build_messages(request)
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": request.temperature,
                "num_ctx": self._context_size_for(model),
            },
        }

        async with httpx.AsyncClient(timeout=_STREAM_TIMEOUT) as client:
            try:
                async with client.stream(
                    "POST", f"{self.base_url}/api/chat", json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            yield chunk
                        if data.get("done", False):
                            self._active_model = model
                            break
            except httpx.TimeoutException:
                raise RuntimeError(f"Ollama/{model} stream timed out")
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"Ollama/{model} stream error {e.response.status_code}")

    # ── Model management ───────────────────────────────────────────────────────

    async def ensure_model_pulled(
        self,
        model_id: str,
        *,
        on_progress: Optional[callable] = None,
    ) -> bool:
        """
        Pull a model if it is not already installed.
        Streams pull progress and fires Events.NOTIFICATION.
        Returns True if the model is ready.
        """
        installed = await self.list_models()
        if model_id in installed:
            return True

        if model_id in self._pulling:
            logger.info(f"[Ollama] Already pulling {model_id}, waiting…")
            for _ in range(120):                # wait up to 2 minutes
                await asyncio.sleep(1)
                if model_id not in self._pulling:
                    break
            return model_id in await self.list_models()

        self._pulling.add(model_id)
        logger.info(f"[Ollama] Pulling model: {model_id}")
        await event_bus.publish(Events.NOTIFICATION, {
            "title": "Downloading model",
            "message": f"Pulling {model_id} from Ollama…",
            "level": "info",
        })

        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/pull",
                    json={"name": model_id, "stream": True},
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        status = data.get("status", "")
                        if on_progress:
                            on_progress(data)
                        if "completed" in data and "total" in data:
                            pct = int(data["completed"] / max(data["total"], 1) * 100)
                            logger.debug(f"[Ollama] Pull {model_id}: {pct}%")
                        if status == "success":
                            logger.info(f"[Ollama] Pull complete: {model_id}")
                            await event_bus.publish(Events.NOTIFICATION, {
                                "title": "Model ready",
                                "message": f"{model_id} downloaded successfully",
                                "level": "success",
                            })
                            return True
            return model_id in await self.list_models()

        except Exception as e:
            logger.error(f"[Ollama] Pull failed for {model_id}: {e}")
            await event_bus.publish(Events.NOTIFICATION, {
                "title": "Model pull failed",
                "message": f"Could not download {model_id}: {e}",
                "level": "error",
            })
            return False
        finally:
            self._pulling.discard(model_id)

    async def unload_model(self, model_id: str) -> bool:
        """
        Explicitly unload a model from Ollama's memory to free RAM.
        Uses the /api/generate keep_alive=0 trick.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": model_id, "keep_alive": 0},
                )
            if self._active_model == model_id:
                self._active_model = None
                self._active_model_ram_gb = 0.0
            logger.info(f"[Ollama] Unloaded {model_id}")
            return True
        except Exception as e:
            logger.warning(f"[Ollama] Could not unload {model_id}: {e}")
            return False

    async def get_running_models(self) -> List[dict]:
        """Return models currently loaded in Ollama's memory (/api/ps)."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/ps")
                if r.status_code == 200:
                    data = r.json()
                    models = data.get("models", [])
                    # Update our active-model tracker
                    if models:
                        self._active_model = models[0].get("name")
                        size_vram = models[0].get("size_vram", 0)
                        size = models[0].get("size", size_vram)
                        self._active_model_ram_gb = round(size / 1024**3, 2)
                    return models
        except Exception:
            pass
        return []

    async def list_models(self) -> List[str]:
        """Return list of installed model IDs."""
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                if r.status_code != 200:
                    return []
                data = r.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    async def list_models_detailed(self) -> List[dict]:
        """Return installed models with size and family info."""
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                if r.status_code != 200:
                    return []
                data = r.json()
                result = []
                for m in data.get("models", []):
                    size_gb = round(m.get("size", 0) / 1024**3, 2)
                    result.append({
                        "id": m["name"],
                        "size_gb": size_gb,
                        "modified_at": m.get("modified_at", ""),
                        "fits_budget": size_gb <= _RAM_BUDGET_GB,
                        "family": m.get("details", {}).get("family", "unknown"),
                        "parameters": m.get("details", {}).get("parameter_size", "?"),
                        "quantization": m.get("details", {}).get("quantization_level", "?"),
                    })
                return result
        except Exception:
            return []

    async def get_model_info(self, model_id: str) -> dict:
        """Fetch detailed info about a specific model (/api/show)."""
        if model_id in self._model_info_cache:
            return self._model_info_cache[model_id]
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    f"{self.base_url}/api/show",
                    json={"name": model_id},
                )
                if r.status_code == 200:
                    info = r.json()
                    self._model_info_cache[model_id] = info
                    return info
        except Exception as e:
            logger.debug(f"[Ollama] model info failed for {model_id}: {e}")
        return {}

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _ensure_model_ready(self, model_id: str) -> None:
        """
        Check RAM budget and model availability before running.
        Fires a load event if switching models.
        """
        # RAM guard — look up the model in our registry
        from app.providers.model_registry import get_model as reg_get
        spec = reg_get(model_id)
        if spec and spec.ram_gb > _RAM_BUDGET_GB:
            raise RuntimeError(
                f"Model {model_id} requires {spec.ram_gb} GB RAM "
                f"but budget is {_RAM_BUDGET_GB} GB. Choose a smaller model."
            )

        # If it's a different model from what's running, log the switch
        if self._active_model and self._active_model != model_id:
            logger.info(
                f"[Ollama] Switching model: {self._active_model} → {model_id}"
            )
            await event_bus.publish(Events.NOTIFICATION, {
                "title": "Model switch",
                "message": f"{self._active_model} → {model_id}",
                "level": "info",
            })
            # Ollama handles unloading automatically when a new model is loaded.
            # We only need to explicitly unload if RAM is very tight.
            if spec and self._active_model_ram_gb + spec.ram_gb > _RAM_BUDGET_GB + 1.0:
                await self.unload_model(self._active_model)

    def _build_messages(self, request: CompletionRequest) -> List[dict]:
        messages: List[dict] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        for msg in request.messages:
            messages.append({"role": msg.role.value, "content": msg.content})
        return messages

    def _context_size_for(self, model_id: str) -> int:
        """
        Return a sensible context window size for the model.
        Smaller models get a smaller context to save RAM.
        """
        from app.providers.model_registry import get_model as reg_get
        spec = reg_get(model_id)
        if not spec:
            return 4096
        # Cap at 32K even if model supports more — RAM savings on 12 GB
        return min(spec.context_tokens, 32768)

    @property
    def active_model(self) -> Optional[str]:
        return self._active_model

    @property
    def ram_budget_gb(self) -> float:
        return _RAM_BUDGET_GB
