"""
J.A.Y. Security & Permissions Layer
"""
from enum import Enum
from typing import Dict, Optional, Callable, Any
from datetime import datetime
import json
import logging
import os
from app.core.config import settings

logger = logging.getLogger(__name__)


class PermissionLevel(str, Enum):
    SAFE = "safe"           # Auto-execute, no confirmation needed
    MODERATE = "moderate"   # Ask once, remember decision
    DANGEROUS = "dangerous" # Always require explicit confirmation
    CRITICAL = "critical"   # Require typed confirmation


class ToolPermission:
    REGISTRY: Dict[str, PermissionLevel] = {
        # Safe tools
        "web_search": PermissionLevel.SAFE,
        "read_file": PermissionLevel.SAFE,
        "list_directory": PermissionLevel.SAFE,
        "get_market_data": PermissionLevel.SAFE,
        "run_analysis": PermissionLevel.SAFE,
        "get_system_info": PermissionLevel.SAFE,
        "open_application": PermissionLevel.MODERATE,
        "create_file": PermissionLevel.MODERATE,
        "create_folder": PermissionLevel.MODERATE,
        "run_terminal_command": PermissionLevel.MODERATE,
        "browser_navigate": PermissionLevel.MODERATE,

        # Dangerous
        "delete_file": PermissionLevel.DANGEROUS,
        "write_file": PermissionLevel.MODERATE,
        "move_file": PermissionLevel.MODERATE,
        "rename_file": PermissionLevel.MODERATE,
        "execute_code": PermissionLevel.DANGEROUS,
        "git_push": PermissionLevel.DANGEROUS,
        "git_commit": PermissionLevel.MODERATE,
        "install_package": PermissionLevel.DANGEROUS,

        # Critical
        "format_drive": PermissionLevel.CRITICAL,
        "delete_folder": PermissionLevel.DANGEROUS,
        "system_shutdown": PermissionLevel.CRITICAL,
        "registry_modify": PermissionLevel.CRITICAL,
    }

    @classmethod
    def get_level(cls, tool_name: str) -> PermissionLevel:
        return cls.REGISTRY.get(tool_name, PermissionLevel.MODERATE)

    @classmethod
    def is_auto_executable(cls, tool_name: str) -> bool:
        return cls.get_level(tool_name) == PermissionLevel.SAFE


class ApprovalManager:
    """Manages pending approvals for dangerous actions."""

    def __init__(self):
        self.pending: Dict[str, Dict] = {}

    def create_approval_request(
        self,
        action_id: str,
        tool_name: str,
        description: str,
        params: Dict,
        risk_explanation: str,
    ) -> Dict:
        request = {
            "id": action_id,
            "tool": tool_name,
            "description": description,
            "params": params,
            "risk": risk_explanation,
            "level": ToolPermission.get_level(tool_name),
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending",
        }
        self.pending[action_id] = request
        return request

    def approve(self, action_id: str) -> bool:
        if action_id in self.pending:
            self.pending[action_id]["status"] = "approved"
            return True
        return False

    def deny(self, action_id: str) -> bool:
        if action_id in self.pending:
            self.pending[action_id]["status"] = "denied"
            return True
        return False

    def get_pending(self) -> list:
        return [r for r in self.pending.values() if r["status"] == "pending"]


class AuditLogger:
    """Logs all tool executions and actions."""

    def __init__(self, log_path: str = settings.AUDIT_LOG_PATH):
        os.makedirs(os.path.dirname(log_path) if os.path.dirname(log_path) else ".", exist_ok=True)
        self.log_path = log_path

    def log(
        self,
        action: str,
        tool: str,
        params: Dict,
        result: Any,
        user: str = "user",
        approved: bool = True,
    ):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user": user,
            "action": action,
            "tool": tool,
            "params": params,
            "result_summary": str(result)[:200],
            "approved": approved,
        }
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Audit log write failed: {e}")


approval_manager = ApprovalManager()
audit_logger = AuditLogger()
