"""
J.A.Y. Planner Agent — Breaks complex tasks into structured execution plans
"""
from typing import List, Dict, Optional
import json
import re
import logging
from app.agents.base import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger(__name__)

PLANNER_SYSTEM = """You are J.A.Y.'s Planner Agent — expert at breaking down complex goals into actionable plans.

Your job: Transform a user's goal into a clear, step-by-step execution plan.

Plan format (JSON):
{
  "goal": "clear statement of what we're building/doing",
  "complexity": "simple|moderate|complex",
  "estimated_time": "X minutes/hours",
  "risks": ["risk1", "risk2"],
  "assumptions": ["assumption1"],
  "steps": [
    {
      "id": 1,
      "title": "Step title",
      "description": "What to do",
      "agent": "coding|research|market|creative|memory|none",
      "tools": ["tool1"],
      "depends_on": [],
      "estimated_time": "5 minutes",
      "success_criteria": "How we know this step is done"
    }
  ],
  "alternatives": ["Alternative approach 1"],
  "questions": ["Any clarification needed?"]
}

Be thorough. Identify risks. Challenge assumptions. Suggest alternatives."""


class PlannerAgent(BaseAgent):
    name = "planner"
    description = "Creates structured execution plans for complex tasks"
    capabilities = ["planning", "task_breakdown", "risk_analysis"]

    async def run(self, context: AgentContext) -> AgentResult:
        self._messages = []
        self._emit(f"Planning: {context.user_query[:100]}", "thought")

        messages = [{"role": "user", "content": f"Create a plan for: {context.user_query}"}]
        if context.metadata.get("previous_results"):
            prev = json.dumps(context.metadata["previous_results"], indent=2)
            messages[0]["content"] += f"\n\nContext from previous steps:\n{prev}"

        try:
            raw = await self._llm(messages, system=PLANNER_SYSTEM, temperature=0.4)
            plan = self._parse_plan(raw)
            self._emit(f"Plan created: {len(plan.get('steps', []))} steps", "result")

            # Format for human consumption
            output = self._format_plan(plan)
            return AgentResult(
                agent=self.name,
                success=True,
                output=output,
                messages=self._messages,
            )
        except Exception as e:
            logger.error(f"Planner error: {e}")
            return AgentResult(agent=self.name, success=False, output=str(e), error=str(e))

    def _parse_plan(self, raw: str) -> Dict:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        return {"goal": "Plan", "steps": [], "raw": raw}

    def _format_plan(self, plan: Dict) -> str:
        lines = [f"**Goal:** {plan.get('goal', 'N/A')}"]
        lines.append(f"**Complexity:** {plan.get('complexity', 'moderate')} | **ETA:** {plan.get('estimated_time', 'unknown')}")

        if plan.get("risks"):
            lines.append("\n**Risks:**")
            for r in plan["risks"]:
                lines.append(f"  ⚠️ {r}")

        if plan.get("steps"):
            lines.append("\n**Execution Plan:**")
            for step in plan["steps"]:
                lines.append(f"\n{step['id']}. **{step['title']}**")
                lines.append(f"   {step['description']}")
                if step.get("agent") and step["agent"] != "none":
                    lines.append(f"   Agent: `{step['agent']}`")
                if step.get("tools"):
                    lines.append(f"   Tools: {', '.join(step['tools'])}")

        if plan.get("alternatives"):
            lines.append("\n**Alternatives:**")
            for alt in plan["alternatives"]:
                lines.append(f"  💡 {alt}")

        if plan.get("questions"):
            lines.append("\n**Questions before proceeding:**")
            for q in plan["questions"]:
                lines.append(f"  ❓ {q}")

        return "\n".join(lines)
