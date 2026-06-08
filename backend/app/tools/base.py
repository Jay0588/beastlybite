"""
J.A.Y. Tool Base — All tools inherit from this
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class ToolInput(BaseModel):
    params: Dict[str, Any] = {}


class ToolOutput(BaseModel):
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict = {}
    execution_time: float = 0.0


class BaseTool(ABC):
    name: str = "base_tool"
    description: str = "Base tool"
    parameters_schema: Dict = {}
    requires_approval: bool = False
    is_dangerous: bool = False

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict:
        """Execute the tool with given parameters."""
        pass

    async def safe_execute(self, params: Dict[str, Any], approved: bool = True) -> Dict:
        """Execute with safety checks."""
        import time
        start = time.time()
        try:
            from app.core.security import ToolPermission, PermissionLevel, audit_logger
            level = ToolPermission.get_level(self.name)
            if level in [PermissionLevel.DANGEROUS, PermissionLevel.CRITICAL] and not approved:
                return {
                    "success": False,
                    "output": None,
                    "error": f"Tool '{self.name}' requires explicit approval",
                    "requires_approval": True,
                }

            result = await self.execute(params)
            elapsed = time.time() - start
            audit_logger.log(
                action="tool_execute",
                tool=self.name,
                params=params,
                result=result,
                approved=approved,
            )
            if isinstance(result, dict):
                result["execution_time"] = elapsed
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"Tool {self.name} error: {e}")
            return {"success": False, "output": None, "error": str(e), "execution_time": elapsed}


class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "requires_approval": t.requires_approval,
                "is_dangerous": t.is_dangerous,
                "parameters": t.parameters_schema,
            }
            for t in self._tools.values()
        ]

    def get_openai_tools_schema(self) -> List[Dict]:
        """Convert tools to OpenAI function calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters_schema or {"type": "object", "properties": {}},
                },
            }
            for t in self._tools.values()
        ]
