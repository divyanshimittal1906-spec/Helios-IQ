from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.agents.base import AgentContext, AgentDefinition, Tool, ToolExecutionError
from app.ai.agents.registry import AgentRegistry, ToolRegistry
from app.ai.agents.service import AgentExecutionService, ExecutionStatus
from app.api.dependencies import get_db
from app.db.base import Base
from app.db.models import Agent, Organization, OrganizationMember, User, Workspace
from app.main import app
from tests.helpers import auth_header


class EchoInput(BaseModel):
    value: str = Field(..., min_length=1)


class EchoOutput(BaseModel):
    result: str


class EchoTool(Tool):
    id = 'echo-tool'
    name = 'echo-tool'
    description = 'Echo a value back to the caller.'
    input_schema = EchoInput
    output_schema = EchoOutput
    permissions = ('workspace:read',)

    async def execute(self, payload: dict[str, object], context: AgentContext | None = None) -> dict[str, object]:
        return {'result': str(payload['value'])}


class SampleAgent(AgentDefinition):
    id = 'sample-agent'
    name = 'sample-agent'
    description = 'Sample framework test agent.'
    version = '1.0.0'
    input_schema = EchoInput
    output_schema = EchoOutput
    tools = ('echo-tool',)
    required_permissions = ('workspace:read',)
    workspace_access_required = True

    async def execute(self, payload: dict[str, object], context: AgentContext | None = None) -> dict[str, object]:
        tool = context.allowed_tools[0] if context and context.allowed_tools else 'echo-tool'
        if tool == 'echo-tool':
            return {'result': str(payload['value'])}
        raise ToolExecutionError('tool_not_allowed', 'Unexpected tool selection.')


@pytest.fixture
def agent_session() -> Session:
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session: Session = SessionLocal()

    org = Organization(name='Org One', slug='org-one')
    user = User(email='user@example.com', password_hash='hash', full_name='User One')
    workspace = Workspace(organization_id=1, owner_id=1, name='Workspace One', slug='workspace-one')
    other_workspace = Workspace(organization_id=1, owner_id=1, name='Workspace Two', slug='workspace-two')
    org_member = OrganizationMember(organization_id=1, user_id=1, role='admin', status='active')
    session.add_all([org, user, workspace, other_workspace, org_member])
    session.commit()

    agent_db = Agent(
        workspace_id=workspace.id,
        name='sample-agent',
        slug='sample-agent',
        description='Persisted sample agent',
        provider='openai',
        model_name='gpt-4o-mini',
        status='active',
        config={},
    )
    session.add(agent_db)
    session.commit()
    yield session
    session.close()


def test_valid_agent_registration() -> None:
    registry = AgentRegistry()
    registry.register(SampleAgent())

    agent = registry.get('sample-agent')
    assert agent.name == 'sample-agent'
    assert registry.exists('sample-agent') is True


def test_duplicate_agent_rejection() -> None:
    registry = AgentRegistry()
    registry.register(SampleAgent())

    with pytest.raises(ValueError, match='already registered'):
        registry.register(SampleAgent())


def test_agent_lookup_and_listing() -> None:
    registry = AgentRegistry()
    registry.register(SampleAgent())

    assert registry.get('sample-agent') is not None
    assert 'sample-agent' in registry.list()


def test_invalid_input_rejection() -> None:
    agent = SampleAgent()
    with pytest.raises(ValueError):
        agent.validate_input({'value': ''})


def test_output_validation() -> None:
    agent = SampleAgent()
    with pytest.raises(ValueError):
        agent.validate_output({'wrong': 'shape'})


def test_tool_registration_and_lookup() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    tool = registry.get('echo-tool')
    assert tool.name == 'echo-tool'
    assert registry.exists('echo-tool') is True


def test_duplicate_tool_rejection() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    with pytest.raises(ValueError, match='already registered'):
        registry.register(EchoTool())


