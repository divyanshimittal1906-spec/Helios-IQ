from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class KnowledgeBaseCreate(KnowledgeBaseBase):
    workspace_id: int = Field(..., gt=0)


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    workspace_id: int | None = Field(default=None, gt=0)


class KnowledgeBaseRead(KnowledgeBaseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime
