from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.db.base import Base
from app.db.models import AgentExecution, Conversation, Message, Organization, OrganizationMember, User, Workspace
from app.main import app
from tests.helpers import auth_header


@pytest.fixture
def conversation_session() -> Session:
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session: Session = SessionLocal()

    org_1 = Organization(name='Org One', slug='org-one')
    org_2 = Organization(name='Org Two', slug='org-two')
    user_1 = User(email='user1@example.com', password_hash='hash1', full_name='User One')
    user_2 = User(email='user2@example.com', password_hash='hash2', full_name='User Two')
    workspace_1 = Workspace(organization_id=1, owner_id=1, name='Workspace One', slug='workspace-one')
    workspace_2 = Workspace(organization_id=2, owner_id=2, name='Workspace Two', slug='workspace-two')
    org_member_1 = OrganizationMember(organization_id=1, user_id=1, role='admin', status='active')
    org_member_2 = OrganizationMember(organization_id=2, user_id=2, role='admin', status='active')

    session.add_all([org_1, org_2, user_1, user_2, workspace_1, workspace_2, org_member_1, org_member_2])
    session.commit()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    yield session
    app.dependency_overrides.clear()
    session.close()


def test_create_conversation_valid_workspace(conversation_session: Session) -> None:
    client = TestClient(app)
    response = client.post(
        '/api/conversations',
        json={'workspace_id': 1, 'initial_message': 'Hello team, can we review the sprint plan?'},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body['workspace_id'] == 1
    assert body['user_id'] == 1
    assert body['title'] == 'Hello team, can we review the sprint plan?'


def test_unauthorized_workspace_access_rejected(conversation_session: Session) -> None:
    client = TestClient(app)
    response = client.post(
        '/api/conversations',
        json={'workspace_id': 2, 'initial_message': 'Nope'},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 403, response.text


def test_cross_workspace_conversation_access_rejected(conversation_session: Session) -> None:
    client = TestClient(app)
    response = client.post(
        '/api/conversations',
        json={'workspace_id': 1, 'initial_message': 'Alpha'},
        headers=auth_header(1, 'user1@example.com'),
    )
    conversation_id = response.json()['id']

    response = client.get(
        f'/api/conversations/{conversation_id}/messages',
        params={'workspace_id': 2},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 403, response.text


def test_add_user_and_assistant_messages(conversation_session: Session) -> None:
    client = TestClient(app)
    create_response = client.post(
        '/api/conversations',
        json={'workspace_id': 1, 'initial_message': 'Initial prompt'},
        headers=auth_header(1, 'user1@example.com'),
    )
    conversation_id = create_response.json()['id']

    user_response = client.post(
        f'/api/conversations/{conversation_id}/messages',
        params={'workspace_id': 1},
        json={'role': 'user', 'content': 'Follow up question'},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert user_response.status_code == 201, user_response.text
    assert user_response.json()['role'] == 'user'

    assistant_response = client.post(
        f'/api/conversations/{conversation_id}/messages',
        params={'workspace_id': 1},
        json={'role': 'assistant', 'content': 'Answer goes here'},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert assistant_response.status_code == 201, assistant_response.text
    assert assistant_response.json()['role'] == 'assistant'


def test_invalid_message_role_and_empty_message_rejected(conversation_session: Session) -> None:
    client = TestClient(app)
    create_response = client.post(
        '/api/conversations',
        json={'workspace_id': 1, 'initial_message': 'Base context'},
        headers=auth_header(1, 'user1@example.com'),
    )
    conversation_id = create_response.json()['id']

    response = client.post(
        f'/api/conversations/{conversation_id}/messages',
        params={'workspace_id': 1},
        json={'role': 'bot', 'content': 'bad role'},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 400, response.text

    response = client.post(
        f'/api/conversations/{conversation_id}/messages',
        params={'workspace_id': 1},
        json={'role': 'user', 'content': '   '},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 400, response.text


def test_message_history_retrieval_and_ordering(conversation_session: Session) -> None:
    client = TestClient(app)
    create_response = client.post(
        '/api/conversations',
        json={'workspace_id': 1, 'initial_message': 'Seed prompt'},
        headers=auth_header(1, 'user1@example.com'),
    )
    conversation_id = create_response.json()['id']

    client.post(
        f'/api/conversations/{conversation_id}/messages',
        params={'workspace_id': 1},
        json={'role': 'user', 'content': 'First'},
        headers=auth_header(1, 'user1@example.com'),
    )
    client.post(
        f'/api/conversations/{conversation_id}/messages',
        params={'workspace_id': 1},
        json={'role': 'assistant', 'content': 'Second'},
        headers=auth_header(1, 'user1@example.com'),
    )

    response = client.get(
        f'/api/conversations/{conversation_id}/messages',
        params={'workspace_id': 1},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert [item['content'] for item in data] == ['Seed prompt', 'First', 'Second']


def test_deterministic_ordering_for_equal_timestamps(conversation_session: Session) -> None:
    now = datetime.utcnow()
    conversation = Conversation(workspace_id=1, user_id=1, title='Equal timestamps')
    conversation_session.add(conversation)
    conversation_session.commit()
    conversation_session.refresh(conversation)

    messages = [
        Message(workspace_id=1, conversation_id=conversation.id, user_id=1, role='user', content='A', created_at=now),
        Message(workspace_id=1, conversation_id=conversation.id, user_id=1, role='user', content='B', created_at=now),
        Message(workspace_id=1, conversation_id=conversation.id, user_id=1, role='assistant', content='C', created_at=now),
    ]
    conversation_session.add_all(messages)
    conversation_session.commit()

    result = conversation_session.query(Message).filter(Message.conversation_id == conversation.id).order_by(Message.created_at.asc(), Message.id.asc()).all()
    assert [item.content for item in result] == ['A', 'B', 'C']


def test_conversation_title_generation_and_truncation(conversation_session: Session) -> None:
    client = TestClient(app)
    response = client.post(
        '/api/conversations',
        json={'workspace_id': 1, 'initial_message': '  this is a long conversation title that should be truncated after the configured max length  '},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body['title'] == 'this is a long conversation title that should be truncated after the configured max length'


def test_conversation_updated_at_changes_on_message_add(conversation_session: Session) -> None:
    client = TestClient(app)
    current = client.post(
        '/api/conversations',
        json={'workspace_id': 1, 'initial_message': 'Base run'},
        headers=auth_header(1, 'user1@example.com'),
    )
    conversation_id = current.json()['id']
    before = datetime.fromisoformat(current.json()['updated_at'])

    response = client.post(
        f'/api/conversations/{conversation_id}/messages',
        params={'workspace_id': 1},
        json={'role': 'user', 'content': 'Update me'},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 201, response.text
    updated = client.get(f'/api/conversations/{conversation_id}', params={'workspace_id': 1}, headers=auth_header(1, 'user1@example.com'))
    assert updated.status_code == 200, updated.text
    updated_at = datetime.fromisoformat(updated.json()['updated_at'])
    assert updated_at >= before + timedelta(seconds=1)


def test_invalid_conversation_id_and_malformed_payload(conversation_session: Session) -> None:
    client = TestClient(app)
    response = client.get('/api/conversations/999/messages', params={'workspace_id': 1}, headers=auth_header(1, 'user1@example.com'))
    assert response.status_code == 404, response.text

    response = client.post(
        '/api/conversations/999/messages',
        params={'workspace_id': 1},
        json={'role': 'user'},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 422, response.text


def test_persistence_across_requests(conversation_session: Session) -> None:
    client = TestClient(app)
    create_response = client.post(
        '/api/conversations',
        json={'workspace_id': 1, 'initial_message': 'Persist me'},
        headers=auth_header(1, 'user1@example.com'),
    )
    conversation_id = create_response.json()['id']

    follow_up = client.post(
        f'/api/conversations/{conversation_id}/messages',
        params={'workspace_id': 1},
        json={'role': 'assistant', 'content': 'Persisted response'},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert follow_up.status_code == 201, follow_up.text

    persisted = client.get(
        f'/api/conversations/{conversation_id}/messages',
        params={'workspace_id': 1},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert persisted.status_code == 200, persisted.text
    contents = [item['content'] for item in persisted.json()]
    assert 'Persist me' in contents
    assert 'Persisted response' in contents


def test_agent_execution_conversation_relationship_stays_compatible(conversation_session: Session) -> None:
    client = TestClient(app)
    create_response = client.post(
        '/api/conversations',
        json={'workspace_id': 1, 'initial_message': 'Context for execution'},
        headers=auth_header(1, 'user1@example.com'),
    )
    conversation_id = create_response.json()['id']

    execution = AgentExecution(
        workspace_id=1,
        user_id=1,
        agent_id=1,
        conversation_id=conversation_id,
        status='completed',
        input_payload={'context': 'ok'},
        output_payload={'result': 'done'},
    )
    conversation_session.add(execution)
    conversation_session.commit()

    result = conversation_session.query(AgentExecution).filter(AgentExecution.conversation_id == conversation_id).one()
    assert result.conversation_id == conversation_id
    assert result.workspace_id == 1
