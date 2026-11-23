from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.db.base import Base
from app.db.models import Conversation, Organization, OrganizationMember, User, Workspace
from app.main import app
from app.services.orchestration_service import AIOrchestrator
from tests.helpers import auth_header


@pytest.fixture
def orchestration_session() -> Session:
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session: Session = SessionLocal()

    org = Organization(name='Org One', slug='org-one')
    user = User(email='orchestrator@example.com', password_hash='hash', full_name='Orchestrator User')
    workspace = Workspace(organization_id=1, owner_id=1, name='Workspace One', slug='workspace-one')
    other_workspace = Workspace(organization_id=1, owner_id=1, name='Workspace Two', slug='workspace-two')
    member = OrganizationMember(organization_id=1, user_id=1, role='admin', status='active')
    session.add_all([org, user, workspace, other_workspace, member])
    session.commit()

    conversation = Conversation(workspace_id=workspace.id, user_id=user.id, title='Initial chat')
    session.add(conversation)
    session.commit()

    yield session
    session.close()


def test_orchestrator_routes_research_request(orchestration_session: Session) -> None:
    orchestrator = AIOrchestrator(orchestration_session)
    decision = orchestrator.route_request('Research the latest public findings on AI risk management.', workspace_id=1, user_id=1)

    assert decision.intent == 'RESEARCH'
    assert decision.agent_id == 'research-agent'
    assert decision.supported is True


def test_orchestrator_routes_content_request(orchestration_session: Session) -> None:
    orchestrator = AIOrchestrator(orchestration_session)
    decision = orchestrator.route_request('Write a product description for a solar battery startup.', workspace_id=1, user_id=1)

    assert decision.intent == 'CONTENT'
    assert decision.agent_id == 'content-agent'


def test_orchestrator_routes_data_request(orchestration_session: Session) -> None:
    orchestrator = AIOrchestrator(orchestration_session)
    decision = orchestrator.route_request('Analyze this CSV dataset and calculate statistics.', workspace_id=1, user_id=1)

    assert decision.intent == 'DATA_ANALYSIS'
    assert decision.agent_id == 'data-analyst-agent'


def test_orchestrator_rejects_unsupported_request(orchestration_session: Session) -> None:
    orchestrator = AIOrchestrator(orchestration_session)
    decision = orchestrator.route_request('Tell me a joke about quantum cats.', workspace_id=1, user_id=1)

    assert decision.supported is False
    assert decision.status in {'unsupported', 'ambiguous'}


def test_orchestrator_execution_tracks_completed_result(orchestration_session: Session) -> None:
    orchestrator = AIOrchestrator(orchestration_session)
    response = orchestrator.execute(
        message='Write a blog post about renewable energy adoption.',
        workspace_id=1,
        user_id=1,
    )

    assert response.status == 'completed'
    assert response.agent_id == 'content-agent'
    assert response.execution_id is not None
    assert response.result is not None


def test_orchestrator_rejects_unauthorized_workspace(orchestration_session: Session) -> None:
    orchestrator = AIOrchestrator(orchestration_session)
    with pytest.raises(PermissionError):
        orchestrator.execute(message='Research a topic', workspace_id=999, user_id=1)


def test_orchestrator_validates_conversation_membership(orchestration_session: Session) -> None:
    orchestrator = AIOrchestrator(orchestration_session)
    conversation = orchestration_session.query(Conversation).first()
    with pytest.raises(ValueError):
        orchestrator.execute(
            message='Analyze dataset insights.',
            workspace_id=2,
            user_id=1,
            conversation_id=conversation.id,
        )


def test_orchestrator_redacts_secret_error_message(orchestration_session: Session) -> None:
    orchestrator = AIOrchestrator(orchestration_session)
    response = orchestrator.execute(
        message='Write a blog post about renewable energy adoption.',
        workspace_id=1,
        user_id=1,
        metadata={'context': {'api_key': 'secret-123'}},
    )

    if response.error is not None:
        assert 'secret-123' not in response.error.lower()


def test_orchestration_api_routes_research_request(orchestration_session: Session) -> None:
    def override_get_db():
        yield orchestration_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        response = client.post(
            '/api/orchestration/route',
            json={'message': 'Find sources about climate policy', 'workspace_id': 1},
            headers=auth_header(1, 'orchestrator@example.com'),
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload['intent'] == 'RESEARCH'
        assert payload['agent_id'] == 'research-agent'
    finally:
        app.dependency_overrides.clear()
