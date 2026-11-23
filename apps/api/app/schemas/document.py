from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    knowledge_base_id: int
    title: str
    file_name: str
    mime_type: str
    storage_path: str
    checksum: str | None = None
    status: str
    document_metadata: dict | None = None
    extracted_text: str | None = None
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime
