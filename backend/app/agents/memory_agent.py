"""
J.A.Y. Memory Agent — Manages long-term memory storage and retrieval
"""
from typing import List, Dict, Optional
import logging
from app.agents.base import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger(__name__)

MEMORY_SYSTEM = """You are J.A.Y.'s Memory Agent — responsible for managing long-term memory.

Your job:
- Extract important information from conversations to remember
- Retrieve relevant memories based on context
- Maintain the user's knowledge base
- Identify connections between memories

When storing memories:
- Be precise and factual
- Categorize correctly: preference, fact, habit, project, lesson, contact, task, research
- Set appropriate importance (0.0-1.0)
- Use clear, retrievable language

When recalling:
- Retrieve the most relevant memories
- Present them clearly
- Note when memories might be outdated"""


class MemoryAgent(BaseAgent):
    name = "memory"
    description = "Manages long-term memory — store, retrieve, and organize information"
    capabilities = ["store_memory", "recall_memory", "search_memory", "forget_memory"]

    async def run(self, context: AgentContext) -> AgentResult:
        self._messages = []
        self._emit(f"Memory task: {context.user_query[:100]}", "thought")

        action = self._detect_action(context.user_query)

        try:
            if action == "store":
                output = await self._handle_store(context)
            elif action == "recall":
                output = await self._handle_recall(context)
            elif action == "list":
                output = await self._handle_list(context)
            elif action == "delete":
                output = await self._handle_delete(context)
            else:
                output = await self._handle_search(context)

            return AgentResult(
                agent=self.name,
                success=True,
                output=output,
                messages=self._messages,
            )
        except Exception as e:
            logger.error(f"Memory agent error: {e}")
            return AgentResult(agent=self.name, success=False, output=str(e), error=str(e))

    def _detect_action(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ["remember", "store", "save", "note", "memorize"]):
            return "store"
        elif any(w in q for w in ["recall", "what did i", "what do i", "do you remember", "did i tell"]):
            return "recall"
        elif any(w in q for w in ["list all", "show all", "all my", "everything you know"]):
            return "list"
        elif any(w in q for w in ["forget", "delete", "remove", "clear"]):
            return "delete"
        return "search"

    async def _handle_store(self, context: AgentContext) -> str:
        if not self.memory_manager:
            return "Memory system not available"

        # Extract what to remember
        query = context.user_query
        doc_id = await self.memory_manager.remember(
            content=query,
            category="fact",
            importance=0.7,
        )
        self._emit(f"Stored memory: {doc_id}", "action")
        return f"✓ Remembered: \"{query}\"\n\nI'll recall this in future conversations when relevant."

    async def _handle_recall(self, context: AgentContext) -> str:
        if not self.memory_manager:
            return "Memory system not available"

        memories = await self.memory_manager.recall(context.user_query, n=8)
        if not memories:
            return "I don't have any relevant memories for that query."

        lines = ["**Retrieved Memories:**\n"]
        for m in memories:
            score = m.get("score", 0)
            cat = m["metadata"].get("category", "general")
            lines.append(f"• [{cat}] {m['content']} *(relevance: {score:.0%})*")

        return "\n".join(lines)

    async def _handle_list(self, context: AgentContext) -> str:
        if not self.memory_manager:
            return "Memory system not available"

        from app.memory.store import memory_store
        memories = await memory_store.get_all(namespace="general")
        if not memories:
            return "No memories stored yet."

        lines = [f"**All Memories** ({len(memories)} entries)\n"]
        for m in memories[:20]:  # Limit display
            cat = m["metadata"].get("category", "general")
            lines.append(f"• [{cat}] {m['content'][:100]}")

        if len(memories) > 20:
            lines.append(f"\n... and {len(memories) - 20} more")
        return "\n".join(lines)

    async def _handle_delete(self, context: AgentContext) -> str:
        return "To delete a specific memory, please provide its ID or the exact content to remove. I'll confirm before deleting."

    async def _handle_search(self, context: AgentContext) -> str:
        if not self.memory_manager:
            return "Memory system not available"

        results = await self.memory_manager.search_all_namespaces(context.user_query, n=8)
        if not results:
            return f"No memories found related to: {context.user_query}"

        lines = [f"**Memory Search: '{context.user_query[:50]}'**\n"]
        for r in results:
            ns = r.get("namespace", "general")
            cat = r["metadata"].get("category", "general")
            score = r.get("score", 0)
            lines.append(f"• [{ns}/{cat}] {r['content'][:120]} *(relevance: {score:.0%})*")
        return "\n".join(lines)
