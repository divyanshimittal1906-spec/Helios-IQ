from __future__ import annotations

from app.ai.agents.base import AgentDefinition, Tool


class AgentRegistry:
    """Registers and resolves AI agents available inside the system."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}

    def register(self, agent: AgentDefinition) -> None:
        agent_id = getattr(agent, 'id', None) or getattr(agent, 'name', None)
        if agent_id in self._agents:
            raise ValueError(f'Agent "{agent_id}" is already registered.')
        self._agents[agent_id] = agent

    def get(self, agent_id: str) -> AgentDefinition:
        if agent_id not in self._agents:
            raise KeyError(f'Agent "{agent_id}" is not registered.')
        return self._agents[agent_id]

    def list(self) -> list[str]:
        return sorted(self._agents.keys())

    def exists(self, agent_id: str) -> bool:
        return agent_id in self._agents


class ToolRegistry:
    """Registers and resolves tools available to deterministic agent executions."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        tool_id = getattr(tool, 'id', None) or getattr(tool, 'name', None)
        if tool_id in self._tools:
            raise ValueError(f'Tool "{tool_id}" is already registered.')
        self._tools[tool_id] = tool

    def get(self, tool_id: str) -> Tool:
        if tool_id not in self._tools:
            raise KeyError(f'Tool "{tool_id}" is not registered.')
        return self._tools[tool_id]

    def list(self) -> list[str]:
        return sorted(self._tools.keys())

    def exists(self, tool_id: str) -> bool:
        return tool_id in self._tools
