"""
J.A.Y. Tools API — Execute tools directly
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tools", tags=["tools"])


class ToolExecuteRequest(BaseModel):
    tool: str
    params: Dict[str, Any] = {}
    approved: bool = False


@router.get("/")
async def list_tools():
    """List all available tools."""
    from app.tools.registry import create_tool_registry
    from app.core.security import ToolPermission
    registry = create_tool_registry()
    tools = registry.list_tools()
    for t in tools:
        t["permission_level"] = ToolPermission.get_level(t["name"]).value
    return {"tools": tools, "count": len(tools)}


@router.post("/execute")
async def execute_tool(request: ToolExecuteRequest):
    """Execute a tool by name."""
    from app.tools.registry import create_tool_registry
    from app.core.security import ToolPermission, PermissionLevel

    registry = create_tool_registry()
    tool = registry.get_tool(request.tool)

    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{request.tool}' not found")

    level = ToolPermission.get_level(request.tool)
    if level in [PermissionLevel.DANGEROUS, PermissionLevel.CRITICAL] and not request.approved:
        return {
            "success": False,
            "requires_approval": True,
            "tool": request.tool,
            "level": level.value,
            "message": f"Tool '{request.tool}' is {level.value} and requires explicit approval",
        }

    result = await tool.safe_execute(request.params, approved=request.approved)
    return result


@router.get("/pending-approvals")
async def get_pending_approvals():
    """Get all pending approval requests."""
    from app.core.security import approval_manager
    return {"pending": approval_manager.get_pending()}


@router.post("/approve/{action_id}")
async def approve_action(action_id: str):
    """Approve a pending action."""
    from app.core.security import approval_manager
    success = approval_manager.approve(action_id)
    return {"success": success}


@router.post("/deny/{action_id}")
async def deny_action(action_id: str):
    """Deny a pending action."""
    from app.core.security import approval_manager
    success = approval_manager.deny(action_id)
    return {"success": success}


@router.get("/audit-log")
async def get_audit_log(limit: int = 50):
    """Get audit log entries."""
    import json
    from app.core.config import settings
    try:
        with open(settings.AUDIT_LOG_PATH, "r") as f:
            lines = f.readlines()
        entries = []
        for line in lines[-limit:]:
            try:
                entries.append(json.loads(line.strip()))
            except Exception:
                pass
        return {"entries": list(reversed(entries)), "count": len(entries)}
    except FileNotFoundError:
        return {"entries": [], "count": 0}
