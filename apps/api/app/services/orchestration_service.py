from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ai.agents.base import AgentContext
from app.ai.agents.content_agent import get_content_agent_registry
from app.ai.agents.data_analyst_agent import get_data_analyst_registry
from app.ai.agents.registry import AgentRegistry
from app.ai.agents.research_agent import get_research_agent_registry
from app.ai.agents.service import AgentExecutionService, ExecutionStatus
from app.api.dependencies import require_workspace_access
from app.db.models import Conversation
from app.schemas.orchestration import OrchestrationDecision, OrchestrationRequest, OrchestrationResponse


class AIOrchestrator:
    """Deterministic workspace-scoped orchestration for the Helios IQ MVP."""

    INTENT_PATTERNS = {
        'RESEARCH': (
            'research', 'investigate', 'find information', 'find sources', 'compare information',
            'analyze sources', 'look up', 'source review', 'research report', 'sources', 'information',
            'facts', 'evidence'
        ),
        'CONTENT': (
            'write', 'create blog', 'write email', 'social post', 'product description',
            'generate content', 'content', 'blog', 'email', 'post', 'description', 'draft'
        ),
        'DATA_ANALYSIS': (
            'analyze csv', 'analyze dataset', 'calculate statistics', 'find insights',
            'analyze uploaded data', 'data analysis', 'dataset', 'csv', 'statistics', 'insights',
            'analyze this csv', 'analyze data', 'stats'
        ),
    }

    AGENT_MAP = {
        'RESEARCH': 'research-agent',
        'CONTENT': 'content-agent',
        'DATA_ANALYSIS': 'data-analyst-agent',
    }

    REGISTRY_MAP = {
        'RESEARCH': get_research_agent_registry,
        'CONTENT': get_content_agent_registry,
        'DATA_ANALYSIS': get_data_analyst_registry,
    }

    def __init__(self, session: Session, registry: AgentRegistry | None = None) -> None:
        self.session = session
        self.registry = registry or self._default_registry()
        self.execution_service = AgentExecutionService(session, registry=self.registry)

    @staticmethod
    def _default_registry() -> AgentRegistry:
        registry = AgentRegistry()
        for factory in (get_research_agent_registry, get_content_agent_registry, get_data_analyst_registry):
            child = factory()
            for agent_id in child.list():
                registry.register(child.get(agent_id))
        return registry

    @staticmethod
    def _normalize_message(value: str | None) -> str:
        if value is None:
            return ''
        return ' '.join(str(value).strip().split())

    @staticmethod
    def _redact_value(value: Any) -> Any:
        if isinstance(value, dict):
            cleaned: dict[str, Any] = {}
            for key, item in value.items():
                lowered = str(key).lower()
                if lowered in {'api_key', 'apikey', 'token', 'secret', 'password', 'authorization', 'cookie', 'session'} or 'secret' in lowered or 'token' in lowered or 'key' in lowered:
                    cleaned[key] = '[REDACTED]'
                else:
                    cleaned[key] = AIOrchestrator._redact_value(item)
            return cleaned
        if isinstance(value, list):
            return [AIOrchestrator._redact_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(AIOrchestrator._redact_value(item) for item in value)
        if isinstance(value, str):
            redacted = value
            redacted = re.sub(r'(?i)(authorization\s*[:=]\s*(?:bearer\s+)?)\S+', r'\1[REDACTED]', redacted)
            redacted = re.sub(r'(?i)(api[_-]?key|token|secret|password|authorization|cookie|session)\s*[:=]\s*([^\s,;\"\']+)', r'\1=[REDACTED]', redacted)
            redacted = re.sub(r'(?i)(sk_live_[A-Za-z0-9]+|ghp_[A-Za-z0-9]+|AIza[0-9A-Za-z\-_]+)', '[REDACTED]', redacted)
            return redacted
        return value

    def _validate_workspace(self, user_id: int, workspace_id: int) -> None:
        try:
            require_workspace_access(self.session, user_id, workspace_id)
        except HTTPException as exc:
            raise PermissionError(str(exc.detail)) from exc

    def _validate_conversation(self, user_id: int, workspace_id: int, conversation_id: int | None) -> None:
        if conversation_id is None:
            return
        conversation = self.session.get(Conversation, conversation_id)
        if conversation is None:
            raise ValueError('Conversation not found.')
        if conversation.workspace_id != workspace_id:
            raise ValueError('Conversation does not belong to the requested workspace.')
        if conversation.user_id != user_id:
            raise ValueError('Conversation does not belong to the authenticated user.')

    def route_request(self, message: str, *, workspace_id: int, user_id: int) -> OrchestrationDecision:
        normalized = self._normalize_message(message)
        if not normalized:
            return OrchestrationDecision(intent='UNKNOWN', agent_id=None, supported=False, status='unsupported', reason='Request message is empty.')

        lowered = normalized.lower()
        matches: list[tuple[str, int]] = []
        for intent, keywords in self.INTENT_PATTERNS.items():
            score = sum(1 for keyword in keywords if keyword in lowered)
            if score:
                matches.append((intent, score))

        if not matches:
            return OrchestrationDecision(intent='UNKNOWN', agent_id=None, supported=False, status='unsupported', reason='No supported intent was identified.')

        priority = ['RESEARCH', 'CONTENT', 'DATA_ANALYSIS']
        sorted_matches = sorted(matches, key=lambda item: (-item[1], priority.index(item[0]) if item[0] in priority else len(priority)))
        chosen_intent, chosen_score = sorted_matches[0]

        if len(sorted_matches) > 1 and sorted_matches[0][1] == sorted_matches[1][1]:
            candidate = next((intent for intent in priority if intent in {match[0] for match in sorted_matches}), chosen_intent)
            return OrchestrationDecision(intent=candidate, agent_id=self.AGENT_MAP[candidate], supported=True, status='ambiguous', reason='Multiple intents matched; selected deterministically by priority.')

        return OrchestrationDecision(intent=chosen_intent, agent_id=self.AGENT_MAP[chosen_intent], supported=True, status='routed')

    def _build_agent_payload(self, intent: str, message: str, *, context: dict[str, Any] | None) -> dict[str, Any]:
        payload: dict[str, Any] = {'workspace_id': context.get('workspace_id') if isinstance(context, dict) else None}
        if intent == 'RESEARCH':
            payload.update({
                'query': message,
                'workspace_id': context.get('workspace_id') if isinstance(context, dict) else None,
                'knowledge_base_id': context.get('knowledge_base_id') if isinstance(context, dict) else None,
                'max_sources': context.get('max_sources', 5) if isinstance(context, dict) else 5,
            })
        elif intent == 'CONTENT':
            payload.update({
                'content_type': context.get('content_type', 'blog') if isinstance(context, dict) else 'blog',
                'topic': message,
                'target_audience': context.get('target_audience', 'general audience') if isinstance(context, dict) else 'general audience',
                'tone': context.get('tone', 'clear and helpful') if isinstance(context, dict) else 'clear and helpful',
                'desired_length': context.get('desired_length', 'medium') if isinstance(context, dict) else 'medium',
                'key_points': context.get('key_points', [message]) if isinstance(context, dict) else [message],
                'brand_voice': context.get('brand_voice') if isinstance(context, dict) else None,
                'language': context.get('language', 'en') if isinstance(context, dict) else 'en',
                'instructions': context.get('instructions') if isinstance(context, dict) else None,
                'workspace_id': context.get('workspace_id') if isinstance(context, dict) else None,
            })
        elif intent == 'DATA_ANALYSIS':
            payload.update({
                'workspace_id': context.get('workspace_id') if isinstance(context, dict) else None,
                'filename': context.get('filename', 'dataset.csv') if isinstance(context, dict) else 'dataset.csv',
                'content_type': context.get('content_type', 'csv') if isinstance(context, dict) else 'csv',
                'file_content': context.get('file_content') if isinstance(context, dict) else None,
            })
        return payload

    def execute(
        self,
        *,
        message: str,
        workspace_id: int,
        user_id: int,
        conversation_id: int | None = None,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OrchestrationResponse:
        self._validate_workspace(user_id, workspace_id)
        self._validate_conversation(user_id, workspace_id, conversation_id)

        decision = self.route_request(message, workspace_id=workspace_id, user_id=user_id)
        if not decision.supported or decision.agent_id is None:
            return OrchestrationResponse(
                execution_id=None,
                intent=decision.intent,
                agent_id=decision.agent_id,
                status='unsupported',
                result=None,
                error=decision.reason or 'Unsupported request.',
                metadata={'workspace_id': workspace_id, 'conversation_id': conversation_id},
            )

        registry = self.REGISTRY_MAP[decision.intent]()
        if not registry.exists(decision.agent_id):
            raise KeyError(f'Agent "{decision.agent_id}" is not registered.')

        agent_payload = self._build_agent_payload(decision.intent, message, context={'workspace_id': workspace_id, **(context or {}), **(metadata or {})})
        execution = self.execution_service.create_execution(
            user_id=user_id,
            workspace_id=workspace_id,
            agent_id=decision.agent_id,
            input_payload={
                'message': message,
                'workspace_id': workspace_id,
                'conversation_id': conversation_id,
                **self._redact_value(context or {}),
            },
            conversation_id=conversation_id,
            request_id=f'{decision.agent_id}:{workspace_id}:{user_id}',
        )

        agent_context = AgentContext(
            user_id=user_id,
            workspace_id=workspace_id,
            conversation_id=str(conversation_id) if conversation_id is not None else None,
            execution_id=execution.id,
            allowed_tools=list(registry.get(decision.agent_id).tools),
            config={'db': self.session, 'metadata': self._redact_value(metadata or {})},
        )

        try:
            result = self.execution_service.execute_agent_execution(
                execution,
                payload=agent_payload,
                context=agent_context,
            )
            return OrchestrationResponse(
                execution_id=execution.id,
                intent=decision.intent,
                agent_id=decision.agent_id,
                status=str(execution.status).lower(),
                result=result,
                error=None,
                metadata={
                    'workspace_id': workspace_id,
                    'conversation_id': conversation_id,
                    'request': self._redact_value({'message': message, **(context or {})}),
                },
            )
        except (ValueError, TypeError, PermissionError, RuntimeError, KeyError) as exc:
            error_message = self._redact_value(str(exc))
            return OrchestrationResponse(
                execution_id=execution.id,
                intent=decision.intent,
                agent_id=decision.agent_id,
                status='failed',
                result=None,
                error=str(error_message),
                metadata={'workspace_id': workspace_id, 'conversation_id': conversation_id},
            )


def route_orchestration_request(payload: OrchestrationRequest, *, user_id: int, db: Session) -> OrchestrationDecision:
    orchestrator = AIOrchestrator(db)
    return orchestrator.route_request(payload.message, workspace_id=payload.workspace_id, user_id=user_id)


def execute_orchestration_request(payload: OrchestrationRequest, *, user_id: int, db: Session) -> OrchestrationResponse:
    orchestrator = AIOrchestrator(db)
    return orchestrator.execute(
        message=payload.message,
        workspace_id=payload.workspace_id,
        user_id=user_id,
        conversation_id=payload.conversation_id,
        context=payload.context,
    )
