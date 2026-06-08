"""
J.A.Y. Chat API — Main conversation endpoint with streaming
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict
import json
import uuid
import logging
from datetime import datetime

from app.core.database import get_db
from app.core.events import event_bus, Events

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    context_type: str = "general"
    stream: bool = True
    provider: Optional[str] = None
    model: Optional[str] = None


class ChatResponse(BaseModel):
    message_id: str
    conversation_id: str
    content: str
    model_used: Optional[str] = None
    provider_used: Optional[str] = None
    tools_used: List[str] = []


@router.post("/message")
async def send_message(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Send a message to J.A.Y. — supports streaming."""
    from app.agents.registry import agent_registry
    from app.agents.base import AgentContext
    from app.models.conversation import Conversation, Message

    if not agent_registry or not agent_registry.coordinator:
        raise HTTPException(status_code=503, detail="Agent system not initialized")

    # Get or create conversation
    conv_id = request.conversation_id or str(uuid.uuid4())

    # Build agent context from history
    from sqlalchemy import select
    history = []
    if request.conversation_id:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at.desc())
            .limit(10)
        )
        msgs = result.scalars().all()
        history = [{"role": m.role, "content": m.content} for m in reversed(msgs)]

    context = AgentContext(
        conversation_id=conv_id,
        user_query=request.message,
        messages=history,
    )

    # Save user message
    user_msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        role="user",
        content=request.message,
        created_at=datetime.utcnow(),
    )
    db.add(user_msg)

    if request.stream:
        async def generate():
            full_content = ""
            try:
                # Try streaming from coordinator
                coordinator = agent_registry.coordinator
                async for chunk in coordinator.stream_response(context):
                    full_content += chunk
                    data = json.dumps({"chunk": chunk, "conversation_id": conv_id})
                    yield f"data: {data}\n\n"

                # Save assistant message
                async with db.begin():
                    assistant_msg = Message(
                        id=str(uuid.uuid4()),
                        conversation_id=conv_id,
                        role="assistant",
                        content=full_content,
                        created_at=datetime.utcnow(),
                    )
                    db.add(assistant_msg)

                yield f"data: {json.dumps({'done': True, 'conversation_id': conv_id})}\n\n"
            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        await db.commit()
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        # Non-streaming response
        result = await agent_registry.coordinator.run(context)
        assistant_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conv_id,
            role="assistant",
            content=str(result.output),
            created_at=datetime.utcnow(),
        )
        db.add(assistant_msg)
        await db.commit()

        return ChatResponse(
            message_id=assistant_msg.id,
            conversation_id=conv_id,
            content=str(result.output),
        )


@router.get("/conversations")
async def list_conversations(db: AsyncSession = Depends(get_db)):
    """List all conversations."""
    from sqlalchemy import select
    from app.models.conversation import Conversation
    result = await db.execute(
        select(Conversation).order_by(Conversation.updated_at.desc()).limit(50)
    )
    convs = result.scalars().all()
    return [
        {
            "id": c.id,
            "title": c.title or "Untitled",
            "context_type": c.context_type,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in convs
    ]


@router.get("/conversations/{conv_id}/messages")
async def get_messages(conv_id: str, db: AsyncSession = Depends(get_db)):
    """Get messages for a conversation."""
    from sqlalchemy import select
    from app.models.conversation import Message
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.asc())
    )
    msgs = result.scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in msgs
    ]


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a conversation."""
    from sqlalchemy import select, delete
    from app.models.conversation import Conversation, Message
    await db.execute(delete(Message).where(Message.conversation_id == conv_id))
    await db.execute(delete(Conversation).where(Conversation.id == conv_id))
    await db.commit()
    return {"success": True}
