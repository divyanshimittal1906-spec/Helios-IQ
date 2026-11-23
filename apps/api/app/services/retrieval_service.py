from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import Document, DocumentChunk
from app.services.embedding_service import EmbeddingService


@dataclass(slots=True)
class RetrievedChunk:
    chunk_id: int
    document_id: int
    workspace_id: int
    knowledge_base_id: int
    document_title: str
    file_name: str
    chunk_index: int
    content: str
    similarity: float
    metadata: dict[str, Any]

    @property
    def citation(self) -> dict[str, Any]:
        return {
            'chunk_id': self.chunk_id,
            'document_id': self.document_id,
            'document_title': self.document_title,
            'file_name': self.file_name,
            'knowledge_base_id': self.knowledge_base_id,
            'chunk_index': self.chunk_index,
            'similarity': round(self.similarity, 6),
            'source_metadata': self.metadata,
        }


class RetrievalService:
    def __init__(self, session: object, embedding_provider: object | None = None, top_k: int | None = None) -> None:
        self.session = session
        self.settings = get_settings()
        self.top_k = top_k or self.settings.rag_top_k
        self.embedding_service = EmbeddingService(session, provider=embedding_provider)

    @staticmethod
    def _cosine_similarity(query_vector: list[float], candidate_vector: list[float]) -> float:
        if len(query_vector) != len(candidate_vector):
            return 0.0
        dot = sum(a * b for a, b in zip(query_vector, candidate_vector))
        norm_query = math.sqrt(sum(value * value for value in query_vector))
        norm_candidate = math.sqrt(sum(value * value for value in candidate_vector))
        if norm_query == 0 or norm_candidate == 0:
            return 0.0
        return dot / (norm_query * norm_candidate)

    def retrieve(
        self,
        *,
        workspace_id: int,
        query_text: str,
        knowledge_base_id: int | None = None,
        top_k: int | None = None,
        min_similarity: float | None = None,
    ) -> list[RetrievedChunk]:
        if not query_text or not query_text.strip():
            raise ValueError('Query text is required.')

        query_vector = self.embedding_service.embed_text(query_text)
        candidate_limit = top_k or self.top_k
        min_similarity_value = min_similarity if min_similarity is not None else 0.2
        base_query = (
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.workspace_id == workspace_id)
            .where(DocumentChunk.workspace_id == workspace_id)
            .where(DocumentChunk.embedding.isnot(None))
        )
        if knowledge_base_id is not None:
            base_query = base_query.where(Document.knowledge_base_id == knowledge_base_id)

        rows = self.session.execute(base_query.limit(candidate_limit * 20)).all()
        if not rows:
            return []
        results = []
        for chunk, document in rows:
            embedding = chunk.embedding
            if embedding is None:
                continue
            if isinstance(embedding, (list, tuple)) and len(embedding) == 0:
                continue
            try:
                candidate_vector = list(embedding)
            except TypeError:
                continue
            similarity = self._cosine_similarity(query_vector, candidate_vector)
            if similarity < min_similarity_value:
                continue
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    workspace_id=document.workspace_id,
                    knowledge_base_id=document.knowledge_base_id,
                    document_title=document.title,
                    file_name=document.file_name,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    similarity=similarity,
                    metadata={
                        'document_id': document.id,
                        'document_title': document.title,
                        'file_name': document.file_name,
                        'knowledge_base_id': document.knowledge_base_id,
                        'chunk_id': chunk.id,
                        'chunk_index': chunk.chunk_index,
                        'status': document.status,
                    },
                )
            )
        results.sort(key=lambda item: item.similarity, reverse=True)
        return results[:candidate_limit]
