"""
J.A.Y. Tool Registry — Registers all tools
"""
from app.tools.base import ToolRegistry
from app.tools.desktop import OpenApplicationTool, ListRunningAppsTool, GetSystemInfoTool, TakeScreenshotTool
from app.tools.file_tools import (
    ReadFileTool, WriteFileTool, CreateFolderTool, ListDirectoryTool,
    SearchFilesTool, DeleteFileTool, MoveFileTool, ScanProjectTool
)
from app.tools.terminal import RunCommandTool, GitTool, NPMTool, PythonExecuteTool
from app.tools.web_tools import WebSearchTool, FetchURLTool, NewsFeedTool
import logging

logger = logging.getLogger(__name__)


def create_tool_registry() -> ToolRegistry:
    """Create and populate the global tool registry."""
    registry = ToolRegistry()

    # Desktop tools
    registry.register(OpenApplicationTool())
    registry.register(ListRunningAppsTool())
    registry.register(GetSystemInfoTool())
    registry.register(TakeScreenshotTool())

    # File tools
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(CreateFolderTool())
    registry.register(ListDirectoryTool())
    registry.register(SearchFilesTool())
    registry.register(DeleteFileTool())
    registry.register(MoveFileTool())
    registry.register(ScanProjectTool())

    # Terminal tools
    registry.register(RunCommandTool())
    registry.register(GitTool())
    registry.register(NPMTool())
    registry.register(PythonExecuteTool())

    # Web tools
    registry.register(WebSearchTool())
    registry.register(FetchURLTool())
    registry.register(NewsFeedTool())

    logger.info(f"Tool registry created with {len(registry._tools)} tools")
    return registry