def test_agent_only_receives_declared_tools() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())
    agent = SampleAgent()

    allowed = agent.resolve_allowed_tools(registry)
    assert allowed == ['echo-tool']


def test_execution_status_transitions(agent_session: Session) -> None:
    registry = AgentRegistry()
    registry.register(SampleAgent())

    service = AgentExecutionService(agent_session, registry=registry)
    execution = service.create_execution(user_id=1, workspace_id=1, agent_id='sample-agent', input_payload={'value': 'hello'})

    assert execution.status == ExecutionStatus.PENDING
    service.set_status(execution, ExecutionStatus.RUNNING)
    assert execution.status == ExecutionStatus.RUNNING
    service.set_status(execution, ExecutionStatus.COMPLETED)
    assert execution.status == ExecutionStatus.COMPLETED


def test_failure_sets_failed_status(agent_session: Session) -> None:
    registry = AgentRegistry()
    registry.register(SampleAgent())

    service = AgentExecutionService(agent_session, registry=registry)
    execution = service.create_execution(user_id=1, workspace_id=1, agent_id='sample-agent', input_payload={'value': 'hello'})
    service.mark_failed(execution, 'invalid_input', 'Value was invalid.')

    assert execution.status == ExecutionStatus.FAILED
    assert execution.error_message == 'Value was invalid.'


def test_invalid_execution_state_transition_is_rejected(agent_session: Session) -> None:
    registry = AgentRegistry()
    registry.register(SampleAgent())

    service = AgentExecutionService(agent_session, registry=registry)
    execution = service.create_execution(user_id=1, workspace_id=1, agent_id='sample-agent', input_payload={'value': 'hello'})
    service.set_status(execution, ExecutionStatus.RUNNING)
    service.set_status(execution, ExecutionStatus.COMPLETED)

    with pytest.raises(ValueError, match='Invalid execution transition'):
        service.set_status(execution, ExecutionStatus.RUNNING)


def test_failed_execution_redacts_secrets(agent_session: Session) -> None:
    registry = AgentRegistry()
    registry.register(SampleAgent())

    service = AgentExecutionService(agent_session, registry=registry)
    execution = service.create_execution(user_id=1, workspace_id=1, agent_id='sample-agent', input_payload={'value': 'hello'})
    service.mark_failed(
        execution,
        'auth_error',
        'Authorization: Bearer sk_live_123456; token=abc123',
        metadata={'api_key': 'abc123', 'token': 'secret-value'},
    )

    assert 'sk_live' not in execution.error_message.lower()
    assert 'abc123' not in str(execution.output_payload).lower()
    assert 'secret-value' not in str(execution.output_payload).lower()


def test_execution_history_routes_filter_and_isolate_by_workspace(agent_session: Session) -> None:
    registry = AgentRegistry()
    registry.register(SampleAgent())
    service = AgentExecutionService(agent_session, registry=registry)

    execution_a = service.create_execution(user_id=1, workspace_id=1, agent_id='sample-agent', input_payload={'value': 'a'})
    execution_b = service.create_execution(user_id=1, workspace_id=1, agent_id='sample-agent', input_payload={'value': 'b'})
    service.set_status(execution_a, ExecutionStatus.RUNNING)
    service.set_status(execution_a, ExecutionStatus.COMPLETED)
    service.mark_failed(execution_b, 'validation_error', 'Input invalid.')

    def override_get_db():
        yield agent_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        list_response = client.get('/api/agents/executions', params={'workspace_id': 1, 'status': 'COMPLETED'}, headers=auth_header(1, 'user@example.com'))
        assert list_response.status_code == 200, list_response.text
        assert any(item['id'] == execution_a.id for item in list_response.json())
        assert all(item['status'] == 'COMPLETED' for item in list_response.json())

        execution_response = client.get(f'/api/agents/executions/{execution_a.id}', params={'workspace_id': 1}, headers=auth_header(1, 'user@example.com'))
        assert execution_response.status_code == 200, execution_response.text
        assert execution_response.json()['id'] == execution_a.id

        unauthorized = client.get(f'/api/agents/executions/{execution_a.id}', params={'workspace_id': 2}, headers=auth_header(1, 'user@example.com'))
        assert unauthorized.status_code == 403, unauthorized.text
    finally:
        app.dependency_overrides.clear()


