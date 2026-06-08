"""
J.A.Y. Core Configuration
─────────────────────────────────────────────────────────────────
All settings are read from environment variables or backend/.env.
Pydantic-settings handles validation and type coercion automatically.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME:    str  = "J.A.Y."
    APP_VERSION: str  = "0.1.0"
    DEBUG:       bool = False
    SECRET_KEY:  str  = "jay-secret-key-change-in-production"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL:      str = "sqlite+aiosqlite:///./jay.db"
    DATABASE_SYNC_URL: str = "sqlite:///./jay.db"

    # ── AI Provider keys ──────────────────────────────────────────────────────
    OPENAI_API_KEY:      Optional[str] = None
    ANTHROPIC_API_KEY:   Optional[str] = None
    GOOGLE_API_KEY:      Optional[str] = None
    OPENROUTER_API_KEY:  Optional[str] = None   # ← primary cloud key

    # ── Ollama ────────────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # RAM budget for Ollama on this machine (GB).
    # On 12 GB RAM: OS ~3 GB + backend ~0.8 GB → safe ceiling ≈ 7 GB
    OLLAMA_RAM_BUDGET_GB: float = 7.0

    # ── Smart routing ─────────────────────────────────────────────────────────
    # Master switch: "auto" = smart routing, "ollama" / "openrouter" = force
    ROUTING_MODE: str = "auto"   # auto | ollama | openrouter | gemini

    # Fallback order when routing_mode == "auto"
    # Comma-separated provider names, highest priority first
    ROUTING_FALLBACK_ORDER: str = "ollama,openrouter,gemini"

    # Whether to auto-pull an Ollama model if it's not installed yet
    OLLAMA_AUTO_PULL: bool = True

    # ── Per-task model overrides ──────────────────────────────────────────────
    # Leave empty ("") to let the router pick automatically.
    # Set to an exact model ID to force that model for the task type.
    MODEL_QUICK:      str = ""   # e.g. "llama3.2:3b"
    MODEL_CHAT:       str = ""   # e.g. "llama3.1:8b-instruct-q4_K_M"
    MODEL_CODE:       str = ""   # e.g. "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
    MODEL_CODE_HEAVY: str = ""   # e.g. "deepseek/deepseek-r1:free"  (OpenRouter)
    MODEL_TRADING:    str = ""   # e.g. "mistral:7b-instruct-q4_K_M"
    MODEL_RESEARCH:   str = ""   # e.g. "meta-llama/llama-3.3-70b-instruct:free"
    MODEL_CREATIVE:   str = ""   # e.g. "google/gemma-3-27b-it:free"
    MODEL_PLAN:       str = ""
    MODEL_ANALYSIS:   str = ""
    MODEL_VOICE:      str = ""   # small model for quick spoken replies
    MODEL_MEMORY:     str = ""
    MODEL_TOOL:       str = ""

    # ── OpenRouter quota / rate-limit settings ────────────────────────────────
    # Free-tier daily request limit per model (conservative estimate).
    # Set to 0 to disable the guard for a specific model.
    OR_FREE_DAILY_LIMIT:     int   = 200    # requests per model per day
    OR_FREE_RPM_LIMIT:       int   = 20     # requests per minute (free tier)
    OR_FREE_TOKENS_PER_DAY:  int   = 50_000 # token budget per model per day

    # After this many consecutive errors from a free model, mark it exhausted
    OR_EXHAUST_ERROR_THRESHOLD: int = 5

    # ── Gemini ────────────────────────────────────────────────────────────────
    GEMINI_DEFAULT_MODEL: str = "gemini-1.5-flash"  # cheapest / fastest

    # ── Voice ─────────────────────────────────────────────────────────────────
    WAKE_WORDS: List[str] = ["hey jay", "wake up jay", "j.a.y."]
    PVPORCUPINE_ACCESS_KEY: Optional[str] = None
    TTS_VOICE:    str = "en-US-AriaNeural"
    TTS_RATE:     str = "+0%"
    TTS_PITCH:    str = "+0Hz"
    STT_MODEL:    str = "base"    # tiny | base | small | medium | large
    STT_LANGUAGE: str = "en"

    # ── Memory / vector store ─────────────────────────────────────────────────
    CHROMA_PERSIST_DIR:         str   = "./data/chroma"
    EMBEDDING_MODEL:            str   = "all-MiniLM-L6-v2"
    MAX_MEMORY_RESULTS:         int   = 10
    MEMORY_SIMILARITY_THRESHOLD: float = 0.7

    # ── Trading ───────────────────────────────────────────────────────────────
    DEFAULT_EXCHANGE:        str   = "NSE"
    PAPER_TRADING_CAPITAL:   float = 100_000.0
    ALPHA_VANTAGE_KEY:       Optional[str] = None
    FINNHUB_KEY:             Optional[str] = None

    # ── Security ──────────────────────────────────────────────────────────────
    REQUIRE_APPROVAL_FOR_DANGEROUS: bool = True
    AUDIT_LOG_PATH: str = "./data/audit.log"

    # ── Paths ─────────────────────────────────────────────────────────────────
    PROJECTS_DIR: str = os.path.expanduser("~/jay-projects")
    DATA_DIR:     str = "./data"
    LOGS_DIR:     str = "./logs"

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("ROUTING_MODE")
    @classmethod
    def _valid_routing_mode(cls, v: str) -> str:
        allowed = {"auto", "ollama", "openrouter", "gemini", "openai"}
        if v not in allowed:
            raise ValueError(f"ROUTING_MODE must be one of {allowed}, got '{v}'")
        return v

    @field_validator("OLLAMA_RAM_BUDGET_GB")
    @classmethod
    def _valid_ram(cls, v: float) -> float:
        if v < 1.0 or v > 128.0:
            raise ValueError("OLLAMA_RAM_BUDGET_GB must be between 1 and 128")
        return v

    # ── Convenience helpers ───────────────────────────────────────────────────

    def fallback_order(self) -> List[str]:
        """Return the routing fallback order as a list."""
        return [p.strip() for p in self.ROUTING_FALLBACK_ORDER.split(",") if p.strip()]

    def task_model_overrides(self) -> Dict[str, str]:
        """
        Return a dict of task_type → model_id for any overrides that are set.
        Only includes entries where the override is non-empty.
        """
        from app.providers.task_classifier import TaskType
        raw = {
            TaskType.QUICK:      self.MODEL_QUICK,
            TaskType.CHAT:       self.MODEL_CHAT,
            TaskType.CODE:       self.MODEL_CODE,
            TaskType.CODE_HEAVY: self.MODEL_CODE_HEAVY,
            TaskType.TRADING:    self.MODEL_TRADING,
            TaskType.RESEARCH:   self.MODEL_RESEARCH,
            TaskType.CREATIVE:   self.MODEL_CREATIVE,
            TaskType.PLAN:       self.MODEL_PLAN,
            TaskType.ANALYSIS:   self.MODEL_ANALYSIS,
            TaskType.VOICE:      self.MODEL_VOICE,
            TaskType.MEMORY:     self.MODEL_MEMORY,
            TaskType.TOOL:       self.MODEL_TOOL,
        }
        return {k.value: v for k, v in raw.items() if v}

    def has_cloud_provider(self) -> bool:
        return bool(
            self.OPENROUTER_API_KEY
            or self.OPENAI_API_KEY
            or self.GOOGLE_API_KEY
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


settings = Settings()
