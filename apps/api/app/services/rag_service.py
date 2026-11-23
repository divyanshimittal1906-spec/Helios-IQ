from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.ai.provider import AIProvider, OpenAICompatibleChatProvider, get_ai_provider
from app.api.dependencies import require_workspace_access
from app.core.config import get_settings
from app.db.models import KnowledgeBase
from app.services.retrieval_service import RetrievalService


class RAGService:
    INSUFFICIENT_EVIDENCE_MESSAGE = "I couldn't find enough information in the selected Knowledge Base to answer this question."

    def __init__(self, session: object, embedding_provider: object | None = None, ai_provider: AIProvider | None = None) -> None:
        self.session = session
        self.settings = get_settings()
        self.embedding_provider = embedding_provider
        self.ai_provider = ai_provider or get_ai_provider()

    def _assert_access(self, user_id: int, workspace_id: int, knowledge_base_id: int) -> KnowledgeBase:
        workspace = require_workspace_access(self.session, user_id, workspace_id)
        knowledge_base = self.session.get(KnowledgeBase, knowledge_base_id)
        if knowledge_base is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Knowledge base not found.')
        if knowledge_base.workspace_id != workspace.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Knowledge base does not belong to this workspace.')
        return knowledge_base

    def _build_context(self, chunks: list[object], max_context_chunks: int | None = None, max_context_tokens: int | None = None) -> dict[str, Any]:
        chunk_limit = max_context_chunks or self.settings.rag_max_context_chunks
        token_limit = max_context_tokens or self.settings.rag_max_context_tokens
        selected: list[object] = []
        seen: set[tuple[int, int]] = set()
        for chunk in chunks:
            key = (chunk.document_id, chunk.chunk_id)
            if key in seen:
                continue
            seen.add(key)
            selected.append(chunk)
            if len(selected) >= chunk_limit:
                break

        context_parts: list[str] = []
        tokens = 0
        citations: list[dict[str, Any]] = []
        for chunk in selected:
            text = (chunk.content or '').strip()
            if not text:
                continue
            tokens += max(1, len(text.split()))
            if tokens > token_limit:
                break
            context_parts.append(f"Source: {chunk.document_title} ({chunk.file_name})\n{chunk.content}")
            citations.append(chunk.citation)

        return {
            'chunks': selected,
            'context': '\n\n'.join(context_parts),
            'citations': citations,
            'token_count': tokens,
        }

    def _fallback_answer(self, context: str) -> str:
        if not context.strip():
            return self.INSUFFICIENT_EVIDENCE_MESSAGE
        return context.strip()[:1200]

    def query(
        self,
        *,
        user_id: int,
        workspace_id: int,
        knowledge_base_id: int,
        query_text: str,
        top_k: int | None = None,
        max_context_chunks: int | None = None,
        max_context_tokens: int | None = None,
        min_similarity: float | None = None,
    ) -> dict[str, Any]:
        self._assert_access(user_id, workspace_id, knowledge_base_id)
        if not query_text or not query_text.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Query text is required.')

        retrieval_service = RetrievalService(self.session, embedding_provider=self.embedding_provider, top_k=top_k or self.settings.rag_top_k)
        chunks = retrieval_service.retrieve(
            workspace_id=workspace_id,
            query_text=query_text,
            knowledge_base_id=knowledge_base_id,
            top_k=top_k or self.settings.rag_top_k,
            min_similarity=min_similarity if min_similarity is not None else 0.15,
        )
        if not chunks:
            return {
                'answer': self.INSUFFICIENT_EVIDENCE_MESSAGE,
                'citations': [],
                'context': '',
                'insufficient_evidence': True,
                'retrieved_chunks': 0,
            }

        context = self._build_context(chunks, max_context_chunks=max_context_chunks, max_context_tokens=max_context_tokens)
        if not context['context'].strip():
            return {
                'answer': self.INSUFFICIENT_EVIDENCE_MESSAGE,
                'citations': [],
                'context': '',
                'insufficient_evidence': True,
                'retrieved_chunks': 0,
            }

        prompt = (
            'Use only the retrieved knowledge-base context below to answer the user question. '
            'If the evidence is insufficient, say that you could not find enough information in the selected Knowledge Base. '
            'Cite only the provided source snippets.\n\n'
            f'Question: {query_text}\n\n'
            f'Context:\n{context["context"]}'
        )

        provider = self.ai_provider or get_ai_provider()
        answer = self._fallback_answer(context['context'])
        if provider is not None:
            try:
                answer = provider.generate(prompt, temperature=0.2, max_tokens=512)
            except Exception:
                answer = self._fallback_answer(context['context'])

        return {
            'answer': answer,
            'citations': context['citations'],
            'context': context['context'],
            'insufficient_evidence': False,
            'retrieved_chunks': len(context['chunks']),
        }
