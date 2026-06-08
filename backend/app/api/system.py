"""
J.A.Y. System API — Status, settings, providers, model routing, agents
"""
from __future__ import annotations

import logging
import platform
from typing import Any, Dict, List, Optional

import psutil
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/system", tags=["system"])


# ── Basic status ───────────────────────────────────────────────────────────────

@router.get("/status")
async def get_status():
    """High-level J.A.Y. system status — used by the dashboard."""
    from app.core.config import settings
    from app.providers.manager import provider_manager
    from app.agents.registry import agent_registry

    providers = await provider_manager.list_available()
    mem = psutil.virtual_memory()

    return {
        "name":             settings.APP_NAME,
        "version":          settings.APP_VERSION,
        "status":           "online",
        "os":               f"{platform.system()} {platform.release()}",
        "cpu_percent":      psutil.cpu_percent(interval=0.3),
        "ram_used_gb":      round(mem.used  / 1024**3, 2),
        "ram_total_gb":     round(mem.total / 1024**3, 2),
        "ram_percent":      mem.percent,
        "providers":        providers,
        "agents":           agent_registry.list_agents() if agent_registry else [],
        "routing_mode":     settings.ROUTING_MODE,
        "last_decision":    provider_manager.get_last_decision(),
    }


# ── Settings ───────────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings():
    """Return all user-visible settings."""
    from app.core.config import settings
    return {
        "app_name":                      settings.APP_NAME,
        # Routing
        "routing_mode":                  settings.ROUTING_MODE,
        "routing_fallback_order":        settings.ROUTING_FALLBACK_ORDER,
        "ollama_ram_budget_gb":          settings.OLLAMA_RAM_BUDGET_GB,
        "ollama_auto_pull":              settings.OLLAMA_AUTO_PULL,
        # Per-task overrides (non-empty only)
        "task_model_overrides":          settings.task_model_overrides(),
        # Voice
        "tts_voice":                     settings.TTS_VOICE,
        "stt_model":                     settings.STT_MODEL,
        "wake_words":                    settings.WAKE_WORDS,
        # Memory
        "memory_similarity_threshold":   settings.MEMORY_SIMILARITY_THRESHOLD,
        # Trading
        "paper_trading_capital":         settings.PAPER_TRADING_CAPITAL,
        # Security
        "require_approval_for_dangerous": settings.REQUIRE_APPROVAL_FOR_DANGEROUS,
        # OpenRouter quota limits
        "or_free_daily_limit":           settings.OR_FREE_DAILY_LIMIT,
        "or_free_rpm_limit":             settings.OR_FREE_RPM_LIMIT,
        "or_free_tokens_per_day":        settings.OR_FREE_TOKENS_PER_DAY,
    }


class SettingsUpdateRequest(BaseModel):
    key:   str
    value: Any


_ALLOWED_SETTING_KEYS = {
    "routing_mode", "routing_fallback_order",
    "ollama_ram_budget_gb", "ollama_auto_pull",
    "tts_voice", "stt_model",
    "require_approval_for_dangerous", "memory_similarity_threshold",
    "or_free_daily_limit", "or_free_rpm_limit", "or_free_tokens_per_day",
}


@router.post("/settings")
async def update_settings(request: SettingsUpdateRequest):
    """Update a runtime setting."""
    from app.core.config import settings
    from app.providers.manager import provider_manager

    if request.key not in _ALLOWED_SETTING_KEYS:
        raise HTTPException(
            status_code=400,
            detail=f"'{request.key}' cannot be updated via API. "
                   f"Allowed: {sorted(_ALLOWED_SETTING_KEYS)}",
        )
    setattr(settings, request.key.upper(), request.value)

    # If routing mode changed, flush availability cache so next request re-probes
    if request.key in ("routing_mode", "routing_fallback_order", "ollama_ram_budget_gb"):
        provider_manager.invalidate_availability_cache()

    return {"success": True, "key": request.key, "value": request.value}


# ── Model status — the new core endpoint ──────────────────────────────────────

