"""
J.A.Y. Coding Agent — Professional software engineer. Builds, debugs, reviews, architects software.
"""
from typing import List, Dict, Optional
import logging
import json
import os
from app.agents.base import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger(__name__)

CODING_SYSTEM = """You are J.A.Y.'s Coding Agent — a world-class software engineer with expertise in:
- Web: React, Next.js, Vue, Angular, TypeScript, JavaScript
- Backend: Python (FastAPI, Django), Node.js, Go, Rust
- Mobile: React Native, Flutter
- Databases: PostgreSQL, MySQL, SQLite, MongoDB, Redis
- Cloud: AWS, GCP, Azure, Docker, Kubernetes
- AI/ML: Python, PyTorch, TensorFlow, LangChain
- Trading: algorithmic trading, technical analysis systems
- Game Development: Unity, Unreal, Godot

Engineering Principles:
- Write clean, maintainable, well-documented code
- Follow SOLID principles and design patterns
- Consider security, performance, scalability from the start
- Write tests alongside code
- Use TypeScript/type hints everywhere
- Catch edge cases

When building software:
1. Clarify requirements if ambiguous
2. Propose architecture before writing code
3. Write complete, working code (no placeholders)
4. Explain key design decisions
5. Identify potential issues and how to solve them

When debugging:
1. Analyze error systematically
2. Identify root cause, not just symptoms
3. Fix the right thing
4. Explain what went wrong and why

Always produce production-ready code."""


class CodingAgent(BaseAgent):
    name = "coding"
    description = "Professional software engineer — builds, debugs, reviews, architects software"
    capabilities = [
        "write_code", "debug", "review_code", "architecture", "git",
        "run_tests", "refactor", "documentation", "scan_project"
    ]

    async def run(self, context: AgentContext) -> AgentResult:
        self._messages = []
        self._emit(f"Coding task: {context.user_query[:100]}", "thought")

        # Detect task type
        task_type = self._detect_task_type(context.user_query)
        self._emit(f"Task type: {task_type}", "thought")

        # Get project context if available
        project_context = ""
        if context.project_context:
            project_context = f"\nProject context:\n{json.dumps(context.project_context, indent=2)}"

        messages = [
            {
                "role": "user",
                "content": f"{context.user_query}{project_context}"
            }
        ]

        try:
            # Execute relevant tools
            tool_output = await self._execute_tools(task_type, context)
            if tool_output:
                messages[0]["content"] += f"\n\nTool results:\n{tool_output}"

            output = await self._llm(messages, system=CODING_SYSTEM, temperature=0.2)
            self._emit("Code generation complete", "result")

            # Store code lesson in memory
            if self.memory_manager and len(output) > 100:
                await self.memory_manager.remember(
                    content=f"Code solution for: {context.user_query[:80]}",
                    category="lesson",
                    namespace="code",
                    importance=0.6,
                )

            return AgentResult(
                agent=self.name,
                success=True,
                output=output,
                messages=self._messages,
                tools_used=["write_code"],
            )
        except Exception as e:
            logger.error(f"Coding agent error: {e}")
            return AgentResult(agent=self.name, success=False, output=str(e), error=str(e))

    def _detect_task_type(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ["debug", "fix", "error", "bug", "broken"]):
            return "debug"
        elif any(w in q for w in ["review", "analyze", "check", "audit"]):
            return "review"
        elif any(w in q for w in ["refactor", "improve", "optimize", "clean"]):
            return "refactor"
        elif any(w in q for w in ["test", "unittest", "spec"]):
            return "testing"
        elif any(w in q for w in ["git", "commit", "push", "pr", "pull request"]):
            return "git"
        elif any(w in q for w in ["scan", "understand", "architecture", "structure"]):
            return "scan"
        else:
            return "build"

    async def _execute_tools(self, task_type: str, context: AgentContext) -> str:
        if not self.tool_registry:
            return ""
        results = []
        try:
            if task_type == "scan" and context.project_context:
                path = context.project_context.get("path", "")
                if path and os.path.exists(path):
                    tool = self.tool_registry.get_tool("scan_project")
                    if tool:
                        r = await tool.execute({"path": path})
                        results.append(f"Project scan:\n{r.get('output', '')}")
            elif task_type == "git":
                tool = self.tool_registry.get_tool("git_status")
                if tool:
                    r = await tool.execute({})
                    results.append(f"Git status:\n{r.get('output', '')}")
        except Exception as e:
            logger.warning(f"Tool execution in coding agent failed: {e}")
        return "\n".join(results)
