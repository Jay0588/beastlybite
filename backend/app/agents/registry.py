"""
J.A.Y. Agent Registry — Creates and manages all agents
"""
from typing import Dict, Optional
import logging
from app.agents.base import BaseAgent
from app.agents.coordinator import CoordinatorAgent
from app.agents.planner import PlannerAgent
from app.agents.research_agent import ResearchAgent
from app.agents.coding_agent import CodingAgent
from app.agents.market_agent import MarketAgent
from app.agents.creative_agent import CreativeAgent
from app.agents.memory_agent import MemoryAgent
from app.agents.reviewer import ReviewerAgent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for all J.A.Y. agents.
    Provides dependency injection and agent lifecycle management.
    """

    def __init__(self, provider_manager=None, tool_registry=None, memory_manager=None):
        self.provider_manager = provider_manager
        self.tool_registry = tool_registry
        self.memory_manager = memory_manager
        self._agents: Dict[str, BaseAgent] = {}
        self._coordinator: Optional[CoordinatorAgent] = None

    def initialize(self):
        """Initialize all agents with shared dependencies."""
        kwargs = dict(
            provider_manager=self.provider_manager,
            tool_registry=self.tool_registry,
            memory_manager=self.memory_manager,
        )

        self._agents = {
            "planner": PlannerAgent(**kwargs),
            "research": ResearchAgent(**kwargs),
            "coding": CodingAgent(**kwargs),
            "market": MarketAgent(**kwargs),
            "creative": CreativeAgent(**kwargs),
            "memory": MemoryAgent(**kwargs),
            "reviewer": ReviewerAgent(**kwargs),
        }

        # Coordinator gets the full agent registry
        self._coordinator = CoordinatorAgent(
            **kwargs,
            agent_registry=self._agents,
        )
        self._agents["coordinator"] = self._coordinator

        logger.info(f"Agent registry initialized: {list(self._agents.keys())}")

    def get(self, name: str) -> Optional[BaseAgent]:
        return self._agents.get(name)

    @property
    def coordinator(self) -> CoordinatorAgent:
        return self._coordinator

    def list_agents(self) -> list:
        return [
            {
                "name": a.name,
                "description": a.description,
                "capabilities": a.capabilities,
                "status": a.status,
            }
            for a in self._agents.values()
        ]


# Will be initialized in main.py
agent_registry: Optional[AgentRegistry] = None
