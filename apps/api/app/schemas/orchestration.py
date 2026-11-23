from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OrchestrationRequest(BaseModel):
    message: str = Field(..., min_length=1)
    workspace_id: int = Field(..., gt=0)
    conversation_id: int | None = Field(default=None, gt=0)
    context: dict[str, Any] | None = None

    model_config = ConfigDict(extra='forbid')


class OrchestrationDecision(BaseModel):
    intent: str
    agent_id: str | None = None
    supported: bool = True
    status: str = 'routed'
    reason: str | None = None


class OrchestrationResponse(BaseModel):
    execution_id: int | None = None
    intent: str | None = None
    agent_id: str | None = None
    status: str = 'completed'
    result: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra='forbid')
