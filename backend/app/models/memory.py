"""
J.A.Y. Long-Term Memory Models
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, JSON, Float
from app.core.database import Base
from datetime import datetime
import uuid


def gen_uuid():
    return str(uuid.uuid4())


class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id = Column(String, primary_key=True, default=gen_uuid)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    category = Column(String(100), nullable=False)  # preference, fact, habit, project, lesson, task
    subcategory = Column(String(100), nullable=True)
    source_type = Column(String(50), default="conversation")  # conversation, manual, system
    source_id = Column(String, nullable=True)
    importance = Column(Float, default=0.5)  # 0.0 - 1.0
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, nullable=True)
    embedding_id = Column(String, nullable=True)
    tags = Column(JSON, default=list)
    project_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    metadata_ = Column(JSON, default=dict)


class UserProfile(Base):
    __tablename__ = "user_profile"

    id = Column(String, primary_key=True, default=gen_uuid)
    key = Column(String(200), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    category = Column(String(100), default="general")
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
