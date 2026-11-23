from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Sequence

from pydantic import BaseModel, ValidationError


class ToolExecutionError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


@dataclass
class AgentContext:
    user_id: int | None = None
    organization_id: int | None = None
    workspace_id: int | None = None
    request_id: str | None = None
    conversation_id: str | None = None
    execution_id: int | None = None
    allowed_tools: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)


class AgentDefinition(ABC):
    """Reusable base interface for deterministic, workspace-scoped agent definitions."""

    id: str = 'base-agent'
    name: str = 'base-agent'
    description: str = 'Base agent placeholder.'
    version: str = '1.0.0'
    input_schema: type[BaseModel] | None = None
    output_schema: type[BaseModel] | None = None
    tools: tuple[str, ...] = ()
    required_permissions: tuple[str, ...] = ()
    workspace_access_required: bool = True

    def validate_input(self, payload: dict[str, Any]) -> BaseModel | dict[str, Any]:
        if self.input_schema is None:
            return payload
        try:
            return self.input_schema.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f'Invalid input for {self.name}: {exc}') from exc

    def validate_output(self, payload: dict[str, Any]) -> BaseModel | dict[str, Any]:
        if self.output_schema is None:
            return payload
        try:
            return self.output_schema.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f'Invalid output for {self.name}: {exc}') from exc

    def validate_tools(self, allowed_tools: Sequence[str] | None) -> list[str]:
        requested = list(allowed_tools) if allowed_tools is not None else list(self.tools)
        if not requested:
            return []
        disallowed = [tool_id for tool_id in requested if tool_id not in set(self.tools)]
        if disallowed:
            raise PermissionError(f'Agent {self.name} does not permit tool(s): {disallowed}')
        return requested

    def resolve_allowed_tools(self, registry: object | None = None) -> list[str]:
        if not self.tools:
            return []
        if registry is None:
            return list(self.tools)
        resolved: list[str] = []
        for tool_id in self.tools:
            if not getattr(registry, 'exists', lambda _tool_id: False)(tool_id):
                raise KeyError(f'Tool {tool_id} is not registered for agent {self.name}.')
            resolved.append(tool_id)
        return resolved

    @abstractmethod
    async def execute(self, payload: dict[str, Any], context: AgentContext | None = None) -> dict[str, Any]:
        raise NotImplementedError('Concrete agent implementation is required.')


class Tool(ABC):
    """Reusable tool abstraction with explicit validation and permission gates."""

    id: str = 'tool'
    name: str = 'tool'
    description: str = 'Generic tool.'
    input_schema: type[BaseModel] | None = None
    output_schema: type[BaseModel] | None = None
    permissions: tuple[str, ...] = ()

    def validate_input(self, payload: dict[str, Any]) -> BaseModel | dict[str, Any]:
        if self.input_schema is None:
            return payload
        try:
            return self.input_schema.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f'Invalid input for tool {self.name}: {exc}') from exc

    def validate_output(self, payload: dict[str, Any]) -> BaseModel | dict[str, Any]:
        if self.output_schema is None:
            return payload
        try:
            return self.output_schema.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f'Invalid output for tool {self.name}: {exc}') from exc

    def check_permissions(self, context: AgentContext | None = None) -> None:
        if context is None:
            return
        if context.allowed_tools and self.id not in context.allowed_tools:
            raise PermissionError(f'Tool {self.id} is not allowed in this execution context.')

    async def execute(self, payload: dict[str, Any], context: AgentContext | None = None) -> dict[str, Any]:
        raise NotImplementedError('Concrete tool implementation is required.')

    async def run(self, payload: dict[str, Any], context: AgentContext | None = None) -> dict[str, Any]:
        self.check_permissions(context)
        validated_input = self.validate_input(payload)
        if hasattr(validated_input, 'model_dump'):
            safe_input = validated_input.model_dump()
        else:
            safe_input = dict(validated_input)
        result = await self.execute(safe_input, context)
        self.validate_output(result)
        return result


class Agent(AgentDefinition):
    """Backward-compatible alias for the existing agent interface."""

    pass