def test_cancellation_behavior(agent_session: Session) -> None:
    registry = AgentRegistry()
    registry.register(SampleAgent())

    service = AgentExecutionService(agent_session, registry=registry)
    execution = service.create_execution(user_id=1, workspace_id=1, agent_id='sample-agent', input_payload={'value': 'hello'})
    service.cancel(execution)

    assert execution.status == ExecutionStatus.CANCELLED


def test_execution_is_persisted_with_timestamps(agent_session: Session) -> None:
    registry = AgentRegistry()
    registry.register(SampleAgent())

    service = AgentExecutionService(agent_session, registry=registry)
    execution = service.create_execution(user_id=1, workspace_id=1, agent_id='sample-agent', input_payload={'value': 'hello'})
    assert execution.started_at is None
    assert execution.created_at is not None


def test_workspace_isolation_prevents_cross_workspace_execution(agent_session: Session) -> None:
    registry = AgentRegistry()
    registry.register(SampleAgent())

    service = AgentExecutionService(agent_session, registry=registry)
    with pytest.raises(PermissionError):
        service.create_execution(user_id=1, workspace_id=999, agent_id='sample-agent', input_payload={'value': 'hello'})


def test_unauthorized_execution_rejected(agent_session: Session) -> None:
    registry = AgentRegistry()
    registry.register(SampleAgent())

    service = AgentExecutionService(agent_session, registry=registry)
    with pytest.raises(PermissionError):
        service.create_execution(user_id=999, workspace_id=1, agent_id='sample-agent', input_payload={'value': 'hello'})


def test_unavailable_agent_rejected(agent_session: Session) -> None:
    registry = AgentRegistry()

    service = AgentExecutionService(agent_session, registry=registry)
    with pytest.raises(KeyError):
        service.create_execution(user_id=1, workspace_id=1, agent_id='missing-agent', input_payload={'value': 'hello'})


def test_disallowed_tool_rejected(agent_session: Session) -> None:
    registry = ToolRegistry()
    registry.register(EchoTool())

    agent = SampleAgent()
    with pytest.raises(PermissionError):
        agent.validate_tools(['other-tool'])


def test_provider_failure_handling(agent_session: Session) -> None:
    class BrokenProviderAgent(SampleAgent):
        id = 'broken-provider-agent'
        name = 'broken-provider-agent'

        async def execute(self, payload: dict[str, object], context: AgentContext | None = None) -> dict[str, object]:
            raise RuntimeError('provider failed')

    registry = AgentRegistry()
    registry.register(BrokenProviderAgent())

    service = AgentExecutionService(agent_session, registry=registry)
    execution = service.create_execution(user_id=1, workspace_id=1, agent_id='broken-provider-agent', input_payload={'value': 'hello'})

    with pytest.raises(RuntimeError):
        service.execute_agent_execution(execution, payload={'value': 'hello'}, context=AgentContext(workspace_id=1, user_id=1, allowed_tools=['echo-tool']))


def test_secrets_are_not_written_to_execution_logs(agent_session: Session) -> None:
    registry = AgentRegistry()
    registry.register(SampleAgent())

    service = AgentExecutionService(agent_session, registry=registry)
    execution = service.create_execution(
        user_id=1,
        workspace_id=1,
        agent_id='sample-agent',
        input_payload={'value': 'hello', 'api_key': 'secret'},
    )
    service.record_safe_metadata(execution, {'payload': {'value': 'hello'}})

    assert 'api_key' not in str(execution.input_payload)
