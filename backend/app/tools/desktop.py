"""
J.A.Y. Desktop Control Tools — Open apps, manage windows, control computer
"""
import subprocess
import platform
import os
import psutil
import logging
from typing import Dict, Any, Optional, List
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)
OS = platform.system()  # Windows, Darwin, Linux


class OpenApplicationTool(BaseTool):
    name = "open_application"
    description = "Open an application by name (e.g., VS Code, Chrome, Spotify, Steam)"
    requires_approval = False

    APP_MAP_WINDOWS = {
        "vscode": "code",
        "vs code": "code",
        "visual studio code": "code",
        "chrome": "chrome",
        "google chrome": "chrome",
        "firefox": "firefox",
        "spotify": "spotify",
        "steam": "steam",
        "notepad": "notepad",
        "calculator": "calc",
        "explorer": "explorer",
        "terminal": "wt",
        "cmd": "cmd",
        "powershell": "powershell",
        "word": "winword",
        "excel": "excel",
        "outlook": "outlook",
    }

    APP_MAP_MAC = {
        "vscode": "Visual Studio Code",
        "vs code": "Visual Studio Code",
        "chrome": "Google Chrome",
        "firefox": "Firefox",
        "spotify": "Spotify",
        "steam": "Steam",
        "terminal": "Terminal",
    }

    async def execute(self, params: Dict[str, Any]) -> Dict:
        app_name = params.get("app", params.get("name", "")).lower().strip()
        if not app_name:
            return {"success": False, "output": None, "error": "No app name provided"}

        try:
            if OS == "Windows":
                cmd = self.APP_MAP_WINDOWS.get(app_name, app_name)
                subprocess.Popen([cmd], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            elif OS == "Darwin":
                app = self.APP_MAP_MAC.get(app_name, app_name.title())
                subprocess.Popen(["open", "-a", app])
            else:  # Linux
                subprocess.Popen([app_name], start_new_session=True)

            return {"success": True, "output": f"Opening {app_name}...", "app": app_name}
        except FileNotFoundError:
            return {"success": False, "output": None, "error": f"Application '{app_name}' not found"}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}


class ListRunningAppsTool(BaseTool):
    name = "list_running_apps"
    description = "List all currently running applications and processes"

    async def execute(self, params: Dict[str, Any]) -> Dict:
        try:
            processes = []
            for proc in psutil.process_iter(["pid", "name", "status", "memory_info"]):
                try:
                    info = proc.info
                    processes.append({
                        "pid": info["pid"],
                        "name": info["name"],
                        "status": info["status"],
                        "memory_mb": round(info["memory_info"].rss / 1024 / 1024, 1) if info.get("memory_info") else 0,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            # Sort by memory usage
            processes.sort(key=lambda x: x["memory_mb"], reverse=True)
            return {"success": True, "output": processes[:50]}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}


class GetSystemInfoTool(BaseTool):
    name = "get_system_info"
    description = "Get system information: CPU, RAM, disk usage, OS details"

    async def execute(self, params: Dict[str, Any]) -> Dict:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            info = {
                "os": f"{platform.system()} {platform.release()}",
                "cpu_percent": cpu_percent,
                "cpu_cores": psutil.cpu_count(),
                "ram_total_gb": round(mem.total / 1024**3, 2),
                "ram_used_gb": round(mem.used / 1024**3, 2),
                "ram_percent": mem.percent,
                "disk_total_gb": round(disk.total / 1024**3, 2),
                "disk_used_gb": round(disk.used / 1024**3, 2),
                "disk_percent": round(disk.percent, 1),
                "python_version": platform.python_version(),
            }
            return {"success": True, "output": info}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}


class TakeScreenshotTool(BaseTool):
    name = "take_screenshot"
    description = "Take a screenshot of the current screen"

    async def execute(self, params: Dict[str, Any]) -> Dict:
        try:
            import pyautogui
            import io
            import base64
            screenshot = pyautogui.screenshot()
            buf = io.BytesIO()
            screenshot.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            return {
                "success": True,
                "output": "Screenshot captured",
                "image_base64": b64,
                "width": screenshot.width,
                "height": screenshot.height,
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}
