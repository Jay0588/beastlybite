"""
J.A.Y. Model Registry
─────────────────────────────────────────────────────────────────
All known models with:
  • RAM requirements (at q4 quantization where applicable)
  • Task suitability scores (0–10)
  • Which provider serves them
  • Whether they're safe to run on 12 GB RAM

12 GB RAM budget breakdown:
  OS + browser + frontend   ~3.0 GB
  J.A.Y. backend / Python   ~0.5 GB
  ChromaDB / embeddings     ~0.3 GB
  ─────────────────────────────────
  Available for models       ~8.2 GB
  Comfortable ceiling        ~7.0 GB  (leave headroom)

So: only load models ≤ 7 GB at a time.
Ollama unloads the previous model before loading the next one.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from app.providers.task_classifier import TaskType


@dataclass
class ModelSpec:
    id: str                        # ollama pull name  OR  openrouter model id
    provider: str                  # "ollama" | "openrouter" | "gemini" | "openai"
    display_name: str
    ram_gb: float                  # peak RAM when loaded (0 = cloud, no local RAM)
    context_tokens: int            # max context window
    fits_12gb: bool                # True if safe on 12 GB RAM machine

    # Per-task suitability 0–10
    scores: Dict[str, int] = field(default_factory=dict)

    # Metadata
    description: str = ""
    is_free: bool = False          # free tier or fully free
    speed: str = "medium"         # "fast" | "medium" | "slow"
    tags: List[str] = field(default_factory=list)


# ── OLLAMA MODELS (local, free, private) ──────────────────────────────────────
#
# Naming convention: use the exact `ollama pull` tag
# RAM figures are for q4_K_M quantisation which Ollama uses by default
# ─────────────────────────────────────────────────────────────────────────────

OLLAMA_MODELS: List[ModelSpec] = [

    # ── Tiny / ultra-fast (≤ 2 GB) ──────────────────────────────────────────
    ModelSpec(
        id="llama3.2:3b",
        provider="ollama",
        display_name="Llama 3.2 3B",
        ram_gb=2.0,
        context_tokens=8192,
        fits_12gb=True,
        speed="fast",
        description="Tiny but surprisingly capable. Best for quick answers and voice.",
        is_free=True,
        tags=["tiny", "fast", "voice"],
        scores={
            TaskType.QUICK:    9,
            TaskType.CHAT:     8,
            TaskType.VOICE:    10,   # short snappy replies
            TaskType.MEMORY:   7,
            TaskType.TOOL:     6,
            TaskType.CODE:     4,
            TaskType.RESEARCH: 4,
            TaskType.TRADING:  3,
            TaskType.PLAN:     4,
            TaskType.ANALYSIS: 3,
            TaskType.CREATIVE: 5,
            TaskType.CODE_HEAVY: 2,
        },
    ),

    ModelSpec(
        id="phi3:3.8b",
        provider="ollama",
        display_name="Phi-3 Mini 3.8B",
        ram_gb=2.3,
        context_tokens=128000,   # huge context for its size
        fits_12gb=True,
        speed="fast",
        description="Microsoft's small model. Punches above weight on reasoning. 128K context.",
        is_free=True,
        tags=["tiny", "fast", "long-context"],
        scores={
            TaskType.QUICK:    9,
            TaskType.CHAT:     8,
            TaskType.VOICE:    9,
            TaskType.MEMORY:   7,
            TaskType.TOOL:     6,
            TaskType.CODE:     6,
            TaskType.RESEARCH: 5,
            TaskType.TRADING:  4,
            TaskType.PLAN:     5,
            TaskType.ANALYSIS: 5,
            TaskType.CREATIVE: 5,
            TaskType.CODE_HEAVY: 3,
        },
    ),

    # ── Mid-range (3–5 GB) ───────────────────────────────────────────────────
    ModelSpec(
        id="mistral:7b-instruct-q4_K_M",
        provider="ollama",
        display_name="Mistral 7B Instruct (q4)",
        ram_gb=4.1,
        context_tokens=32768,
        fits_12gb=True,
        speed="medium",
        description="Excellent all-rounder. Great at instructions, analysis, trading logic.",
        is_free=True,
        tags=["balanced", "instruct", "recommended"],
        scores={
            TaskType.QUICK:    8,
            TaskType.CHAT:     9,
            TaskType.VOICE:    7,
            TaskType.MEMORY:   8,
            TaskType.TOOL:     8,
            TaskType.CODE:     7,
            TaskType.RESEARCH: 8,
            TaskType.TRADING:  8,
            TaskType.PLAN:     8,
            TaskType.ANALYSIS: 8,
            TaskType.CREATIVE: 7,
            TaskType.CODE_HEAVY: 6,
        },
    ),

    ModelSpec(
        id="llama3.1:8b-instruct-q4_K_M",
        provider="ollama",
        display_name="Llama 3.1 8B Instruct (q4)",
        ram_gb=4.7,
        context_tokens=128000,
        fits_12gb=True,
        speed="medium",
        description="Meta's Llama 3.1 with 128K context. Strong general intelligence.",
        is_free=True,
        tags=["balanced", "long-context", "recommended"],
        scores={
            TaskType.QUICK:    8,
            TaskType.CHAT:     9,
            TaskType.VOICE:    7,
            TaskType.MEMORY:   9,
            TaskType.TOOL:     8,
            TaskType.CODE:     8,
            TaskType.RESEARCH: 8,
            TaskType.TRADING:  7,
            TaskType.PLAN:     9,
            TaskType.ANALYSIS: 8,
            TaskType.CREATIVE: 7,
            TaskType.CODE_HEAVY: 7,
        },
    ),

    ModelSpec(
        id="deepseek-coder-v2:16b-lite-instruct-q4_K_M",
        provider="ollama",
        display_name="DeepSeek Coder V2 16B Lite (q4)",
        ram_gb=4.9,
        context_tokens=16384,
        fits_12gb=True,
        speed="medium",
        description="Purpose-built code model. Best local option for coding tasks.",
        is_free=True,
        tags=["code", "specialist"],
        scores={
            TaskType.QUICK:    4,
            TaskType.CHAT:     5,
            TaskType.VOICE:    3,
            TaskType.MEMORY:   5,
            TaskType.TOOL:     7,
            TaskType.CODE:     10,
            TaskType.RESEARCH: 4,
            TaskType.TRADING:  5,
            TaskType.PLAN:     6,
            TaskType.ANALYSIS: 6,
            TaskType.CREATIVE: 4,
            TaskType.CODE_HEAVY: 10,
        },
    ),

    ModelSpec(
        id="codellama:7b-instruct-q4_K_M",
        provider="ollama",
        display_name="Code Llama 7B Instruct (q4)",
        ram_gb=3.8,
        context_tokens=16384,
        fits_12gb=True,
        speed="medium",
        description="Meta's code specialist. Fallback when DeepSeek isn't available.",
        is_free=True,
        tags=["code", "fallback"],
        scores={
            TaskType.QUICK:    3,
            TaskType.CHAT:     4,
            TaskType.VOICE:    2,
            TaskType.MEMORY:   4,
            TaskType.TOOL:     7,
            TaskType.CODE:     9,
            TaskType.RESEARCH: 3,
            TaskType.TRADING:  4,
            TaskType.PLAN:     5,
            TaskType.ANALYSIS: 5,
            TaskType.CREATIVE: 3,
            TaskType.CODE_HEAVY: 8,
        },
    ),

    # ── Upper range (5–7 GB — fits but tight) ───────────────────────────────
    ModelSpec(
        id="mixtral:8x7b-instruct-v0.1-q2_K",
        provider="ollama",
        display_name="Mixtral 8x7B (q2 — tight fit)",
        ram_gb=6.5,
        context_tokens=32768,
        fits_12gb=True,   # q2 keeps it just under budget
        speed="slow",
        description="Mixture-of-experts powerhouse at q2. Best local intelligence. Use only when really needed.",
        is_free=True,
        tags=["powerful", "slow", "moe"],
        scores={
            TaskType.QUICK:    7,
            TaskType.CHAT:     10,
            TaskType.VOICE:    5,
            TaskType.MEMORY:   9,
            TaskType.TOOL:     8,
            TaskType.CODE:     9,
            TaskType.RESEARCH: 9,
            TaskType.TRADING:  9,
            TaskType.PLAN:     10,
            TaskType.ANALYSIS: 10,
            TaskType.CREATIVE: 9,
            TaskType.CODE_HEAVY: 9,
        },
    ),

    # ── Too large for 12 GB (listed for completeness / future upgrade) ───────
    ModelSpec(
        id="llama3:70b-instruct-q4_K_M",
        provider="ollama",
        display_name="Llama 3 70B (q4) — needs 40 GB+",
        ram_gb=40.0,
        context_tokens=8192,
        fits_12gb=False,
        speed="slow",
        description="Not usable on 12 GB RAM.",
        is_free=True,
        tags=["too-large"],
        scores={t: 10 for t in TaskType},
    ),
]

# ── OPENROUTER MODELS (cloud, free tier) ──────────────────────────────────────
#   Free tier limits vary; we track usage to avoid exhaustion.
#   Free models as of 2025: marked is_free=True
# ─────────────────────────────────────────────────────────────────────────────

OPENROUTER_MODELS: List[ModelSpec] = [

    # ── NVIDIA Nemotron Ultra 550B — Jay's primary cloud model ────────────
    ModelSpec(
        id="nvidia/nemotron-3-ultra-550b-a55b:free",
        provider="openrouter",
        display_name="NVIDIA Nemotron Ultra 550B (FREE)",
        ram_gb=0,
        context_tokens=32768,
        fits_12gb=True,
        speed="medium",
        description="NVIDIA's 550B parameter beast. Free tier. Exceptional at everything — code, analysis, reasoning, creative.",
        is_free=True,
        tags=["free", "cloud", "powerful", "primary", "recommended"],
        scores={
            TaskType.QUICK:    9,  TaskType.CHAT:      10, TaskType.VOICE:    7,
            TaskType.MEMORY:   9,  TaskType.TOOL:      9,  TaskType.CODE:     10,
            TaskType.RESEARCH: 10, TaskType.TRADING:   10, TaskType.PLAN:     10,
            TaskType.ANALYSIS: 10, TaskType.CREATIVE:  10, TaskType.CODE_HEAVY: 10,
        },
    ),

    ModelSpec(
        id="meta-llama/llama-3.1-8b-instruct:free",
        provider="openrouter",
        display_name="Llama 3.1 8B (OpenRouter Free)",
        ram_gb=0,
        context_tokens=131072,
        fits_12gb=True,
        speed="fast",
        description="Free tier Llama 3.1 8B via OpenRouter. Great fallback.",
        is_free=True,
        tags=["free", "cloud", "fallback"],
        scores={
            TaskType.QUICK:    8, TaskType.CHAT:     9, TaskType.VOICE:    7,
            TaskType.MEMORY:   8, TaskType.TOOL:     7, TaskType.CODE:     7,
            TaskType.RESEARCH: 8, TaskType.TRADING:  7, TaskType.PLAN:     8,
            TaskType.ANALYSIS: 8, TaskType.CREATIVE: 7, TaskType.CODE_HEAVY: 6,
        },
    ),

    ModelSpec(
        id="meta-llama/llama-3.3-70b-instruct:free",
        provider="openrouter",
        display_name="Llama 3.3 70B (OpenRouter Free)",
        ram_gb=0,
        context_tokens=131072,
        fits_12gb=True,
        speed="medium",
        description="Massive 70B model FREE via OpenRouter. Best quality for heavy tasks.",
        is_free=True,
        tags=["free", "cloud", "powerful", "recommended"],
        scores={
            TaskType.QUICK:    8, TaskType.CHAT:     10, TaskType.VOICE:    6,
            TaskType.MEMORY:   9, TaskType.TOOL:     8,  TaskType.CODE:     9,
            TaskType.RESEARCH: 10, TaskType.TRADING: 9,  TaskType.PLAN:     10,
            TaskType.ANALYSIS: 10, TaskType.CREATIVE: 9, TaskType.CODE_HEAVY: 9,
        },
    ),

    ModelSpec(
        id="google/gemma-3-27b-it:free",
        provider="openrouter",
        display_name="Gemma 3 27B (OpenRouter Free)",
        ram_gb=0,
        context_tokens=131072,
        fits_12gb=True,
        speed="medium",
        description="Google's Gemma 3 27B free on OpenRouter. Strong at analysis.",
        is_free=True,
        tags=["free", "cloud", "google"],
        scores={
            TaskType.QUICK:    7, TaskType.CHAT:     9,  TaskType.VOICE:    7,
            TaskType.MEMORY:   8, TaskType.TOOL:     7,  TaskType.CODE:     8,
            TaskType.RESEARCH: 9, TaskType.TRADING:  8,  TaskType.PLAN:     9,
            TaskType.ANALYSIS: 9, TaskType.CREATIVE: 8,  TaskType.CODE_HEAVY: 7,
        },
    ),

    ModelSpec(
        id="deepseek/deepseek-r1:free",
        provider="openrouter",
        display_name="DeepSeek R1 (OpenRouter Free)",
        ram_gb=0,
        context_tokens=164000,
        fits_12gb=True,
        speed="slow",
        description="DeepSeek's reasoning model, FREE. Best for hard math, analysis, deep code.",
        is_free=True,
        tags=["free", "cloud", "reasoning", "powerful"],
        scores={
            TaskType.QUICK:    5, TaskType.CHAT:     8,  TaskType.VOICE:    4,
            TaskType.MEMORY:   7, TaskType.TOOL:     8,  TaskType.CODE:     10,
            TaskType.RESEARCH: 9, TaskType.TRADING:  10, TaskType.PLAN:     10,
            TaskType.ANALYSIS: 10, TaskType.CREATIVE: 7, TaskType.CODE_HEAVY: 10,
        },
    ),

    ModelSpec(
        id="mistralai/mistral-7b-instruct:free",
        provider="openrouter",
        display_name="Mistral 7B Instruct (OpenRouter Free)",
        ram_gb=0,
        context_tokens=32768,
        fits_12gb=True,
        speed="fast",
        description="Fast free Mistral on OpenRouter. Emergency fallback.",
        is_free=True,
        tags=["free", "cloud", "fast", "fallback"],
        scores={
            TaskType.QUICK:    8, TaskType.CHAT:     8,  TaskType.VOICE:    7,
            TaskType.MEMORY:   7, TaskType.TOOL:     7,  TaskType.CODE:     7,
            TaskType.RESEARCH: 7, TaskType.TRADING:  7,  TaskType.PLAN:     7,
            TaskType.ANALYSIS: 7, TaskType.CREATIVE: 6,  TaskType.CODE_HEAVY: 5,
        },
    ),

    # Paid OpenRouter models (used only when free quota exhausted AND paid key set)
    ModelSpec(
        id="anthropic/claude-3.5-sonnet",
        provider="openrouter",
        display_name="Claude 3.5 Sonnet (paid)",
        ram_gb=0,
        context_tokens=200000,
        fits_12gb=True,
        speed="medium",
        description="Anthropic's best. Paid only. Reserved for critical tasks.",
        is_free=False,
        tags=["paid", "powerful", "cloud"],
        scores={t: 10 for t in TaskType},
    ),

    ModelSpec(
        id="openai/gpt-4o",
        provider="openrouter",
        display_name="GPT-4o (paid)",
        ram_gb=0,
        context_tokens=128000,
        fits_12gb=True,
        speed="medium",
        description="OpenAI GPT-4o via OpenRouter. Paid only.",
        is_free=False,
        tags=["paid", "powerful", "cloud"],
        scores={t: 10 for t in TaskType},
    ),
]

# ── COMBINED INDEX ─────────────────────────────────────────────────────────────

ALL_MODELS: Dict[str, ModelSpec] = {
    m.id: m for m in OLLAMA_MODELS + OPENROUTER_MODELS
}


def get_model(model_id: str) -> Optional[ModelSpec]:
    return ALL_MODELS.get(model_id)


def models_for_provider(provider: str) -> List[ModelSpec]:
    return [m for m in ALL_MODELS.values() if m.provider == provider]


def ollama_models_for_12gb() -> List[ModelSpec]:
    """All Ollama models that fit comfortably on a 12 GB RAM machine."""
    return [m for m in OLLAMA_MODELS if m.fits_12gb]


def best_ollama_for_task(task: TaskType, max_ram_gb: float = 7.0) -> Optional[ModelSpec]:
    """
    Return the highest-scoring Ollama model for a task that fits within RAM budget.
    Breaks ties by preferring faster models.
    """
    candidates = [
        m for m in OLLAMA_MODELS
        if m.fits_12gb and m.ram_gb <= max_ram_gb
    ]
    if not candidates:
        return None
    speed_order = {"fast": 0, "medium": 1, "slow": 2}
    candidates.sort(
        key=lambda m: (-m.scores.get(task, 0), speed_order.get(m.speed, 1))
    )
    return candidates[0]


def best_openrouter_for_task(task: TaskType, free_only: bool = True) -> Optional[ModelSpec]:
    """Return the highest-scoring OpenRouter model for a task."""
    candidates = [
        m for m in OPENROUTER_MODELS
        if (not free_only or m.is_free)
    ]
    if not candidates:
        return None
    speed_order = {"fast": 0, "medium": 1, "slow": 2}
    candidates.sort(
        key=lambda m: (-m.scores.get(task, 0), speed_order.get(m.speed, 1))
    )
    return candidates[0]


# ── RECOMMENDED INSTALL LIST (models to pull on setup) ────────────────────────
#
# Strategy for 12 GB RAM:
#   • llama3.2:3b         — always loaded for voice/quick (2 GB)
#   • mistral:7b-q4       — general workhorse (4 GB)
#   • deepseek-coder-v2   — code specialist (5 GB)
#   Swap between them as needed; Ollama handles unloading automatically.
#
RECOMMENDED_INSTALL = [
    "llama3.2:3b",
    "phi3:3.8b",
    "mistral:7b-instruct-q4_K_M",
    "llama3.1:8b-instruct-q4_K_M",
    "deepseek-coder-v2:16b-lite-instruct-q4_K_M",
    "codellama:7b-instruct-q4_K_M",
]

OPTIONAL_INSTALL = [
    "mixtral:8x7b-instruct-v0.1-q2_K",   # powerful but slow, 6.5 GB
]
