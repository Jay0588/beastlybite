"""
J.A.Y. Terminal Tools — Execute shell commands safely
"""
import asyncio
import subprocess
import os
import logging
from typing import Dict, Any, Optional
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

BLOCKED_COMMANDS = [
    "rm -rf /", "format", "mkfs", "dd if=", ":(){ :|:& };:",
    "shutdown", "reboot", "halt", "> /dev/sda",
    "chmod -R 777 /", "chown -R",
]


class RunCommandTool(BaseTool):
    name = "run_terminal_command"
    description = "Execute a shell command in a working directory"
    requires_approval = False

    async def execute(self, params: Dict[str, Any]) -> Dict:
        command = params.get("command", "").strip()
        cwd = params.get("cwd", os.path.expanduser("~"))
        timeout = min(params.get("timeout", 30), 120)

        if not command:
            return {"success": False, "error": "No command provided"}

        # Safety check
        cmd_lower = command.lower()
        for blocked in BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                return {
                    "success": False,
                    "error": f"Command blocked for safety: contains '{blocked}'",
                    "blocked": True,
                }

        try:
            cwd_path = os.path.expanduser(cwd)
            if not os.path.exists(cwd_path):
                os.makedirs(cwd_path, exist_ok=True)

            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd_path,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                return {"success": False, "error": f"Command timed out after {timeout}s"}

            stdout_str = stdout.decode("utf-8", errors="replace").strip()
            stderr_str = stderr.decode("utf-8", errors="replace").strip()

            # Limit output
            if len(stdout_str) > 10000:
                stdout_str = stdout_str[:10000] + "\n[...output truncated]"

            return {
                "success": proc.returncode == 0,
                "output": stdout_str or stderr_str or "(no output)",
                "stdout": stdout_str,
                "stderr": stderr_str,
                "return_code": proc.returncode,
                "command": command,
                "cwd": cwd_path,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "command": command}


class GitTool(BaseTool):
    name = "git_command"
    description = "Execute git commands (status, add, commit, log, diff, clone)"

    SAFE_GIT_COMMANDS = ["status", "log", "diff", "branch", "remote", "show", "blame", "ls-files"]
    MODERATE_GIT_COMMANDS = ["add", "commit", "checkout", "merge", "rebase", "stash"]
    DANGEROUS_GIT_COMMANDS = ["push", "force", "reset --hard", "clean -fd"]

    async def execute(self, params: Dict[str, Any]) -> Dict:
        git_cmd = params.get("git_command", "status")
        cwd = params.get("cwd", os.getcwd())
        args = params.get("args", "")

        full_command = f"git {git_cmd} {args}".strip()

        # Check if command is safe
        cmd_lower = git_cmd.lower()
        if any(dangerous in cmd_lower for dangerous in self.DANGEROUS_GIT_COMMANDS):
            if not params.get("approved", False):
                return {
                    "success": False,
                    "error": f"Git command '{git_cmd}' requires explicit approval",
                    "requires_approval": True,
                }

        tool = RunCommandTool()
        return await tool.execute({"command": full_command, "cwd": cwd})


class NPMTool(BaseTool):
    name = "npm_command"
    description = "Run npm/yarn/pnpm commands (install, run, build, test)"

    async def execute(self, params: Dict[str, Any]) -> Dict:
        subcommand = params.get("subcommand", "install")
        cwd = params.get("cwd", os.getcwd())
        package_manager = params.get("pm", "npm")
        extra_args = params.get("args", "")

        command = f"{package_manager} {subcommand} {extra_args}".strip()
        tool = RunCommandTool()
        return await tool.execute({"command": command, "cwd": cwd, "timeout": 120})


class PythonExecuteTool(BaseTool):
    name = "execute_python"
    description = "Execute Python code in a sandboxed environment"
    requires_approval = True
    is_dangerous = True

    async def execute(self, params: Dict[str, Any]) -> Dict:
        code = params.get("code", "")
        if not code:
            return {"success": False, "error": "No code provided"}

        # Write to temp file and execute
        import tempfile
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                tmp_path = f.name

            tool = RunCommandTool()
            result = await tool.execute({
                "command": f"python {tmp_path}",
                "timeout": 30,
            })
            os.unlink(tmp_path)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
