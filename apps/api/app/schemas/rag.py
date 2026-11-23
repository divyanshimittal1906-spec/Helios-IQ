from __future__ import annotations

from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    max_context_chunks: int = Field(default=5, ge=1, le=20)
    max_context_tokens: int = Field(default=2000, ge=1)
    min_similarity: float = Field(default=0.15, ge=0.0, le=1.0)


class Citation(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    file_name: str
    knowledge_base_id: int
    chunk_index: int
    similarity: float | None = None
    source_metadata: dict | None = None


class RAGQueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    context: str
    insufficient_evidence: bool = False
    retrieved_chunks: int = 0
