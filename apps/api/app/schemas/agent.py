from __future__ import annotations

from pydantic import BaseModel, Field


class AgentRead(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    provider: str | None = None
    model_name: str | None = None
    status: str = 'active'
    workspace_id: int


class AgentExecutionRead(BaseModel):
    id: int
    workspace_id: int
    user_id: int | None = None
    agent_id: int
    conversation_id: int | None = None
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None
    error_message: str | None = None
    request_id: str | None = Field(default=None, alias='request_id')

    model_config = {'populate_by_name': True}
