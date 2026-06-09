"""
J.A.Y. Vision API — Image understanding via multimodal models
─────────────────────────────────────────────────────────────────
Supports:
  • Ollama vision models (llava, llava-llama3, bakllava) — local, free
  • OpenRouter vision models (llama-3.2-11b-vision:free) — cloud, free
  • Direct base64 image upload + URL-based images

On 12 GB RAM: llava:7b uses ~4.5 GB
"""

from __future__ import annotations

import base64
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/vision", tags=["vision"])

# Vision model priority (tried in order)
OLLAMA_VISION_MODELS = [
    "llava:7b",
    "llava-llama3",
    "bakllava",
    "llava:13b",
    "llava",
]

OPENROUTER_VISION_MODELS = [
    "meta-llama/llama-3.2-11b-vision-instruct:free",
    "google/gemma-3-27b-it:free",
    "qwen/qwen2-vl-7b-instruct:free",
]


class VisionRequest(BaseModel):
    image_base64: str
    prompt: str = "Describe this image in detail. What do you see?"
    max_tokens: int = 1024


class VisionResponse(BaseModel):
    description: str
    model_used: str
    provider: str


@router.post("/analyze", response_model=VisionResponse)
async def analyze_image(request: VisionRequest):
    """Analyze an image with a vision model. Tries Ollama then OpenRouter."""
    image_b64 = request.image_base64
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    prompt = request.prompt

    # Try Ollama vision models
    if await _ollama_is_available():
        installed = await _ollama_installed_models()
        for model in OLLAMA_VISION_MODELS:
            if model in installed:
                try:
                    result = await _ollama_vision(model, image_b64, prompt, request.max_tokens)
                    return VisionResponse(description=result, model_used=model, provider="ollama")
                except Exception as e:
                    logger.warning(f"Ollama vision ({model}) failed: {e}")
                    continue

    # Try OpenRouter vision models
    if settings.OPENROUTER_API_KEY:
        for model in OPENROUTER_VISION_MODELS:
            try:
                result = await _openrouter_vision(model, image_b64, prompt, request.max_tokens)
                return VisionResponse(description=result, model_used=model, provider="openrouter")
            except Exception as e:
                logger.warning(f"OpenRouter vision ({model}) failed: {e}")
                continue

    raise HTTPException(
        status_code=503,
        detail="No vision model available. Run: ollama pull llava  OR  set OPENROUTER_API_KEY",
    )


@router.post("/analyze-upload")
async def analyze_uploaded_image(
    file: UploadFile = File(...),
    prompt: str = Form("Describe this image in detail. What do you see?"),
):
    """Analyze an uploaded image file directly."""
    allowed = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp"}
    if file.content_type not in allowed:
        raise HTTPException(400, f"Unsupported type: {file.content_type}")
    if file.size and file.size > 20 * 1024 * 1024:
        raise HTTPException(400, "Image too large (max 20 MB)")

    data = await file.read()
    image_b64 = base64.b64encode(data).decode("utf-8")
    request = VisionRequest(image_base64=image_b64, prompt=prompt)
    return await analyze_image(request)


@router.get("/models")
async def list_vision_models():
    """List available vision models."""
    result = {"ollama": [], "openrouter": []}
    if await _ollama_is_available():
        installed = await _ollama_installed_models()
        for model in OLLAMA_VISION_MODELS:
            result["ollama"].append({"id": model, "installed": model in installed, "local": True})
    if settings.OPENROUTER_API_KEY:
        for model in OPENROUTER_VISION_MODELS:
            result["openrouter"].append({"id": model, "installed": True, "local": False})
    return result


@router.post("/pull-vision-model")
async def pull_vision_model(model_id: str = "llava"):
    """Pull a vision model via Ollama."""
    if not await _ollama_is_available():
        raise HTTPException(503, "Ollama not running")
    import asyncio
    from app.core.events import event_bus, Events

    async def _pull():
        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                async with client.stream("POST", f"{settings.OLLAMA_BASE_URL}/api/pull",
                    json={"name": model_id, "stream": True}) as resp:
                    async for _ in resp.aiter_lines():
                        pass
            await event_bus.publish(Events.NOTIFICATION, {
                "title": "Vision model ready", "message": f"{model_id} installed", "level": "success"})
        except Exception as e:
            await event_bus.publish(Events.NOTIFICATION, {
                "title": "Pull failed", "message": str(e), "level": "error"})

    asyncio.create_task(_pull())
    return {"success": True, "message": f"Pulling {model_id}…"}


# ── Ollama vision call ─────────────────────────────────────────────────────────

async def _ollama_vision(model: str, image_b64: str, prompt: str, max_tokens: int) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt, "images": [image_b64]}],
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.3},
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{settings.OLLAMA_BASE_URL}/api/chat", json=payload)
        resp.raise_for_status()
    return resp.json().get("message", {}).get("content", "")


# ── OpenRouter vision call ─────────────────────────────────────────────────────

async def _openrouter_vision(model: str, image_b64: str, prompt: str, max_tokens: int) -> str:
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "J.A.Y. Personal AI OS",
        "HTTP-Referer": "https://github.com/jay-ai-os",
    }
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
            ],
        }],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
    choices = resp.json().get("choices", [])
    return choices[0].get("message", {}).get("content", "") if choices else ""


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _ollama_is_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def _ollama_installed_models() -> list:
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []
