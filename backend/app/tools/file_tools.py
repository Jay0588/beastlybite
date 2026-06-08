"""
J.A.Y. File System Tools — Create, read, write, move, delete files
"""
import os
import shutil
import glob
import json
import logging
from typing import Dict, Any, List
from pathlib import Path
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read the contents of a file"

    async def execute(self, params: Dict[str, Any]) -> Dict:
        path = params.get("path", "")
        if not path:
            return {"success": False, "error": "No path provided"}
        try:
            p = Path(os.path.expanduser(path))
            if not p.exists():
                return {"success": False, "error": f"File not found: {path}"}
            if not p.is_file():
                return {"success": False, "error": f"Not a file: {path}"}

            content = p.read_text(encoding="utf-8", errors="replace")
            # Limit output
            if len(content) > 50000:
                content = content[:50000] + "\n\n[...truncated at 50,000 chars]"
            return {"success": True, "output": content, "path": str(p), "size": p.stat().st_size}
        except Exception as e:
            return {"success": False, "error": str(e)}


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write content to a file (creates or overwrites)"
    requires_approval = False

    async def execute(self, params: Dict[str, Any]) -> Dict:
        path = params.get("path", "")
        content = params.get("content", "")
        if not path:
            return {"success": False, "error": "No path provided"}
        try:
            p = Path(os.path.expanduser(path))
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"success": True, "output": f"Written {len(content)} chars to {path}", "path": str(p)}
        except Exception as e:
            return {"success": False, "error": str(e)}


class CreateFolderTool(BaseTool):
    name = "create_folder"
    description = "Create a new folder/directory"

    async def execute(self, params: Dict[str, Any]) -> Dict:
        path = params.get("path", "")
        if not path:
            return {"success": False, "error": "No path provided"}
        try:
            p = Path(os.path.expanduser(path))
            p.mkdir(parents=True, exist_ok=True)
            return {"success": True, "output": f"Created folder: {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class ListDirectoryTool(BaseTool):
    name = "list_directory"
    description = "List files and folders in a directory"

    async def execute(self, params: Dict[str, Any]) -> Dict:
        path = params.get("path", os.path.expanduser("~"))
        try:
            p = Path(os.path.expanduser(path))
            if not p.exists():
                return {"success": False, "error": f"Directory not found: {path}"}
            
            items = []
            for item in sorted(p.iterdir()):
                try:
                    stat = item.stat()
                    items.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat.st_size if item.is_file() else None,
                        "modified": stat.st_mtime,
                    })
                except PermissionError:
                    items.append({"name": item.name, "type": "unknown", "error": "permission denied"})
            
            return {"success": True, "output": items, "path": str(p), "count": len(items)}
        except Exception as e:
            return {"success": False, "error": str(e)}


class SearchFilesTool(BaseTool):
    name = "search_files"
    description = "Search for files by name pattern or content"

    async def execute(self, params: Dict[str, Any]) -> Dict:
        pattern = params.get("pattern", "*")
        search_dir = params.get("directory", os.path.expanduser("~"))
        content_search = params.get("content", None)
        max_results = params.get("max_results", 20)

        try:
            base = Path(os.path.expanduser(search_dir))
            matches = []

            for p in base.rglob(pattern):
                if len(matches) >= max_results:
                    break
                if p.is_file():
                    match_info = {
                        "path": str(p),
                        "name": p.name,
                        "size": p.stat().st_size,
                    }
                    if content_search:
                        try:
                            text = p.read_text(errors="replace")
                            if content_search.lower() in text.lower():
                                matches.append(match_info)
                        except Exception:
                            pass
                    else:
                        matches.append(match_info)

            return {"success": True, "output": matches, "count": len(matches)}
        except Exception as e:
            return {"success": False, "error": str(e)}


class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = "Delete a file (requires confirmation)"
    requires_approval = True
    is_dangerous = True

    async def execute(self, params: Dict[str, Any]) -> Dict:
        path = params.get("path", "")
        if not path:
            return {"success": False, "error": "No path provided"}
        try:
            p = Path(os.path.expanduser(path))
            if not p.exists():
                return {"success": False, "error": f"File not found: {path}"}
            p.unlink()
            return {"success": True, "output": f"Deleted: {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class MoveFileTool(BaseTool):
    name = "move_file"
    description = "Move or rename a file or folder"

    async def execute(self, params: Dict[str, Any]) -> Dict:
        src = params.get("source", "")
        dst = params.get("destination", "")
        if not src or not dst:
            return {"success": False, "error": "Source and destination required"}
        try:
            s = Path(os.path.expanduser(src))
            d = Path(os.path.expanduser(dst))
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(s), str(d))
            return {"success": True, "output": f"Moved {src} → {dst}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class ScanProjectTool(BaseTool):
    name = "scan_project"
    description = "Scan a project directory to understand its architecture, stack, and structure"

    async def execute(self, params: Dict[str, Any]) -> Dict:
        path = params.get("path", os.getcwd())
        try:
            p = Path(os.path.expanduser(path))
            info = {
                "path": str(p),
                "files_by_type": {},
                "detected_stack": [],
                "key_files": [],
                "structure": [],
            }

            # Count files by type
            type_counts: Dict[str, int] = {}
            all_files = []
            for f in p.rglob("*"):
                if f.is_file() and ".git" not in str(f) and "node_modules" not in str(f) and "__pycache__" not in str(f):
                    ext = f.suffix.lower()
                    type_counts[ext] = type_counts.get(ext, 0) + 1
                    all_files.append(str(f.relative_to(p)))

            info["files_by_type"] = dict(sorted(type_counts.items(), key=lambda x: -x[1])[:20])

            # Detect stack
            indicators = {
                "Next.js": (p / "next.config.js").exists() or (p / "next.config.ts").exists(),
                "React": (p / "package.json").exists() and "react" in (p / "package.json").read_text(errors="replace") if (p / "package.json").exists() else False,
                "TypeScript": ".ts" in type_counts or ".tsx" in type_counts,
                "Python": ".py" in type_counts,
                "FastAPI": any("fastapi" in str(f) for f in p.rglob("requirements*.txt")),
                "Docker": (p / "Dockerfile").exists() or (p / "docker-compose.yml").exists(),
                "Git": (p / ".git").exists(),
                "Tauri": (p / "src-tauri").exists(),
                "PostgreSQL": any("postgres" in f.lower() for f in all_files),
            }
            info["detected_stack"] = [k for k, v in indicators.items() if v]

            # Key files
            key_names = ["package.json", "requirements.txt", "Dockerfile", "docker-compose.yml",
                        "README.md", ".env.example", "pyproject.toml", "Cargo.toml"]
            info["key_files"] = [str(p / f) for f in key_names if (p / f).exists()]

            # Top-level structure
            info["structure"] = [item.name for item in sorted(p.iterdir())
                                 if item.name not in [".git", "node_modules", "__pycache__", ".next"]]

            return {"success": True, "output": info}
        except Exception as e:
            return {"success": False, "error": str(e)}