@router.get("/model-status")
async def get_model_status():
    """
    Full picture of the AI model routing state:
      • Which model is currently active in Ollama
      • All installed Ollama models with size / RAM info
      • Per-task routing decisions (what would be picked right now)
      • OpenRouter quota status for every free model
      • Usage stats per model
      • Last routing decision
    """
    from app.core.config import settings
    from app.providers.manager import provider_manager
    from app.providers.quota_tracker import quota_tracker
    from app.providers.model_registry import (
        OLLAMA_MODELS, OPENROUTER_MODELS,
        best_ollama_for_task, best_openrouter_for_task,
    )
    from app.providers.task_classifier import TaskType, task_label

    ollama_provider = provider_manager.get_provider("ollama")
    ollama_available = await provider_manager._is_available("ollama")

    # ── Ollama section ────────────────────────────────────────────────
    installed_detailed: List[dict] = []
    running_models:     List[dict] = []
    active_model:       Optional[str] = None

    if ollama_available and ollama_provider:
        installed_detailed = await ollama_provider.list_models_detailed()
        running_models     = await ollama_provider.get_running_models()
        active_model       = ollama_provider.active_model
        if not active_model and running_models:
            active_model = running_models[0].get("name")

    # Annotate installed models with registry info
    installed_ids = {m["id"] for m in installed_detailed}
    for m in installed_detailed:
        reg = next((r for r in OLLAMA_MODELS if r.id == m["id"]), None)
        m["display_name"]   = reg.display_name   if reg else m["id"]
        m["description"]    = reg.description    if reg else ""
        m["fits_budget"]    = m["size_gb"] <= settings.OLLAMA_RAM_BUDGET_GB
        m["is_active"]      = (m["id"] == active_model)
        m["recommended"]    = (reg is not None and reg.fits_12gb) if reg else False

    # Models in the registry but not yet installed
    not_installed = [
        {
            "id":           m.id,
            "display_name": m.display_name,
            "ram_gb":       m.ram_gb,
            "description":  m.description,
            "speed":        m.speed,
            "fits_budget":  m.ram_gb <= settings.OLLAMA_RAM_BUDGET_GB,
            "tags":         m.tags,
        }
        for m in OLLAMA_MODELS
        if m.fits_12gb and m.id not in installed_ids
    ]

    # ── Per-task routing preview ──────────────────────────────────────
    # Show what model WOULD be picked right now for each task type
    task_routing: List[dict] = []
    for task in TaskType:
        ollama_pick = best_ollama_for_task(task, max_ram_gb=settings.OLLAMA_RAM_BUDGET_GB)
        or_pick     = best_openrouter_for_task(task, free_only=True)

        # Check if ollama pick is installed
        ollama_ready = (
            ollama_pick is not None
            and ollama_available
            and ollama_pick.id in installed_ids
        )

        # Check if OR pick is quota-available
        or_quota_ok = False
        or_reason   = ""
        if or_pick:
            or_quota_ok, or_reason = await quota_tracker.is_available(or_pick.id)

        # Determine what would actually be used
        override = settings.task_model_overrides().get(task.value, "")
        if override:
            effective = override
            effective_provider = _infer_provider(override)
            effective_reason = "Manual override in .env"
        elif ollama_ready:
            effective = ollama_pick.id
            effective_provider = "ollama"
            effective_reason = f"Best local model (score {ollama_pick.scores.get(task,0)}/10)"
        elif or_quota_ok and or_pick:
            effective = or_pick.id
            effective_provider = "openrouter"
            effective_reason = f"Best free cloud model (score {or_pick.scores.get(task,0)}/10)"
        else:
            effective = None
            effective_provider = None
            effective_reason = "No model available — install Ollama model or set OpenRouter key"

        task_routing.append({
            "task":               task.value,
            "task_label":         task_label(task),
            "override":           override or None,
            "effective_model":    effective,
            "effective_provider": effective_provider,
            "effective_reason":   effective_reason,
            "ollama_candidate":   ollama_pick.id if ollama_pick else None,
            "ollama_installed":   ollama_ready,
            "or_candidate":       or_pick.id if or_pick else None,
            "or_available":       or_quota_ok,
            "or_reason":          or_reason if not or_quota_ok else "",
        })

    # ── OpenRouter quota status ───────────────────────────────────────
    or_available = await provider_manager._is_available("openrouter")
    quota_status = quota_tracker.get_status() if or_available else []

    # Merge registry display names into quota status
    or_model_map = {m.id: m for m in OPENROUTER_MODELS}
    for entry in quota_status:
        reg = or_model_map.get(entry["model_id"])
        entry["display_name"] = reg.display_name if reg else entry["model_id"]
        entry["is_free"]      = reg.is_free      if reg else True
        entry["speed"]        = reg.speed        if reg else "unknown"

    # ── Usage stats ───────────────────────────────────────────────────
    usage_stats = provider_manager.get_usage_stats()

    return {
        # Ollama
        "ollama_available":    ollama_available,
        "active_model":        active_model,
        "ram_budget_gb":       settings.OLLAMA_RAM_BUDGET_GB,
        "installed_models":    installed_detailed,
        "not_installed":       not_installed,
        "running_models":      running_models,

        # Routing
        "routing_mode":        settings.ROUTING_MODE,
        "fallback_order":      settings.fallback_order(),
        "task_routing":        task_routing,
        "last_decision":       provider_manager.get_last_decision(),

        # OpenRouter
        "openrouter_available": or_available,
        "openrouter_key_set":   bool(settings.OPENROUTER_API_KEY),
        "quota_status":         quota_status,

        # Usage
        "usage_stats":         usage_stats,
    }


