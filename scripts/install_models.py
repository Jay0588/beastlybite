#!/usr/bin/env python3
"""
J.A.Y. Ollama Model Installer — Python (cross-platform fallback)
Works on Windows, Linux, and macOS without any extra dependencies.

Usage:
    python scripts/install_models.py              # recommended set
    python scripts/install_models.py --all        # everything
    python scripts/install_models.py --minimal    # tiny models only
    python scripts/install_models.py --check      # show status
    python scripts/install_models.py --custom     # interactive picker
    python scripts/install_models.py --model llama3.2:3b  # one model
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import List, Optional

# ── ANSI colours (disabled on Windows if not supported) ──────────────────────

def _ansi_supported() -> bool:
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32        # type: ignore
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    return True

USE_COLOR = _ansi_supported() and sys.stdout.isatty()

def c(text: str, code: str) -> str:
    if not USE_COLOR:
        return text
    codes = {"green": "32", "cyan": "36", "yellow": "33",
             "red": "31", "bold": "1", "dim": "2", "reset": "0"}
    return f"\033[{codes.get(code, '0')}m{text}\033[0m"


# ── Model catalogue ───────────────────────────────────────────────────────────

@dataclass
class Model:
    id:      str
    ram_gb:  float
    speed:   str
    purpose: str
    tier:    str          # minimal | recommended | optional


MODELS: List[Model] = [
    # ── Minimal (tiny, fast, always safe on 12 GB) ───────────────────────────
    Model("llama3.2:3b",                                    2.0, "fast",   "Quick answers · voice replies · memory",      "minimal"),
    Model("phi3:3.8b",                                      2.3, "fast",   "Fast reasoning · 128K context",               "minimal"),

    # ── Recommended (core working set) ───────────────────────────────────────
    Model("mistral:7b-instruct-q4_K_M",                     4.1, "medium", "General workhorse · trading · tools",         "recommended"),
    Model("llama3.1:8b-instruct-q4_K_M",                    4.7, "medium", "Strong general AI · planning · 128K ctx",     "recommended"),
    Model("deepseek-coder-v2:16b-lite-instruct-q4_K_M",     4.9, "medium", "Best local code model",                       "recommended"),
    Model("codellama:7b-instruct-q4_K_M",                   3.8, "medium", "Code fallback (lighter)",                     "recommended"),

    # ── Optional (powerful but needs more RAM / time) ─────────────────────────
    Model("mixtral:8x7b-instruct-v0.1-q2_K",               6.5, "slow",   "Powerful MoE · heavy analysis (q2)",          "optional"),
]


# ── Ollama helpers ────────────────────────────────────────────────────────────

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")

    def is_running(self) -> bool:
        try:
            urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=4)
            return True
        except Exception:
            return False

    def installed_models(self) -> List[str]:
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=8) as r:
                data = json.loads(r.read())
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def is_installed(self, model_id: str) -> bool:
        return model_id in self.installed_models()

    def pull(self, model_id: str) -> bool:
        """Pull a model using the `ollama` CLI — streams progress to stdout."""
        print(f"    Running: ollama pull {model_id}")
        try:
            result = subprocess.run(
                ["ollama", "pull", model_id],
                check=False,
            )
            return result.returncode == 0
        except FileNotFoundError:
            print(c("  ✗ `ollama` binary not found in PATH.", "red"))
            return False

    def start_server(self) -> bool:
        """Try to start `ollama serve` in the background."""
        try:
            kwargs: dict = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore
            subprocess.Popen(["ollama", "serve"], **kwargs)
            import time; time.sleep(3)
            return self.is_running()
        except Exception:
            return False


# ── Installer logic ───────────────────────────────────────────────────────────

class Installer:
    def __init__(self, ollama: OllamaClient, ram_budget: float):
        self.ollama     = ollama
        self.ram_budget = ram_budget

    # ── Public modes ──────────────────────────────────────────────────────────

    def check(self):
        installed = self.ollama.installed_models()
        self._print_catalogue(installed)

    def install(self, tier_filter: Optional[List[str]] = None):
        """Install models matching tier_filter. None = all tiers."""
        for m in MODELS:
            if tier_filter and m.tier not in tier_filter:
                continue
            self._pull_if_needed(m)

    def install_one(self, model_id: str):
        """Install a single model by ID."""
        for m in MODELS:
            if m.id == model_id:
                self._pull_if_needed(m)
                return
        # Not in catalogue — pull anyway
        print(f"\n  {c('?', 'yellow')}  {model_id} not in catalogue — pulling anyway")
        if self.ollama.pull(model_id):
            print(f"  {c('✓', 'green')}  {model_id} installed")
        else:
            print(f"  {c('✗', 'red')}  Pull failed for {model_id}")

    def interactive(self):
        self._print_catalogue(self.ollama.installed_models())
        print("Enter model IDs to install (space-separated), or press Enter to cancel:")
        try:
            choice = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return
        if not choice:
            print("Cancelled.")
            return
        for mid in choice.split():
            self.install_one(mid)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _pull_if_needed(self, m: Model):
        prefix = f"  [{m.ram_gb}GB {m.speed:6s}]  {m.id}"

        if self.ollama.is_installed(m.id):
            print(f"  {c('✓', 'green')} {m.id:<52} {c('(already installed)', 'dim')}")
            return

        if m.ram_gb > self.ram_budget:
            skip_msg = f"needs {m.ram_gb} GB > budget {self.ram_budget} GB"
            print(f"  {c('⚠', 'yellow')} {m.id:<52} {c(f'skipped — {skip_msg}', 'yellow')}")
            return

        print(f"\n  {c('↓', 'cyan')} Pulling {c(m.id, 'bold')}  "
              f"({m.ram_gb} GB · {m.speed} · {m.purpose})")
        ok = self.ollama.pull(m.id)
        if ok:
            print(f"  {c('✓', 'green')} {m.id} installed successfully")
        else:
            print(f"  {c('✗', 'red')} Pull failed for {m.id}")

    def _print_catalogue(self, installed: List[str]):
        print(f"\n{'─' * 70}")
        header = f"  {'Model ID':<52} {'RAM':<6} {'Speed':<8} Tier"
        print(c(header, "bold"))
        print(f"  {'─' * 52} {'────':<6} {'────────':<8} ────")

        for m in MODELS:
            is_inst = m.id in installed
            fits    = m.ram_gb <= self.ram_budget

            if is_inst:
                mark = c("✓", "green")
            elif not fits:
                mark = c("!", "yellow")
            else:
                mark = " "

            tier_fmt = {
                "minimal":     c("minimal",     "green"),
                "recommended": c("recommended", "cyan"),
                "optional":    c("optional",    "dim"),
            }.get(m.tier, m.tier)

            print(f"  {mark} {m.id:<52} {m.ram_gb:<6} {m.speed:<8} {tier_fmt}")

        print(f"{'─' * 70}")
        print(f"\n  Installed: {len([m for m in MODELS if m.id in installed])}/{len(MODELS)} "
              f"registry models")
        print(f"  RAM budget: {self.ram_budget} GB\n")


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(ollama: OllamaClient):
    installed = ollama.installed_models()
    print()
    print(c("╔══════════════════════════════════════════════════╗", "green"))
    print(c("║          Model installation complete             ║", "green"))
    print(c("╚══════════════════════════════════════════════════╝", "green"))
    print()
    if not installed:
        print(f"  {c('No models installed.', 'yellow')}")
    else:
        for m in installed:
            print(f"  {c('✓', 'green')}  {m}")
    print()
    print(c("  J.A.Y. will automatically choose the right model per task.", "dim"))
    print(c("  Start backend: cd backend && uvicorn app.main:app --reload",  "dim"))
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="J.A.Y. Ollama model installer",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--all",        action="store_true", help="Install all models")
    parser.add_argument("--minimal",    action="store_true", help="Install minimal set (< 3 GB)")
    parser.add_argument("--check",      action="store_true", help="Show installation status")
    parser.add_argument("--custom",     action="store_true", help="Interactive picker")
    parser.add_argument("--model",      type=str,            help="Install a specific model ID")
    parser.add_argument("--url",        type=str,            default=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
    parser.add_argument("--ram-budget", type=float,          default=float(os.environ.get("OLLAMA_RAM_BUDGET_GB", "7.0")))
    args = parser.parse_args()

    # Header
    print()
    print(c("╔══════════════════════════════════════════════════╗", "cyan"))
    print(c("║     J.A.Y.  Ollama Model Installer               ║", "cyan"))
    print(c("╚══════════════════════════════════════════════════╝", "cyan"))
    print()
    print(f"  Ollama URL:  {args.url}")
    print(f"  RAM budget:  {args.ram_budget} GB")
    print()

    ollama = OllamaClient(args.url)

    # Ensure Ollama is running
    if not ollama.is_running():
        print(c("  ⚠  Ollama not responding — attempting to start...", "yellow"))
        if not ollama.start_server():
            print(c("\n  ✗ Cannot reach Ollama.", "red"))
            print("    • Install from: https://ollama.ai/download")
            print("    • Then run:     ollama serve")
            sys.exit(1)

    print(c("  ✓ Ollama is running", "green"))

    installer = Installer(ollama, args.ram_budget)

    if args.check:
        installer.check()
        return

    if args.model:
        installer.install_one(args.model)
        print_summary(ollama)
        return

    if args.minimal:
        print(c("\n  Installing minimal set:", "cyan"))
        installer.install(["minimal"])
    elif args.all:
        print(c("\n  Installing ALL models:", "yellow"))
        installer.install()
    elif args.custom:
        installer.interactive()
    else:
        # Default: recommended
        print(c("\n  Installing recommended set:", "cyan"))
        print(c(f"  (models over {args.ram_budget} GB will be skipped)\n", "dim"))
        installer.install(["minimal", "recommended"])

    print_summary(ollama)


if __name__ == "__main__":
    main()
