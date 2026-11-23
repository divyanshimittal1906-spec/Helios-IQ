from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Agent(Base):
    __tablename__ = 'agents'
    __table_args__ = (Index('ix_agents_workspace_name', 'workspace_id', 'name'),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(80), default='openai', nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), default='gpt-4o-mini', nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='active', nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workspace: Mapped['Workspace'] = relationship(back_populates='agents')
    tools: Mapped[list['AgentTool']] = relationship(back_populates='agent', cascade='all, delete-orphan')
    executions: Mapped[list['AgentExecution']] = relationship(back_populates='agent', cascade='all, delete-orphan')
    conversations: Mapped[list['Conversation']] = relationship(back_populates='agent')


class AgentTool(Base):
    __tablename__ = 'agent_tools'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey('agents.id', ondelete='CASCADE'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    agent: Mapped[Agent] = relationship(back_populates='tools')


class AgentExecution(Base):
    __tablename__ = 'agent_executions'
    __table_args__ = (Index('ix_agent_execution_workspace_status', 'workspace_id', 'status'),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey('agents.id', ondelete='CASCADE'), nullable=False, index=True)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey('conversations.id', ondelete='SET NULL'), nullable=True, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey('projects.id', ondelete='SET NULL'), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default='queued', nullable=False)
    input_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workspace: Mapped['Workspace'] = relationship(back_populates='agent_executions')
    user: Mapped['User | None'] = relationship(back_populates='executions')
    agent: Mapped[Agent] = relationship(back_populates='executions')
    conversation: Mapped['Conversation | None'] = relationship(back_populates='executions')
