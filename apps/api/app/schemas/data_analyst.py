from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DataAnalysisRequest(BaseModel):
    workspace_id: int = Field(..., gt=0)
    filename: str = Field(..., min_length=1)
    content_type: str = Field(..., min_length=3)
    file_content: bytes | None = None

    model_config = ConfigDict(extra='forbid')


class DataAnalysisResponse(BaseModel):
    dataset: dict[str, Any]
    columns: list[dict[str, Any]]
    statistics: dict[str, Any]
    data_quality: dict[str, Any]
    insights: list[str]
    chart_ready: list[dict[str, Any]] = Field(default_factory=list)
    execution_id: int | None = None
    status: str = 'completed'

    model_config = ConfigDict(extra='forbid')
