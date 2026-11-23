from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.provider import EmbeddingProvider, get_embedding_provider
from app.core.config import get_settings
from app.db.models import DocumentChunk


class EmbeddingProviderError(RuntimeError):
    pass


class EmbeddingService:
    def __init__(self, session: Session, provider: EmbeddingProvider | None = None) -> None:
        self.session = session
        self.settings = get_settings()
        self.provider = provider or get_embedding_provider()

    def _with_retry(self, fn_name: str, operation: object) -> object:
        last_error: Exception | None = None
        attempts = max(1, self.settings.embedding_max_retries)
        for attempt in range(1, attempts + 1):
            try:
                return operation()
            except Exception as exc:  # pragma: no cover - safety wrapper
                last_error = exc
                if attempt == attempts:
                    raise EmbeddingProviderError(f'{fn_name} failed after {attempts} attempts: {exc}') from exc
        if last_error is not None:
            raise EmbeddingProviderError(f'{fn_name} failed: {last_error}')
        raise EmbeddingProviderError(f'{fn_name} failed without a concrete error.')

    def embed_text(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError('Query text is required for embedding generation.')
        return self._with_retry('embed_text', lambda: self.provider.embed_text(text))

    def embed_documents(self, documents: Sequence[str]) -> list[list[float]]:
        if not documents:
            return []
        cleaned = [str(document).strip() for document in documents if str(document).strip()]
        if not cleaned:
            return []
        return self._with_retry('embed_documents', lambda: self.provider.embed_documents(cleaned))

    def generate_document_embeddings(self, document_id: int) -> list[DocumentChunk]:
        statement = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        chunks = self.session.execute(statement).scalars().all()
        if not chunks:
            return []

        texts = [chunk.content for chunk in chunks]
        embeddings = self.embed_documents(texts)
        if len(embeddings) != len(chunks):
            raise EmbeddingProviderError('Embedding generation returned an incomplete result set for the document chunks.')

        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
            self.session.add(chunk)

        self.session.commit()
        return chunks
