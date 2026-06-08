"""
J.A.Y. Research Agent — Web search, documentation reading, deep research
"""
from typing import List, Dict, Optional
import logging
import json
from app.agents.base import BaseAgent, AgentContext, AgentResult

logger = logging.getLogger(__name__)

RESEARCH_SYSTEM = """You are J.A.Y.'s Research Agent — expert at finding, analyzing, and synthesizing information.

Capabilities:
- Web search
- Documentation reading
- News analysis  
- Fact checking
- Product/competitor research
- Industry analysis

Rules:
- Always cite sources
- Distinguish facts from opinions
- Flag outdated information
- Be concise but complete
- Present confidence levels for key claims

Format your output clearly with sections, bullet points, and source citations."""


class ResearchAgent(BaseAgent):
    name = "research"
    description = "Web research, documentation, fact-finding, analysis"
    capabilities = ["web_search", "read_url", "summarize", "fact_check"]

    async def run(self, context: AgentContext) -> AgentResult:
        self._messages = []
        self._emit(f"Researching: {context.user_query[:100]}", "thought")

        # Execute research using tools
        search_results = await self._do_research(context.user_query)

        # Synthesize with LLM
        messages = [
            {
                "role": "user",
                "content": f"Research query: {context.user_query}\n\nSearch results:\n{search_results}\n\nSynthesize a comprehensive, accurate answer."
            }
        ]

        try:
            output = await self._llm(messages, system=RESEARCH_SYSTEM, temperature=0.3)
            self._emit("Research complete", "result")

            # Store in memory
            if self.memory_manager:
                await self.memory_manager.remember(
                    content=f"Research on '{context.user_query[:50]}': {output[:500]}",
                    category="research",
                    namespace="research",
                )

            return AgentResult(
                agent=self.name,
                success=True,
                output=output,
                messages=self._messages,
                tools_used=["web_search"],
            )
        except Exception as e:
            logger.error(f"Research agent error: {e}")
            return AgentResult(agent=self.name, success=False, output=str(e), error=str(e))

    async def _do_research(self, query: str) -> str:
        """Execute web search using available tools."""
        if self.tool_registry:
            try:
                tool = self.tool_registry.get_tool("web_search")
                if tool:
                    result = await tool.execute({"query": query, "max_results": 5})
                    return result.get("output", "No results found")
            except Exception as e:
                logger.warning(f"Tool search failed: {e}")

        # Fallback: DuckDuckGo direct
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            formatted = []
            for r in results:
                formatted.append(f"**{r['title']}**\n{r['body']}\nSource: {r['href']}\n")
            return "\n".join(formatted) if formatted else "No search results found."
        except Exception as e:
            return f"Search unavailable: {e}"
