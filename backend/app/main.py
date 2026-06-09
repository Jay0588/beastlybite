"""
J.A.Y. Main Application — FastAPI entry point
"""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("=" * 60)
    logger.info("   J.A.Y. — Just Assists You  v0.1.0")
    logger.info("=" * 60)

    # Create directories
    from app.core.config import settings
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    os.makedirs(settings.LOGS_DIR, exist_ok=True)
    os.makedirs(settings.PROJECTS_DIR, exist_ok=True)
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(settings.AUDIT_LOG_PATH), exist_ok=True)

    # Initialize database
    from app.core.database import init_db
    await init_db()
    logger.info("✓ Database initialized")

    # Initialize providers
    from app.providers.manager import provider_manager
    available = await provider_manager.list_available()
    active = [p["name"] for p in available if p["available"]]
    logger.info(f"✓ AI Providers available: {active or ['none — configure in .env']}")

    # Initialize tool registry
    from app.tools.registry import create_tool_registry
    tool_registry = create_tool_registry()
    logger.info(f"✓ Tools registered: {len(tool_registry._tools)}")

    # Initialize memory
    from app.memory.manager import memory_manager
    logger.info("✓ Memory system initialized")

    # Initialize agents
    from app.agents.registry import AgentRegistry
    import app.agents.registry as agent_reg_module
    agent_registry = AgentRegistry(
        provider_manager=provider_manager,
        tool_registry=tool_registry,
        memory_manager=memory_manager,
    )
    agent_registry.initialize()
    agent_reg_module.agent_registry = agent_registry
    logger.info(f"✓ Agents initialized: {[a['name'] for a in agent_registry.list_agents()]}")

    logger.info("✓ J.A.Y. is online and ready")
    logger.info("=" * 60)

    yield

    logger.info("J.A.Y. shutting down...")


# Create FastAPI app
app = FastAPI(
    title="J.A.Y. API",
    description="Just Assists You — Personal AI Operating System",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow Tauri/Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:1420",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from app.api.chat import router as chat_router
from app.api.voice import router as voice_router
from app.api.trading import router as trading_router
from app.api.tools import router as tools_router
from app.api.memory import router as memory_router
from app.api.system import router as system_router
from app.api.projects import router as projects_router
from app.api.websocket import router as ws_router
from app.api.vision import router as vision_router

app.include_router(chat_router)
app.include_router(voice_router)
app.include_router(trading_router)
app.include_router(tools_router)
app.include_router(memory_router)
app.include_router(system_router)
app.include_router(projects_router)
app.include_router(ws_router)
app.include_router(vision_router)


@app.get("/")
async def root():
    return {
        "name": "J.A.Y.",
        "description": "Just Assists You — Personal AI Operating System",
        "version": "0.1.0",
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "jay"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
