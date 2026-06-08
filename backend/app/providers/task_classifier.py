"""
J.A.Y. Task Classifier
Analyzes a message and returns its TaskType so the router can pick the right model.
"""
from enum import Enum
from typing import Optional
import re


class TaskType(str, Enum):
    # Conversation / quick answers
    CHAT        = "chat"          # simple question, small talk
    QUICK       = "quick"         # one-liner lookup, yes/no, math

    # Technical
    CODE        = "code"          # write / debug / review code
    CODE_HEAVY  = "code_heavy"    # full app scaffold, architecture review

    # Reasoning
    PLAN        = "plan"          # multi-step planning, task breakdown
    ANALYSIS    = "analysis"      # deep analysis, comparison, research synthesis

    # Domain-specific
    TRADING     = "trading"       # market analysis, indicators, strategy
    RESEARCH    = "research"      # web search summary, fact-finding
    CREATIVE    = "creative"      # image prompts, marketing copy, UI ideas
    MEMORY      = "memory"        # store / recall user facts

    # System
    TOOL        = "tool"          # direct tool execution (terminal, file ops)
    VOICE       = "voice"         # short, natural spoken responses


# ── Keyword patterns per task type ────────────────────────────────────────────

_PATTERNS: list[tuple[TaskType, list[str]]] = [
    # Code — check before CHAT so "fix bug" doesn't fall through
    (TaskType.CODE_HEAVY, [
        r"\bscaffold\b", r"\bfull.?app\b", r"\bbuild.{0,20}(app|system|platform|dashboard|api|website)\b",
        r"\barchitect\b", r"\brefactor.{0,30}entire\b", r"\bmigrat\b",
        r"\bgenerate.{0,20}(project|codebase|boilerplate)\b",
    ]),
    (TaskType.CODE, [
        r"\b(code|script|function|class|method|module|component)\b",
        r"\b(debug|fix|error|bug|exception|traceback|stacktrace)\b",
        r"\b(write|create|implement|build).{0,30}(function|class|api|endpoint|route|hook)\b",
        r"\b(python|javascript|typescript|rust|go|java|c\+\+|sql|bash|html|css|react|next\.?js|fastapi|django)\b",
        r"\b(test|unittest|pytest|jest|spec)\b",
        r"\b(git|commit|pull.?request|pr|merge|branch|diff)\b",
        r"```",
    ]),

    # Trading
    (TaskType.TRADING, [
        r"\b(nse|bse|nifty|sensex|forex|crypto|bitcoin|btc|eth|stock|equity|index)\b",
        r"\b(rsi|macd|ema|sma|vwap|atr|bollinger|candlestick|chart|indicator)\b",
        r"\b(buy|sell|long|short|trade|position|entry|exit|stop.?loss|take.?profit)\b",
        r"\b(backtest|strategy|paper.?trad|portfolio|watchlist|signal)\b",
        r"\b(market|price|volume|breakout|support|resistance|trend)\b",
    ]),

    # Research
    (TaskType.RESEARCH, [
        r"\b(search|find|look.?up|research|what is|who is|explain|summarize)\b",
        r"\b(latest|recent|news|update|article|documentation|docs)\b",
        r"\bhttps?://\S+",
        r"\b(compare|difference between|pros and cons|versus|vs\.?)\b",
    ]),

    # Creative
    (TaskType.CREATIVE, [
        r"\b(generate|create|design|make).{0,25}(image|logo|banner|thumbnail|poster|ad|ui|mockup)\b",
        r"\b(marketing|copy|slogan|headline|caption|social.?media|youtube|instagram)\b",
        r"\b(prompt.{0,15}(stable.?diffusion|midjourney|dall.?e))\b",
        r"\b(color.?palette|typography|wireframe|ui.?concept)\b",
    ]),

    # Memory
    (TaskType.MEMORY, [
        r"\b(remember|store|save|memorize|note.?that|don.?t.?forget)\b",
        r"\b(recall|what.?did.?i|do.?you.?know|what.?do.?i|you.?know.?that)\b",
        r"\b(my.{0,20}(name|preference|habit|favorite|usually|always|never))\b",
    ]),

    # Plan
    (TaskType.PLAN, [
        r"\b(plan|roadmap|steps|breakdown|how.?to.?build|how.?should.?i|strategy.?for)\b",
        r"\b(project.?plan|sprint|milestone|timeline|todo.?list|prioritize)\b",
    ]),

    # Analysis (heavier reasoning)
    (TaskType.ANALYSIS, [
        r"\b(analyz|evaluat|assess|review|audit|deep.?dive|thorough)\b",
        r"\b(why.{0,20}(good|bad|better|worse|fail|work)|trade.?off|pros|cons)\b",
        r"\b(report|insight|recommendation|suggest.{0,10}based.?on)\b",
    ]),

    # Tool
    (TaskType.TOOL, [
        r"\b(open|launch|start|run|execute|install|uninstall)\b.{0,20}\b(app|application|program|chrome|vscode|spotify|steam|terminal)\b",
        r"\b(create|delete|move|rename|copy|find).{0,20}\b(file|folder|directory)\b",
        r"\brun.{0,10}(command|cmd|bash|shell|script|terminal)\b",
    ]),

    # Quick — very short / trivial
    (TaskType.QUICK, [
        r"^.{0,60}[\?\.]?$",  # Short message heuristic handled in code
    ]),
]

_QUICK_MAX_WORDS = 10


def classify(message: str, conversation_history: Optional[list] = None) -> TaskType:
    """
    Classify a user message into a TaskType.
    Falls back to CHAT if nothing matches.
    """
    text = message.lower().strip()
    word_count = len(text.split())

    # Very short message → QUICK (cheap model)
    if word_count <= _QUICK_MAX_WORDS and "?" in text and not any(
        kw in text for kw in ["code", "build", "implement", "trade", "analyze"]
    ):
        return TaskType.QUICK

    for task_type, patterns in _PATTERNS:
        # Skip the QUICK catch-all pattern — handled above
        if task_type == TaskType.QUICK:
            continue
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return task_type

    # Default: plain conversation
    return TaskType.CHAT


def task_label(tt: TaskType) -> str:
    labels = {
        TaskType.CHAT:       "Conversation",
        TaskType.QUICK:      "Quick answer",
        TaskType.CODE:       "Code",
        TaskType.CODE_HEAVY: "Heavy coding",
        TaskType.PLAN:       "Planning",
        TaskType.ANALYSIS:   "Deep analysis",
        TaskType.TRADING:    "Trading analysis",
        TaskType.RESEARCH:   "Research",
        TaskType.CREATIVE:   "Creative",
        TaskType.MEMORY:     "Memory",
        TaskType.TOOL:       "Tool execution",
        TaskType.VOICE:      "Voice response",
    }
    return labels.get(tt, tt.value)
