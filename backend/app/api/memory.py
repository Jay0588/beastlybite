"""
J.A.Y. Memory API — Store, retrieve, and manage long-term memory
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memory", tags=["memory"])


class MemoryStoreRequest(BaseModel):
    content: str
    category: str = "fact"
    namespace: str = "general"
    importance: float = 0.5
    tags: List[str] = []


class MemorySearchRequest(BaseModel):
    query: str
    namespace: str = "general"
    category: Optional[str] = None
    n: int = 10


@router.post("/store")
async def store_memory(request: MemoryStoreRequest):
    """Store a memory entry."""
    from app.memory.manager import memory_manager
    doc_id = await memory_manager.remember(
        content=request.content,
        category=request.category,
        namespace=request.namespace,
        importance=request.importance,
    )
    return {"success": True, "id": doc_id}


@router.post("/search")
async def search_memory(request: MemorySearchRequest):
    """Search memories semantically."""
    from app.memory.manager import memory_manager
    results = await memory_manager.recall(
        query=request.query,
        namespace=request.namespace,
        category=request.category,
        n=request.n,
    )
    return {"results": results, "count": len(results)}


@router.get("/all")
async def get_all_memories(namespace: str = "general", category: Optional[str] = None):
    """Get all memories."""
    from app.memory.store import memory_store
    memories = await memory_store.get_all(namespace=namespace, category=category)
    return {"memories": memories, "count": len(memories)}


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str, namespace: str = "general"):
    """Delete a memory entry."""
    from app.memory.store import memory_store
    await memory_store.delete(memory_id, namespace=namespace)
    return {"success": True}


@router.get("/stats")
async def memory_stats():
    """Get memory statistics."""
    from app.memory.store import memory_store
    stats = {}
    for ns in ["general", "conversations", "projects", "trading", "research", "code"]:
        count = await memory_store.count(ns)
        stats[ns] = count
    return {"namespaces": stats, "total": sum(stats.values())}


@router.get("/profile")
async def get_user_profile():
    """Get user profile derived from memories."""
    from app.memory.manager import memory_manager
    profile = await memory_manager.get_user_profile()
    return {"profile": profile}
