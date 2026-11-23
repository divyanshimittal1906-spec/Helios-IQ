from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Organization(Base):
    __tablename__ = 'organizations'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    members: Mapped[list['OrganizationMember']] = relationship(back_populates='organization', cascade='all, delete-orphan')
    workspaces: Mapped[list['Workspace']] = relationship(back_populates='organization', cascade='all, delete-orphan')


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization_memberships: Mapped[list['OrganizationMember']] = relationship(back_populates='user', cascade='all, delete-orphan')
    owned_workspaces: Mapped[list['Workspace']] = relationship(back_populates='owner', foreign_keys='Workspace.owner_id')
    projects_owned: Mapped[list['Project']] = relationship(back_populates='owner', foreign_keys='Project.owner_id')
    tasks_assigned: Mapped[list['Task']] = relationship(back_populates='assignee', foreign_keys='Task.assignee_id')
    conversations: Mapped[list['Conversation']] = relationship(back_populates='user', cascade='all, delete-orphan')
    messages: Mapped[list['Message']] = relationship(back_populates='user', cascade='all, delete-orphan')
    executions: Mapped[list['AgentExecution']] = relationship(back_populates='user', cascade='all, delete-orphan')


class OrganizationMember(Base):
    __tablename__ = 'organization_members'
    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id', name='uq_organization_member'),
        Index('ix_organization_member_org_user', 'organization_id', 'user_id'),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), default='member', nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='active', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization: Mapped[Organization] = relationship(back_populates='members')
    user: Mapped[User] = relationship(back_populates='organization_memberships')


class Workspace(Base):
    __tablename__ = 'workspaces'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default='active', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization: Mapped[Organization] = relationship(back_populates='workspaces')
    owner: Mapped[User] = relationship(back_populates='owned_workspaces', foreign_keys=[owner_id])
    projects: Mapped[list['Project']] = relationship(back_populates='workspace', cascade='all, delete-orphan')
    conversations: Mapped[list['Conversation']] = relationship(back_populates='workspace', cascade='all, delete-orphan')
    knowledge_bases: Mapped[list['KnowledgeBase']] = relationship(back_populates='workspace', cascade='all, delete-orphan')
    documents: Mapped[list['Document']] = relationship(back_populates='workspace', cascade='all, delete-orphan')
    agent_executions: Mapped[list['AgentExecution']] = relationship(back_populates='workspace', cascade='all, delete-orphan')
    integrations: Mapped[list['Integration']] = relationship(back_populates='workspace', cascade='all, delete-orphan')
    automations: Mapped[list['Automation']] = relationship(back_populates='workspace', cascade='all, delete-orphan')
    agents: Mapped[list['Agent']] = relationship(back_populates='workspace', cascade='all, delete-orphan')
    tasks: Mapped[list['Task']] = relationship(back_populates='workspace', cascade='all, delete-orphan')


class Project(Base):
    __tablename__ = 'projects'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default='active', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workspace: Mapped[Workspace] = relationship(back_populates='projects')
    owner: Mapped[User] = relationship(back_populates='projects_owned', foreign_keys=[owner_id])
    tasks: Mapped[list['Task']] = relationship(back_populates='project', cascade='all, delete-orphan')


class Task(Base):
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'), nullable=True, index=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default='todo', nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    workspace: Mapped[Workspace] = relationship(back_populates='tasks')
    project: Mapped[Project | None] = relationship(back_populates='tasks')
    assignee: Mapped[User | None] = relationship(back_populates='tasks_assigned', foreign_keys=[assignee_id])
