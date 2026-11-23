from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.ai.agents.base import Agent, AgentContext, Tool
from app.ai.agents.registry import AgentRegistry


class SearchResult(BaseModel):
    title: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    snippet: str = Field(default='')
    publication_date: str | None = None
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        raise NotImplementedError('Concrete search provider implementations are required.')


class DefaultSearchProvider(SearchProvider):
    def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        normalized = (query or '').strip()
        if not normalized:
            return []
        return [
            SearchResult(
                title='Local knowledge base result',
                url='https://internal.local/knowledge-base',
                source='internal.local',
                snippet='No public search provider is configured, therefore only workspace-backed knowledge is used for this request.',
                publication_date='n/a',
                relevance_score=1.0,
            )
        ][: max(1, min(limit, 5))]


class SearchToolInput(BaseModel):
    query: str = Field(..., min_length=3)
    limit: int = Field(default=5, ge=1, le=10)


class SearchToolOutput(BaseModel):
    query: str
    count: int
    results: list[dict[str, Any]]


class SearchTool(Tool):
    id = 'research-search'
    name = 'research_search'
    description = 'Searches authoritative sources and returns structured evidence for a research request.'
    input_schema = SearchToolInput
    output_schema = SearchToolOutput
    permissions = ('workspace:read',)

    def __init__(self, search_provider: SearchProvider | None = None) -> None:
        self.search_provider = search_provider or DefaultSearchProvider()

    def check_permissions(self, context: AgentContext | None = None) -> None:
        super().check_permissions(context)
        if context is not None and context.workspace_id is not None and context.workspace_id <= 0:
            raise PermissionError('workspace_id must be greater than zero.')

    async def execute(self, payload: dict[str, Any], context: AgentContext | None = None) -> dict[str, Any]:
        self.check_permissions(context)
        validated = self.validate_input(payload)
        query = validated.query.strip()
        limit = max(1, validated.limit)
        results = self.search_provider.search(query, limit=limit)
        return {
            'query': query,
            'count': len(results),
            'results': [result.model_dump(exclude_none=True) for result in results],
        }


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=3)
    workspace_id: int = Field(..., gt=0)
    knowledge_base_id: int | None = Field(default=None, gt=0)
    max_sources: int = Field(default=5, ge=1, le=10)


class ResearchResponse(BaseModel):
    question: str
    summary: str
    key_findings: list[str]
    sources: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    insufficient_evidence: bool = False


