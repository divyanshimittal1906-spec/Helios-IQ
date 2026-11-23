from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    workspace_id: int = Field(..., gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    initial_message: str | None = Field(default=None, min_length=1, max_length=20000)


class MessageCreate(BaseModel):
    role: str = 'user'
    content: str = Field(..., min_length=1, max_length=20000)
    metadata: dict[str, object] | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    workspace_id: int
    conversation_id: int
    user_id: int | None
    role: str
    content: str
    metadata: dict[str, object] | None = Field(default=None, validation_alias='message_metadata', serialization_alias='metadata')
    created_at: datetime
