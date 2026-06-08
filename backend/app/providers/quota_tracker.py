"""
J.A.Y. OpenRouter Quota Tracker
────────────────────────────────────────────────────────────────────────────────
Tracks usage of every OpenRouter free-tier model across three dimensions:

  1. Daily requests     — resets at midnight UTC
  2. Per-minute RPM     — sliding 60-second window
  3. Daily token budget — resets at midnight UTC

When any dimension is exhausted the model is marked as "blocked" and the
router skips it automatically. The next available free model is tried instead.

Persistence:
  State is written to  data/quota_state.json  every time a model is recorded.
  On startup the file is loaded so quotas survive backend restarts.

Thread safety:
  All mutations go through asyncio.Lock — safe for FastAPI's async workers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

# Path where quota state is persisted between restarts
_STATE_FILE = Path(settings.DATA_DIR) / "quota_state.json"


# ── Per-model quota bucket ─────────────────────────────────────────────────────

@dataclass
class ModelQuota:
    model_id: str

    # Daily counters (reset at UTC midnight)
    daily_requests:    int   = 0
    daily_tokens_in:   int   = 0
    daily_tokens_out:  int   = 0
    day_str:           str   = ""        # "YYYY-MM-DD" of last reset

    # RPM sliding window — stored as list for JSON serialisation
    rpm_timestamps: List[float] = field(default_factory=list)

    # Consecutive error counter (proxy for 429 / quota exhausted responses)
    consecutive_errors: int = 0

    # Manual block flag — set by operator or after too many errors
    blocked: bool = False
    blocked_reason: str = ""
    blocked_until: Optional[float] = None   # unix timestamp, None = permanent

    # ── Derived status ─────────────────────────────────────────────────────────

    def is_exhausted(
        self,
        daily_req_limit:   int,
        rpm_limit:         int,
        daily_token_limit: int,
        error_threshold:   int,
    ) -> Tuple[bool, str]:
        """
        Returns (is_exhausted, reason_string).
        Checks every dimension in priority order.
        """
        now = time.time()

        # Manual block with optional expiry
        if self.blocked:
            if self.blocked_until is None or now < self.blocked_until:
                return True, self.blocked_reason or "Manually blocked"
            # Expired block — clear it
            self.blocked = False
            self.blocked_reason = ""
            self.blocked_until = None

        # Daily request limit
        if daily_req_limit > 0 and self.daily_requests >= daily_req_limit:
            return True, f"Daily request limit reached ({self.daily_requests}/{daily_req_limit})"

        # Daily token budget
        total_tokens = self.daily_tokens_in + self.daily_tokens_out
        if daily_token_limit > 0 and total_tokens >= daily_token_limit:
            return True, f"Daily token budget exhausted ({total_tokens}/{daily_token_limit})"

        # RPM sliding window
        window_start = now - 60.0
        recent = [t for t in self.rpm_timestamps if t > window_start]
        if rpm_limit > 0 and len(recent) >= rpm_limit:
            oldest_in_window = min(recent)
            wait_s = round(60.0 - (now - oldest_in_window) + 0.5)
            return True, f"Rate limit: {len(recent)}/{rpm_limit} req/min — wait {wait_s}s"

        # Consecutive errors
        if error_threshold > 0 and self.consecutive_errors >= error_threshold:
            return True, f"Too many errors ({self.consecutive_errors}) — possible quota exhaustion"

        return False, ""

    def reset_if_new_day(self) -> bool:
        """Reset daily counters if UTC date has changed. Returns True if reset."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.day_str != today:
            self.daily_requests   = 0
            self.daily_tokens_in  = 0
            self.daily_tokens_out = 0
            self.consecutive_errors = 0
            # Don't clear permanent blocks on day reset
            if self.blocked and self.blocked_until is not None:
                if time.time() >= self.blocked_until:
                    self.blocked = False
                    self.blocked_reason = ""
                    self.blocked_until = None
            self.day_str = today
            return True
        return False

    def record_request(self, tokens_in: int = 0, tokens_out: int = 0):
        self.reset_if_new_day()
        now = time.time()
        self.daily_requests   += 1
        self.daily_tokens_in  += tokens_in
        self.daily_tokens_out += tokens_out
        self.consecutive_errors = 0   # successful request clears error streak
        # Keep only the last 120 timestamps (2-minute buffer)
        self.rpm_timestamps.append(now)
        if len(self.rpm_timestamps) > 120:
            self.rpm_timestamps = self.rpm_timestamps[-120:]

    def record_error(self, is_quota_error: bool = False):
        self.reset_if_new_day()
        self.consecutive_errors += 1
        if is_quota_error:
            self.blocked = True
            self.blocked_reason = "Quota/rate-limit error from API"
            # Block for 1 hour then retry
            self.blocked_until = time.time() + 3600.0
            logger.warning(
                f"[Quota] {self.model_id} marked exhausted — blocked for 1h"
            )

    def to_dict(self) -> dict:
        return {
            "model_id":           self.model_id,
            "daily_requests":     self.daily_requests,
            "daily_tokens_in":    self.daily_tokens_in,
            "daily_tokens_out":   self.daily_tokens_out,
            "day_str":            self.day_str,
            "rpm_timestamps":     self.rpm_timestamps[-60:],  # trim for storage
            "consecutive_errors": self.consecutive_errors,
            "blocked":            self.blocked,
            "blocked_reason":     self.blocked_reason,
            "blocked_until":      self.blocked_until,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ModelQuota":
        q = cls(model_id=data["model_id"])
        q.daily_requests     = data.get("daily_requests", 0)
        q.daily_tokens_in    = data.get("daily_tokens_in", 0)
        q.daily_tokens_out   = data.get("daily_tokens_out", 0)
        q.day_str            = data.get("day_str", "")
        q.rpm_timestamps     = data.get("rpm_timestamps", [])
        q.consecutive_errors = data.get("consecutive_errors", 0)
        q.blocked            = data.get("blocked", False)
        q.blocked_reason     = data.get("blocked_reason", "")
        q.blocked_until      = data.get("blocked_until", None)
        return q


# ── Tracker singleton ──────────────────────────────────────────────────────────

class OpenRouterQuotaTracker:
    """
    Central quota manager for all OpenRouter models.
    Used by ProviderManager to decide whether a model is available.
    """

    def __init__(self):
        self._quotas: Dict[str, ModelQuota] = {}
        self._lock = asyncio.Lock()
        self._dirty = False   # True when state needs saving

        # Load persisted state (non-async, called at import time via _load_sync)
        self._load_sync()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def is_available(self, model_id: str) -> Tuple[bool, str]:
        """
        Check if a model can be used right now.
        Returns (available, reason_if_not).
        """
        async with self._lock:
            quota = self._get_or_create(model_id)
            quota.reset_if_new_day()
            exhausted, reason = quota.is_exhausted(
                daily_req_limit   = settings.OR_FREE_DAILY_LIMIT,
                rpm_limit         = settings.OR_FREE_RPM_LIMIT,
                daily_token_limit = settings.OR_FREE_TOKENS_PER_DAY,
                error_threshold   = settings.OR_EXHAUST_ERROR_THRESHOLD,
            )
            return not exhausted, reason

    async def record_success(
        self,
        model_id: str,
        tokens_in:  int = 0,
        tokens_out: int = 0,
    ):
        """Call after every successful OpenRouter request."""
        async with self._lock:
            self._get_or_create(model_id).record_request(tokens_in, tokens_out)
            self._dirty = True
        await self._save()

    async def record_error(self, model_id: str, is_quota_error: bool = False):
        """
        Call on any OpenRouter error.
        Set is_quota_error=True for HTTP 429 or 'quota exceeded' messages.
        """
        async with self._lock:
            self._get_or_create(model_id).record_error(is_quota_error)
            self._dirty = True
        await self._save()

    async def unblock(self, model_id: str):
        """Manually unblock a model (e.g. from the Settings UI)."""
        async with self._lock:
            quota = self._get_or_create(model_id)
            quota.blocked = False
            quota.blocked_reason = ""
            quota.blocked_until = None
            quota.consecutive_errors = 0
            self._dirty = True
        await self._save()
        logger.info(f"[Quota] {model_id} manually unblocked")

    async def reset_model(self, model_id: str):
        """Reset all counters for a model."""
        async with self._lock:
            self._quotas[model_id] = ModelQuota(model_id=model_id)
            self._dirty = True
        await self._save()

    async def reset_all(self):
        """Reset every model's counters (e.g. at start of new day or manual reset)."""
        async with self._lock:
            for q in self._quotas.values():
                q.daily_requests    = 0
                q.daily_tokens_in   = 0
                q.daily_tokens_out  = 0
                q.consecutive_errors = 0
                q.rpm_timestamps    = []
            self._dirty = True
        await self._save()
        logger.info("[Quota] All OpenRouter quotas reset")

    def get_status(self) -> List[dict]:
        """Return a summary of all tracked models — used by the /model-status API."""
        now = time.time()
        result = []
        for model_id, q in self._quotas.items():
            q.reset_if_new_day()
            exhausted, reason = q.is_exhausted(
                daily_req_limit   = settings.OR_FREE_DAILY_LIMIT,
                rpm_limit         = settings.OR_FREE_RPM_LIMIT,
                daily_token_limit = settings.OR_FREE_TOKENS_PER_DAY,
                error_threshold   = settings.OR_EXHAUST_ERROR_THRESHOLD,
            )
            # RPM: requests in the last 60 seconds
            window_start = now - 60.0
            recent_rpm = len([t for t in q.rpm_timestamps if t > window_start])

            # Percent of daily budget used
            daily_pct = round(
                q.daily_requests / max(settings.OR_FREE_DAILY_LIMIT, 1) * 100, 1
            ) if settings.OR_FREE_DAILY_LIMIT else 0

            token_pct = round(
                (q.daily_tokens_in + q.daily_tokens_out)
                / max(settings.OR_FREE_TOKENS_PER_DAY, 1) * 100, 1
            ) if settings.OR_FREE_TOKENS_PER_DAY else 0

            result.append({
                "model_id":           model_id,
                "available":          not exhausted,
                "exhausted_reason":   reason if exhausted else "",
                "daily_requests":     q.daily_requests,
                "daily_req_limit":    settings.OR_FREE_DAILY_LIMIT,
                "daily_req_pct":      daily_pct,
                "daily_tokens":       q.daily_tokens_in + q.daily_tokens_out,
                "daily_token_limit":  settings.OR_FREE_TOKENS_PER_DAY,
                "daily_token_pct":    token_pct,
                "rpm_current":        recent_rpm,
                "rpm_limit":          settings.OR_FREE_RPM_LIMIT,
                "consecutive_errors": q.consecutive_errors,
                "blocked":            q.blocked,
                "blocked_reason":     q.blocked_reason,
                "blocked_until":      (
                    datetime.fromtimestamp(q.blocked_until, tz=timezone.utc).isoformat()
                    if q.blocked_until else None
                ),
                "day_str":            q.day_str,
            })

        # Sort: available first, then by model_id
        result.sort(key=lambda x: (x["blocked"], x["model_id"]))
        return result

    def is_quota_error_response(self, status_code: int, body: str) -> bool:
        """
        Heuristic: detect whether an HTTP response from OpenRouter
        indicates quota / rate-limit exhaustion.
        """
        if status_code == 429:
            return True
        if status_code in (402, 403):
            return True
        body_lower = body.lower()
        quota_phrases = [
            "quota", "rate limit", "rate_limit", "exceeded",
            "too many requests", "out of credits", "insufficient credits",
            "context length exceeded",  # model-level limit
        ]
        return any(p in body_lower for p in quota_phrases)

    # ── Persistence ────────────────────────────────────────────────────────────

    async def _save(self):
        if not self._dirty:
            return
        try:
            os.makedirs(_STATE_FILE.parent, exist_ok=True)
            payload = {
                "version": 1,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "quotas": {mid: q.to_dict() for mid, q in self._quotas.items()},
            }
            tmp = _STATE_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2))
            tmp.replace(_STATE_FILE)
            self._dirty = False
        except Exception as e:
            logger.warning(f"[Quota] Could not save state: {e}")

    def _load_sync(self):
        """Load persisted quota state at startup (synchronous)."""
        if not _STATE_FILE.exists():
            return
        try:
            raw = json.loads(_STATE_FILE.read_text())
            for mid, data in raw.get("quotas", {}).items():
                q = ModelQuota.from_dict(data)
                q.reset_if_new_day()   # clear stale daily counters
                self._quotas[mid] = q
            logger.info(
                f"[Quota] Loaded quota state for {len(self._quotas)} OpenRouter models"
            )
        except Exception as e:
            logger.warning(f"[Quota] Could not load state: {e}")

    def _get_or_create(self, model_id: str) -> ModelQuota:
        if model_id not in self._quotas:
            self._quotas[model_id] = ModelQuota(model_id=model_id)
        return self._quotas[model_id]


# ── Global singleton ───────────────────────────────────────────────────────────
quota_tracker = OpenRouterQuotaTracker()
