"""
J.A.Y. Projects API — Project management, tasks, notes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    project_type: str = "general"
    path: Optional[str] = None
    tech_stack: List[str] = []


class TaskCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    project_id: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[str] = None
    tags: List[str] = []


@router.get("/")
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all projects."""
    from sqlalchemy import select
    from app.models.project import Project
    result = await db.execute(select(Project).order_by(Project.updated_at.desc()))
    projects = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "type": p.project_type,
            "status": p.status,
            "path": p.path,
            "tech_stack": p.tech_stack,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in projects
    ]


@router.post("/")
async def create_project(request: ProjectCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a new project."""
    from app.models.project import Project
    import uuid
    project = Project(
        id=str(uuid.uuid4()),
        name=request.name,
        description=request.description,
        project_type=request.project_type,
        path=request.path,
        tech_stack=request.tech_stack,
    )
    db.add(project)
    await db.commit()
    return {"success": True, "id": project.id, "name": project.name}


@router.post("/scan")
async def scan_project(path: str):
    """Scan a project directory."""
    from app.tools.file_tools import ScanProjectTool
    tool = ScanProjectTool()
    return await tool.execute({"path": path})


# Tasks
@router.get("/tasks")
async def list_tasks(project_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """List tasks."""
    from sqlalchemy import select
    from app.models.project import Task
    query = select(Task)
    if project_id:
        query = query.where(Task.project_id == project_id)
    query = query.order_by(Task.created_at.desc())
    result = await db.execute(query)
    tasks = result.scalars().all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "priority": t.priority,
            "project_id": t.project_id,
            "tags": t.tags,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tasks
    ]


@router.post("/tasks")
async def create_task(request: TaskCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a task."""
    from app.models.project import Task
    import uuid
    task = Task(
        id=str(uuid.uuid4()),
        title=request.title,
        description=request.description,
        project_id=request.project_id,
        priority=request.priority,
        tags=request.tags,
    )
    db.add(task)
    await db.commit()
    return {"success": True, "id": task.id}


@router.put("/tasks/{task_id}/status")
async def update_task_status(task_id: str, status: str, db: AsyncSession = Depends(get_db)):
    """Update task status."""
    from sqlalchemy import update
    from app.models.project import Task
    from datetime import datetime
    values = {"status": status}
    if status == "done":
        values["completed_at"] = datetime.utcnow()
    await db.execute(update(Task).where(Task.id == task_id).values(**values))
    await db.commit()
    return {"success": True}
