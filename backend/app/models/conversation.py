"""
J.A.Y. Conversation & Message Models
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import uuid


def gen_uuid():
    return str(uuid.uuid4())


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    context_type = Column(String(50), default="general")  # general, coding, trading, research
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_archived = Column(Boolean, default=False)
    metadata_ = Column(JSON, default=dict)

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    project = relationship("Project", back_populates="conversations")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=gen_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)
    tool_results = Column(JSON, nullable=True)
    tokens_used = Column(Integer, default=0)
    model_used = Column(String(100), nullable=True)
    provider_used = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_ = Column(JSON, default=dict)
    embedding_id = Column(String, nullable=True)

    conversation = relationship("Conversation", back_populates="messages")
