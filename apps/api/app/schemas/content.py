from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContentType(str, Enum):
    BLOG = 'blog'
    SOCIAL_MEDIA_POST = 'social_media_post'
    EMAIL = 'email'
    PRODUCT_DESCRIPTION = 'product_description'
    REPORT = 'report'


class ContentGenerationRequest(BaseModel):
    content_type: ContentType
    topic: str = Field(..., min_length=3)
    target_audience: str = Field(..., min_length=2)
    tone: str = Field(..., min_length=2)
    desired_length: str = Field(default='medium', min_length=2)
    key_points: list[str] = Field(default_factory=list)
    brand_voice: str | None = Field(default=None, max_length=500)
    language: str = Field(default='en', min_length=2, max_length=10)
    instructions: str | None = Field(default=None, max_length=2000)
    workspace_id: int = Field(..., gt=0)

    model_config = ConfigDict(extra='forbid')

    @field_validator('key_points')
    @classmethod
    def validate_key_points(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for point in value:
            item = str(point).strip()
            if item:
                cleaned.append(item)
        if not cleaned:
            raise ValueError('At least one key point is recommended for content generation.')
        return cleaned[:10]


class ContentGenerationResponse(BaseModel):
    content: str
    content_type: ContentType
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_id: int | None = None
    status: str = 'completed'

    model_config = ConfigDict(extra='forbid')