# ── Ollama model actions ───────────────────────────────────────────────────────

@router.post("/ollama/pull/{model_id:path}")
async def pull_ollama_model(model_id: str, background_tasks: BackgroundTasks):
    """
    Trigger an Ollama model pull.
    Runs in the background — progress is broadcast via WebSocket notifications.
    """
    from app.providers.manager import provider_manager
    ollama = provider_manager.get_provider("ollama")
    if not ollama:
        raise HTTPException(status_code=503, detail="Ollama provider not available")

    # Check RAM budget first
    from app.providers.model_registry import get_model
    from app.core.config import settings
    spec = get_model(model_id)
    if spec and spec.ram_gb > settings.OLLAMA_RAM_BUDGET_GB:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Model {model_id} requires {spec.ram_gb} GB RAM "
                f"but your budget is {settings.OLLAMA_RAM_BUDGET_GB} GB. "
                f"Choose a smaller model."
            ),
        )

    background_tasks.add_task(ollama.ensure_model_pulled, model_id)
    return {
        "success": True,
        "message": f"Pulling {model_id} in background — watch notifications for progress",
        "model_id": model_id,
    }


@router.post("/ollama/unload/{model_id:path}")
async def unload_ollama_model(model_id: str):
    """Unload a model from Ollama's memory to free RAM."""
    from app.providers.manager import provider_manager
    ollama = provider_manager.get_provider("ollama")
    if not ollama:
        raise HTTPException(status_code=503, detail="Ollama provider not available")
    ok = await ollama.unload_model(model_id)
    return {"success": ok, "model_id": model_id}


@router.get("/ollama/running")
async def get_running_models():
    """List models currently loaded in Ollama's memory."""
    from app.providers.manager import provider_manager
    ollama = provider_manager.get_provider("ollama")
    if not ollama:
        return {"models": []}
    models = await ollama.get_running_models()
    return {"models": models}


# ── OpenRouter quota actions ───────────────────────────────────────────────────

@router.get("/openrouter/quota")
async def get_openrouter_quota():
    """Full OpenRouter quota status for all tracked models."""
    from app.providers.quota_tracker import quota_tracker
    return {"quota": quota_tracker.get_status()}


@router.post("/openrouter/quota/unblock/{model_id:path}")
async def unblock_openrouter_model(model_id: str):
    """Manually unblock a quota-exhausted OpenRouter model."""
    from app.providers.quota_tracker import quota_tracker
    await quota_tracker.unblock(model_id)
    return {"success": True, "model_id": model_id}


@router.post("/openrouter/quota/reset")
async def reset_openrouter_quota():
    """Reset ALL OpenRouter quota counters (use at start of day)."""
    from app.providers.quota_tracker import quota_tracker
    await quota_tracker.reset_all()
    return {"success": True, "message": "All OpenRouter quotas reset"}


# ── Provider management ────────────────────────────────────────────────────────

@router.get("/providers")
async def get_providers():
    """Detailed provider availability including installed Ollama models."""
    from app.providers.manager import provider_manager
    providers = await provider_manager.list_available()
    return {"providers": providers}


@router.post("/providers/refresh")
async def refresh_providers():
    """Force re-check of all provider availability (clears cache)."""
    from app.providers.manager import provider_manager
    provider_manager.invalidate_availability_cache()
    providers = await provider_manager.list_available()
    return {"success": True, "providers": providers}


# ── Agents ─────────────────────────────────────────────────────────────────────

@router.get("/agents")
async def get_agents():
    from app.agents.registry import agent_registry
    if not agent_registry:
        return {"agents": []}
    return {"agents": agent_registry.list_agents()}


# ── Classify endpoint (debug / UI preview) ────────────────────────────────────

@router.post("/classify")
async def classify_message(body: Dict[str, str]):
    """
    Debug endpoint: classify a message and show the full routing chain.
    Useful for the Settings panel routing preview.
    """
    from app.providers.task_classifier import classify, task_label
    message = body.get("message", "")
    if not message:
        raise HTTPException(status_code=400, detail="message required")
    task = classify(message)
    return {
        "message":    message,
        "task_type":  task.value,
        "task_label": task_label(task),
    }


# ── Quick tool execution ───────────────────────────────────────────────────────

@router.post("/tool/{tool_name}/execute")
async def execute_tool_quick(tool_name: str, params: Dict[str, Any] = {}):
    from app.api.tools import execute_tool, ToolExecuteRequest
    return await execute_tool(ToolExecuteRequest(tool=tool_name, params=params))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _infer_provider(model_id: str) -> str:
    """Guess provider from model ID format."""
    if "/" in model_id:
        return "openrouter"
    if "gemini" in model_id.lower():
        return "gemini"
    return "ollama"
