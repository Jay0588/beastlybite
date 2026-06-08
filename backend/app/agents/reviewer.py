"""
J.A.Y. Reviewer Agent — Reviews code, plans, and outputs for quality
"""
from typing import List, Dict, Optional
import logging
from app.agents.base import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger(__name__)

REVIEWER_SYSTEM = """You are J.A.Y.'s Reviewer Agent — a rigorous quality assurance expert.

You review: code, plans, strategies, analyses, and any output for quality.

Code Review criteria:
- Correctness: Does it do what it's supposed to?
- Security: SQL injection, XSS, auth flaws, secrets in code?
- Performance: O(n²) where O(n) is possible? N+1 queries?
- Maintainability: Is it readable? Self-documenting?
- Error handling: All edge cases covered?
- Testing: Is it testable? Are tests present?
- Best practices: Language-specific conventions?

Plan Review criteria:
- Completeness: Are all steps accounted for?
- Risks: What could go wrong?
- Assumptions: What's being assumed without verification?
- Alternatives: Is this the best approach?
- Dependencies: Are there blockers?

Output format:
## Review Summary
**Overall: PASS / NEEDS_WORK / FAIL**

## Issues Found
### Critical (must fix):
- Issue with explanation and fix

### Major (should fix):
- Issue with explanation and fix

### Minor (consider fixing):
- Issue with explanation

## Positive Aspects
- What's done well

## Recommendations
- Actionable next steps

Be thorough but fair. Praise what's good. Be specific about problems."""


class ReviewerAgent(BaseAgent):
    name = "reviewer"
    description = "Reviews code, plans, and outputs for quality, security, and correctness"
    capabilities = ["review_code", "review_plan", "security_audit", "performance_review"]

    async def run(self, context: AgentContext) -> AgentResult:
        self._messages = []
        self._emit(f"Reviewing: {context.user_query[:100]}", "thought")

        messages = [{"role": "user", "content": context.user_query}]

        # Include previous agent output if available
        prev_results = context.metadata.get("previous_results", {})
        if prev_results:
            import json
            prev_text = "\n\n".join([f"**{k} output:**\n{v}" for k, v in prev_results.items()])
            messages[0]["content"] += f"\n\nContent to review:\n{prev_text}"

        try:
            output = await self._llm(messages, system=REVIEWER_SYSTEM, temperature=0.2)
            self._emit("Review complete", "result")

            return AgentResult(
                agent=self.name,
                success=True,
                output=output,
                messages=self._messages,
            )
        except Exception as e:
            logger.error(f"Reviewer agent error: {e}")
            return AgentResult(agent=self.name, success=False, output=str(e), error=str(e))
