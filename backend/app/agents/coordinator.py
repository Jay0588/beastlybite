"""
J.A.Y. Coordinator Agent — Routes requests to the right agents, orchestrates multi-agent tasks
"""
from typing import Dict, List, Optional, AsyncGenerator
import logging
import json
from app.agents.base import BaseAgent, AgentContext, AgentResult, AgentMessage
from app.core.events import event_bus, Events

logger = logging.getLogger(__name__)

COORDINATOR_SYSTEM = """You are J.A.Y.'s Coordinator — an expert at understanding user intent and routing tasks.

Your personality: Calm, confident, professional, subtly witty. Never a yes-man. Think like a senior engineer and trusted advisor.

You have these specialized agents available:
- planner: Break down complex multi-step tasks into plans
- research: Web search, documentation, fact-finding
- coding: Write code, debug, architect software, analyze codebases
- market: Trading analysis, market data, technical analysis, strategies
- creative: Generate images, videos, UI concepts, marketing materials
- memory: Store/retrieve long-term information
- reviewer: Review code, plans, or outputs for quality and correctness

Rules:
1. For simple questions/conversation → answer directly as J.A.Y. (no sub-agents needed)
2. For complex tasks → use planner first, then relevant agents
3. For coding tasks → use coding agent
4. For research → use research agent
5. For trading/market questions → use market agent
6. Be honest about limitations
7. Challenge bad ideas diplomatically
8. Always explain your reasoning

Respond in JSON:
{
  "response_type": "direct|multi_agent|single_agent",
  "direct_response": "...",  // if response_type is direct
  "agents_to_use": ["planner", "coding"],  // if multi_agent
  "primary_agent": "coding",  // if single_agent
  "reasoning": "why this routing decision",
  "requires_approval": false,
  "clarification_needed": false,
  "clarification_question": ""
}
"""