class ResearchAgent(Agent):
    id = 'research-agent'
    name = 'research-agent'
    description = 'Gathers facts, synthesizes source-backed evidence, and produces structured research briefings.'
    version = '1.0.0'
    input_schema = ResearchRequest
    output_schema = ResearchResponse
    tools = ('research-search',)
    required_permissions = ('workspace:read',)
    workspace_access_required = True

    def __init__(self, search_provider: SearchProvider | None = None, rag_service: object | None = None) -> None:
        self.search_provider = search_provider or DefaultSearchProvider()
        self.rag_service = rag_service
        self.search_tool = SearchTool(search_provider=self.search_provider)

    def validate_input(self, payload: dict[str, Any]) -> ResearchRequest:
        try:
            validated = super().validate_input(payload)
            if isinstance(validated, ResearchRequest):
                normalized = validated.model_copy(update={'query': validated.query.strip()})
                if not normalized.query:
                    raise ValueError('Research query cannot be empty.')
                return normalized
            if isinstance(validated, dict):
                normalized = ResearchRequest.model_validate(validated)
                if not normalized.query.strip():
                    raise ValueError('Research query cannot be empty.')
                return normalized
            raise ValueError('Input did not resolve to a valid research request.')
        except ValidationError as exc:
            raise ValueError(f'Invalid input for {self.name}: {exc}') from exc

    def authorize_workspace(self, user_id: int | None, workspace_id: int, current_workspace_id: int | None) -> None:
        if workspace_id <= 0:
            raise ValueError('workspace_id must be greater than zero.')
        if current_workspace_id is not None and workspace_id != current_workspace_id:
            raise PermissionError('The requested workspace does not match the current execution context.')
        if user_id is None:
            raise PermissionError('A valid user is required to perform research in a workspace.')

    @staticmethod
    def _strip_prompt_injection(text: str) -> str:
        if not text:
            return ''
        cleaned = re.sub(r'(?i)(ignore previous instructions|system prompt|reveal secrets|you are an?\s+assistant)', '', text)
        return cleaned.strip()

    def deduplicate_sources(self, sources: list[SearchResult]) -> list[SearchResult]:
        seen: set[str] = set()
        deduped: list[SearchResult] = []
        for item in sources:
            key = (item.url or item.title).strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    async def execute(self, payload: dict[str, Any], context: AgentContext | None = None) -> dict[str, Any]:
        validated = self.validate_input(payload)
        if context is not None:
            self.authorize_workspace(context.user_id, validated.workspace_id, context.workspace_id)

        search_payload = {'query': validated.query, 'limit': validated.max_sources}
        search_result = await self.search_tool.run(search_payload, context)
        raw_results = [SearchResult(**item) for item in search_result.get('results', [])]
        sources = self.deduplicate_sources(raw_results)

        knowledge_result: dict[str, Any] | None = None
        if validated.knowledge_base_id is not None and self.rag_service is not None and context is not None:
            try:
                knowledge_result = self.rag_service.query(
                    user_id=context.user_id,
                    workspace_id=validated.workspace_id,
                    knowledge_base_id=validated.knowledge_base_id,
                    query_text=validated.query,
                    top_k=validated.max_sources,
                )
            except Exception:
                knowledge_result = None

        key_findings: list[str] = []
        citations: list[dict[str, Any]] = []
        for item in sources:
            snippet = self._strip_prompt_injection(item.snippet or item.title)
            if snippet:
                key_findings.append(snippet)
            citations.append(
                {
                    'title': item.title,
                    'url': item.url,
                    'source': item.source,
                    'snippet': snippet,
                    'publication_date': item.publication_date,
                }
            )

        if knowledge_result and not knowledge_result.get('insufficient_evidence', False):
            kb_answer = str(knowledge_result.get('answer', '')).strip()
            if kb_answer:
                key_findings.insert(0, kb_answer)
            for citation in knowledge_result.get('citations', []) or []:
                if isinstance(citation, dict) and citation.get('file_name'):
                    citations.append(
                        {
                            'title': citation.get('document_title') or citation.get('file_name'),
                            'url': citation.get('url') or f'knowledge-base://{citation.get("document_id")}',
                            'source': citation.get('file_name') or 'knowledge-base',
                            'snippet': self._strip_prompt_injection(str(citation.get('content', '') or citation.get('document_title', ''))),
                            'publication_date': None,
                        }
                    )

        if not key_findings:
            summary = 'Insufficient evidence was found for this research question. Please narrow the scope or provide additional source material.'
            insufficient_evidence = True
        else:
            summary = ' '.join(key_findings[:3])
            insufficient_evidence = False

        result = ResearchResponse(
            question=validated.query,
            summary=summary,
            key_findings=key_findings[:5],
            sources=[{'title': item.title, 'url': item.url, 'source': item.source, 'snippet': self._strip_prompt_injection(item.snippet or item.title)} for item in sources[: validated.max_sources]],
            citations=citations[: validated.max_sources],
            insufficient_evidence=insufficient_evidence,
        )
        return result.model_dump(exclude_none=True)


_research_agent_registry = AgentRegistry()
_try_agent = ResearchAgent()
try:
    _research_agent_registry.register(_try_agent)
except ValueError:
    pass


def get_research_agent_registry() -> AgentRegistry:
    return _research_agent_registry
