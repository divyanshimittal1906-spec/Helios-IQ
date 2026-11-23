from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.db.base import Base
from app.db.models import KnowledgeBase, Organization, OrganizationMember, User, Workspace
from app.main import app
from tests.helpers import auth_header


@pytest.fixture
def client_and_session():
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
    session.refresh(workspace_1)
    session.refresh(workspace_2)

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield client, session, workspace_1, workspace_2

    app.dependency_overrides.clear()
    session.close()


def test_route_registration(client_and_session):
    client, _session, _workspace_1, _workspace_2 = client_and_session
    paths = {route.path for route in app.routes}
    assert '/api/knowledge' in paths
    assert '/api/knowledge/{knowledge_base_id}' in paths


def test_create_and_list_knowledge_bases(client_and_session):
    client, _session, workspace_1, _workspace_2 = client_and_session

    response = client.post(
        '/api/knowledge',
        json={'workspace_id': workspace_1.id, 'name': 'Research KB', 'description': 'Primary workspace knowledge'},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body['name'] == 'Research KB'

    response = client.get('/api/knowledge', params={'workspace_id': workspace_1.id}, headers=auth_header(1, 'user1@example.com'))
    assert response.status_code == 200, response.text
    items = response.json()
    assert len(items) == 1
    assert items[0]['name'] == 'Research KB'


def test_get_and_update_knowledge_base(client_and_session):
    client, _session, workspace_1, _workspace_2 = client_and_session

    create_response = client.post(
        '/api/knowledge',
        json={'workspace_id': workspace_1.id, 'name': 'Ops KB', 'description': 'Ops notes'},
        headers=auth_header(1, 'user1@example.com'),
    )
    knowledge_base_id = create_response.json()['id']

    response = client.get(
        f'/api/knowledge/{knowledge_base_id}',
        params={'workspace_id': workspace_1.id},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 200, response.text
    assert response.json()['description'] == 'Ops notes'

    response = client.patch(
        f'/api/knowledge/{knowledge_base_id}',
        params={'workspace_id': workspace_1.id},
        json={'name': 'Updated Ops KB', 'description': 'Updated notes'},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 200, response.text
    assert response.json()['name'] == 'Updated Ops KB'


def test_delete_knowledge_base(client_and_session):
    client, _session, workspace_1, _workspace_2 = client_and_session

    create_response = client.post(
        '/api/knowledge',
        json={'workspace_id': workspace_1.id, 'name': 'Delete KB'},
        headers=auth_header(1, 'user1@example.com'),
    )
    knowledge_base_id = create_response.json()['id']

    response = client.delete(
        f'/api/knowledge/{knowledge_base_id}',
        params={'workspace_id': workspace_1.id},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 200, response.text

    response = client.get(
        f'/api/knowledge/{knowledge_base_id}',
        params={'workspace_id': workspace_1.id},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 404


def test_workspace_isolation_blocks_other_workspace(client_and_session):
    client, _session, workspace_1, workspace_2 = client_and_session

    response = client.post(
        '/api/knowledge',
        json={'workspace_id': workspace_2.id, 'name': 'Blocked KB'},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 403, response.text


def test_unauthorized_access_for_other_user(client_and_session):
    client, _session, workspace_1, _workspace_2 = client_and_session

    response = client.post(
        '/api/knowledge',
        json={'workspace_id': workspace_1.id, 'name': 'User Two KB'},
        headers=auth_header(2, 'user2@example.com'),
    )
    assert response.status_code == 403, response.text

    response = client.get('/api/knowledge', params={'workspace_id': workspace_1.id}, headers=auth_header(2, 'user2@example.com'))
    assert response.status_code == 403, response.text


def test_invalid_request_payloads(client_and_session):
    client, _session, workspace_1, _workspace_2 = client_and_session

    response = client.post(
        '/api/knowledge',
        json={'workspace_id': workspace_1.id},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 422, response.text

    response = client.patch(
        f'/api/knowledge/999',
        params={'workspace_id': workspace_1.id},
        json={'name': 'x'},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 404, response.text


def test_duplicate_name_is_rejected(client_and_session):
    client, _session, workspace_1, _workspace_2 = client_and_session

    client.post(
        '/api/knowledge',
        json={'workspace_id': workspace_1.id, 'name': 'Shared KB'},
        headers=auth_header(1, 'user1@example.com'),
    )

    response = client.post(
        '/api/knowledge',
        json={'workspace_id': workspace_1.id, 'name': 'Shared KB'},
        headers=auth_header(1, 'user1@example.com'),
    )
    assert response.status_code == 409, response.text