class CoordinatorAgent(BaseAgent):
    name = "coordinator"
    description = "Routes requests and orchestrates multi-agent collaboration"
    capabilities = ["routing", "orchestration", "conversation", "planning"]

    def __init__(self, provider_manager=None, tool_registry=None, memory_manager=None, agent_registry=None):
        super().__init__(provider_manager, tool_registry, memory_manager)
        self.agent_registry: Dict[str, BaseAgent] = agent_registry or {}

    async def run(self, context: AgentContext) -> AgentResult:
        self._messages = []
        self.status = "thinking"

        # Get memory context
        memory_ctx = ""
        if self.memory_manager:
            memory_ctx = await self.memory_manager.build_context(context.user_query)

        self._emit(f"Analyzing: {context.user_query[:100]}", "thought")
        await event_bus.publish(Events.AGENT_THINKING, {"agent": self.name, "query": context.user_query})

        # Build conversation history
        messages = [{"role": m["role"], "content": m["content"]} for m in context.messages[-6:]]
        messages.append({"role": "user", "content": context.user_query})

        system = COORDINATOR_SYSTEM
        if memory_ctx:
            system += f"\n\n{memory_ctx}"

        # Ask LLM to route
        try:
            raw = await self._llm(messages, system=system, temperature=0.3)
            routing = self._parse_routing(raw)
        except Exception as e:
            logger.error(f"Routing failed: {e}")
            routing = {"response_type": "direct", "direct_response": f"I encountered an issue: {e}"}

        response_type = routing.get("response_type", "direct")
        self._emit(f"Route decision: {response_type} | {routing.get('reasoning', '')}", "thought")

        if response_type == "direct":
            result_text = routing.get("direct_response", "I'm not sure how to respond to that.")
            self.status = "complete"
            await event_bus.publish(Events.AGENT_COMPLETED, {"agent": self.name})
            return AgentResult(
                agent=self.name,
                success=True,
                output=result_text,
                messages=self._messages,
            )

        elif response_type == "single_agent":
            agent_name = routing.get("primary_agent", "coding")
            return await self._run_single_agent(agent_name, context)

        elif response_type == "multi_agent":
            agents = routing.get("agents_to_use", [])
            return await self._run_multi_agent(agents, context)

        else:
            return AgentResult(
                agent=self.name,
                success=True,
                output=routing.get("direct_response", "How can I help you?"),
                messages=self._messages,
            )

    async def stream_response(self, context: AgentContext) -> AsyncGenerator[str, None]:
        """Stream the coordinator response directly."""
        memory_ctx = ""
        if self.memory_manager:
            memory_ctx = await self.memory_manager.build_context(context.user_query)

        messages = [{"role": m["role"], "content": m["content"]} for m in context.messages[-8:]]
        messages.append({"role": "user", "content": context.user_query})

        system = JAY_DIRECT_SYSTEM
        if memory_ctx:
            system += f"\n\n{memory_ctx}"

        async for chunk in self._stream_llm(messages, system=system, temperature=0.7):
            yield chunk

        # Store conversation in memory asynchronously
        if self.memory_manager:
            try:
                await self.memory_manager.extract_and_store_from_conversation(
                    messages, self.provider_manager
                )
            except Exception:
                pass

    def _parse_routing(self, raw: str) -> Dict:
        """Parse routing JSON from LLM response."""
        try:
            # Extract JSON
            import re
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        # Fallback: direct response
        return {"response_type": "direct", "direct_response": raw}

    async def _run_single_agent(self, agent_name: str, context: AgentContext) -> AgentResult:
        agent = self.agent_registry.get(agent_name)
        if not agent:
            return AgentResult(
                agent=self.name,
                success=False,
                output=f"Agent '{agent_name}' not available.",
                error=f"Agent {agent_name} not found",
            )
        self._emit(f"Delegating to {agent_name}", "action")
        await event_bus.publish(Events.AGENT_STARTED, {"agent": agent_name})
        return await agent.run(context)

    async def _run_multi_agent(self, agent_names: List[str], context: AgentContext) -> AgentResult:
        """Run agents sequentially, passing results as context."""
        all_messages = list(self._messages)
        accumulated_output = {}
        final_output = ""

        for agent_name in agent_names:
            agent = self.agent_registry.get(agent_name)
            if not agent:
                continue

            # Enrich context with previous results
            enhanced_context = AgentContext(
                conversation_id=context.conversation_id,
                user_query=context.user_query,
                messages=context.messages,
                memory_context=context.memory_context,
                metadata={**context.metadata, "previous_results": accumulated_output},
            )

            self._emit(f"Running agent: {agent_name}", "action")
            await event_bus.publish(Events.AGENT_STARTED, {"agent": agent_name})

            result = await agent.run(enhanced_context)
            accumulated_output[agent_name] = result.output
            all_messages.extend(result.messages)
            final_output = result.output  # Last agent's output is final

            await event_bus.publish(Events.AGENT_COMPLETED, {"agent": agent_name})

        self.status = "complete"
        return AgentResult(
            agent=self.name,
            success=True,
            output=final_output,
            messages=all_messages,
        )


# J.A.Y. direct conversation system prompt
JAY_DIRECT_SYSTEM = """You are J.A.Y. (Just Assists You) — a personal AI operating system.

PERSONALITY:
- Calm, confident, intelligent, professionally witty
- Think and act like a senior engineer + trusted advisor
- Never blindly agree — challenge assumptions, identify risks, suggest alternatives
- Be cooperative, not obedient. Trust is earned through accuracy

CAPABILITIES you can discuss:
- Software engineering (build, debug, architect, review code)
- Trading & market analysis (NSE, BSE, Forex, Crypto, US stocks)
- Internet research and fact-finding
- Desktop control (open apps, manage files, run commands)
- Creative work (images, logos, UI concepts)
- Productivity (tasks, reminders, projects, notes)
- Long-term memory (you remember conversations and preferences)

RULES:
1. Be direct and precise
2. Admit uncertainty honestly ("I'm not certain about X, let me verify")
3. Point out flaws in plans before executing them
4. Ask clarifying questions when intent is ambiguous
5. Explain risks alongside recommendations
6. Never guarantee profits in trading
7. Never execute dangerous actions without confirmation
8. Format code and technical content clearly

You are running locally on the user's machine. You have access to tools and agents."""
