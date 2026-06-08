"""
J.A.Y. Project & Task Models
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import uuid


def gen_uuid():
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    project_type = Column(String(50), default="general")  # web, mobile, api, trading, research
    status = Column(String(30), default="active")  # active, paused, completed, archived
    path = Column(String(500), nullable=True)
    tech_stack = Column(JSON, default=list)
    dependencies = Column(JSON, default=dict)
    git_remote = Column(String(500), nullable=True)
    git_branch = Column(String(100), nullable=True)
    architecture = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_ = Column(JSON, default=dict)

    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="project")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=gen_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(30), default="todo")  # todo, in_progress, done, blocked, cancelled
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    tags = Column(JSON, default=list)
    subtasks = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="tasks")


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(String, primary_key=True, default=gen_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    remind_at = Column(DateTime, nullable=False)
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String(100), nullable=True)  # daily, weekly, cron
    is_triggered = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
