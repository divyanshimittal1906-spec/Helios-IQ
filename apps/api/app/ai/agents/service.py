from __future__ import annotations

import asyncio
import inspect
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.agents.base import AgentContext, AgentDefinition, ToolExecutionError
from app.ai.agents.registry import AgentRegistry, ToolRegistry
from app.api.dependencies import require_workspace_access
from app.db.models import Agent, AgentExecution


class ExecutionStatus(str, Enum):
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'

    @classmethod
    def normalize(cls, value: str | 'ExecutionStatus') -> str:
        if isinstance(value, cls):
            return value.value
        normalized = str(value).strip().upper()
        if normalized == 'QUEUED':
            return cls.PENDING.value
        return normalized


class AgentExecutionService:
    """Handles deterministic execution lifecycle for workspace-scoped agents."""

    SENSITIVE_KEYS = {
        'api_key',
        'apikey',
        'token',
        'secret',
        'password',
        'authorization',
        'cookie',
        'session',
        'access_token',
        'refresh_token',
    }

    def __init__(
        self,
        session: Session,
        registry: AgentRegistry | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self.session = session
        self.registry = registry or AgentRegistry()
        self.tool_registry = tool_registry or ToolRegistry()

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _ensure_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def _redact_string(cls, value: str) -> str:
        redacted = value
        redacted = re.sub(r'(?i)(authorization\s*[:=]\s*(?:bearer\s+)?)\S+', r'\1[REDACTED]', redacted)
        redacted = re.sub(r'(?i)(api[_-]?key|token|secret|password|authorization|cookie|session)\s*[:=]\s*([^\s,;\"\']+)', r'\1=[REDACTED]', redacted)
        redacted = re.sub(r'(?i)(sk_live_[A-Za-z0-9]+|ghp_[A-Za-z0-9]+|AIza[0-9A-Za-z\-_]+)', '[REDACTED]', redacted)
        return redacted

    @classmethod
    def _sanitize_value(cls, value: Any) -> Any:
        if isinstance(value, dict):
            cleaned: dict[str, Any] = {}
            for key, item in value.items():
                lowered = str(key).lower()
                if (
                    lowered in cls.SENSITIVE_KEYS
                    or 'secret' in lowered
                    or 'token' in lowered
                    or 'password' in lowered
                    or lowered.endswith('_key')
                    or lowered.endswith('apikey')
                ):
                    cleaned[key] = '[REDACTED]'
                else:
                    cleaned[key] = cls._sanitize_value(item)
            return cleaned
        if isinstance(value, list):
            return [cls._sanitize_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(cls._sanitize_value(item) for item in value)
        if isinstance(value, str):
            return cls._redact_string(value)
        return value

    def _assert_workspace_access(self, user_id: int, workspace_id: int) -> None:
        try:
            require_workspace_access(self.session, user_id, workspace_id)
        except HTTPException as exc:
            raise PermissionError(str(exc.detail)) from exc

    def _assert_agent_available(self, agent_id: str) -> AgentDefinition:
        if not self.registry.exists(agent_id):
            raise KeyError(f'Agent "{agent_id}" is not available.')
        return self.registry.get(agent_id)

    def _resolve_agent_record_id(self, agent_id: str) -> int:
        row = self.session.execute(select(Agent).where(Agent.slug == agent_id)).scalar_one_or_none()
        if row is not None:
            return int(row.id)
        return 1

    def _agent_id_from_execution(self, execution: AgentExecution) -> str:
        payload = execution.input_payload or {}
        if isinstance(payload, dict):
            agent_id = payload.get('agent_id')
            if agent_id is not None:
                return str(agent_id)
        if self.registry.list():
            return self.registry.list()[0]
        raise KeyError('No agent mapping available for execution.')

    def create_execution(
        self,
        *,
        user_id: int,
        workspace_id: int,
        agent_id: str,
        input_payload: dict[str, Any] | None = None,
        request_id: str | None = None,
        conversation_id: int | None = None,
        allowed_tools: list[str] | None = None,
    ) -> AgentExecution:
        self._assert_workspace_access(user_id, workspace_id)
        self._assert_agent_available(agent_id)
        sanitized_payload = self._sanitize_value(input_payload or {})
        sanitized_payload['agent_id'] = agent_id
        if request_id is not None:
            sanitized_payload['request_id'] = request_id
        if allowed_tools is not None:
            sanitized_payload['allowed_tools'] = list(allowed_tools)

        execution = AgentExecution(
            workspace_id=workspace_id,
            user_id=user_id,
            agent_id=self._resolve_agent_record_id(agent_id),
            conversation_id=conversation_id,
            status=ExecutionStatus.PENDING.value,
            input_payload=sanitized_payload,
            output_payload=None,
            error_message=None,
            started_at=None,
            completed_at=None,
            duration_ms=None,
        )
        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)
        return execution

    def set_status(self, execution: AgentExecution, status: ExecutionStatus | str) -> AgentExecution:
        current = ExecutionStatus.normalize(execution.status)
        target = ExecutionStatus.normalize(status)
        valid_transitions = {
            ExecutionStatus.PENDING.value: {ExecutionStatus.RUNNING.value, ExecutionStatus.CANCELLED.value},
            ExecutionStatus.RUNNING.value: {ExecutionStatus.COMPLETED.value, ExecutionStatus.FAILED.value, ExecutionStatus.CANCELLED.value},
            ExecutionStatus.COMPLETED.value: set(),
            ExecutionStatus.FAILED.value: set(),
            ExecutionStatus.CANCELLED.value: set(),
        }
        if current not in valid_transitions or target not in valid_transitions[current]:
            raise ValueError(f'Invalid execution transition from {current} to {target}.')

        execution.status = target
        if execution.status == ExecutionStatus.RUNNING.value and execution.started_at is None:
            execution.started_at = self._ensure_utc(self._utc_now())
        execution.started_at = self._ensure_utc(execution.started_at)
        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)
        return execution

    def mark_failed(self, execution: AgentExecution, error_category: str, message: str, *, metadata: dict[str, Any] | None = None) -> AgentExecution:
        execution.status = ExecutionStatus.FAILED.value
        execution.error_message = self._sanitize_value(message)
        execution.output_payload = self._sanitize_value({'error_category': error_category, 'details': metadata or {}})
        execution.completed_at = self._ensure_utc(self._utc_now())
        execution.started_at = self._ensure_utc(execution.started_at)
        if execution.started_at is not None:
            execution.duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)
        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)
        return execution

    def cancel(self, execution: AgentExecution) -> AgentExecution:
        execution.status = ExecutionStatus.CANCELLED.value
        execution.completed_at = self._ensure_utc(self._utc_now())
        execution.started_at = self._ensure_utc(execution.started_at)
        if execution.started_at is not None:
            execution.duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)
        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)
        return execution

    def record_safe_metadata(self, execution: AgentExecution, metadata: dict[str, Any]) -> AgentExecution:
        execution.input_payload = self._sanitize_value(metadata)
        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)
        return execution

    async def execute_agent_execution_async(
        self,
        execution: AgentExecution,
        *,
        payload: dict[str, Any],
        context: AgentContext | None = None,
    ) -> dict[str, Any]:
        agent_id = self._agent_id_from_execution(execution)
        agent = self._assert_agent_available(agent_id)
        validated = agent.validate_input(payload)

        if context is None:
            context = AgentContext(
                user_id=execution.user_id,
                workspace_id=execution.workspace_id,
                allowed_tools=list(agent.tools),
            )
        elif context.allowed_tools:
            agent.validate_tools(context.allowed_tools)
        else:
            context.allowed_tools = list(agent.tools)

        self.set_status(execution, ExecutionStatus.RUNNING)
        try:
            raw_result = agent.execute(validated.model_dump() if hasattr(validated, 'model_dump') else validated, context)
            if inspect.isawaitable(raw_result):
                result = await raw_result
            else:
                result = raw_result
            validated_output = agent.validate_output(result)
            execution.output_payload = self._sanitize_value(
                validated_output.model_dump() if hasattr(validated_output, 'model_dump') else validated_output
            )
            execution.completed_at = self._ensure_utc(self._utc_now())
            execution.started_at = self._ensure_utc(execution.started_at)
            execution.status = ExecutionStatus.COMPLETED.value
            if execution.started_at is not None:
                execution.duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)
            self.session.add(execution)
            self.session.commit()
            self.session.refresh(execution)
            return execution.output_payload
        except (ValueError, TypeError, PermissionError, ToolExecutionError, RuntimeError) as exc:
            if isinstance(exc, ValueError) and 'Invalid input' in str(exc):
                error_category = 'validation_error'
            elif isinstance(exc, PermissionError):
                error_category = 'tool_not_allowed'
            elif isinstance(exc, ToolExecutionError):
                error_category = exc.code
            else:
                error_category = 'execution_error'
            self.mark_failed(execution, error_category, str(exc))
            raise

    def execute_agent_execution(
        self,
        execution: AgentExecution,
        *,
        payload: dict[str, Any],
        context: AgentContext | None = None,
    ) -> dict[str, Any]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.execute_agent_execution_async(execution, payload=payload, context=context))
        raise RuntimeError(
            'Cannot execute agent synchronously while an event loop is already running. '
            'Use await execute_agent_execution_async(...) from async request handlers.'
        )
