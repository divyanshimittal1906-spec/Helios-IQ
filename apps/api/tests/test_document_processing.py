from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.db.base import Base
from app.db.models import Organization, OrganizationMember, User, Workspace
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

    org = Organization(name='Org One', slug='org-one')
    user = User(email='user@example.com', password_hash='hash', full_name='User One')
    workspace = Workspace(organization_id=1, owner_id=1, name='Workspace One', slug='workspace-one')
    org_member = OrganizationMember(organization_id=1, user_id=1, role='admin', status='active')

    session.add_all([org, user, workspace, org_member])
    session.commit()
    session.refresh(workspace)

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield client, session, workspace

    app.dependency_overrides.clear()
    session.close()


def _create_kb(client: TestClient, workspace_id: int) -> int:
    response = client.post(
        '/api/knowledge',
        json={'workspace_id': workspace_id, 'name': 'Ops KB', 'description': 'Operational notes'},
        headers=auth_header(1, 'user@example.com'),
    )
    assert response.status_code == 201, response.text
    return response.json()['id']


def test_upload_txt_document_and_list_documents(client_and_session):
    client, _session, workspace = client_and_session
    knowledge_base_id = _create_kb(client, workspace.id)

    response = client.post(
        f'/api/knowledge/{knowledge_base_id}/documents?workspace_id={workspace.id}',
        files={'file': ('notes.txt', b'Alpha beta gamma delta', 'text/plain')},
        headers=auth_header(1, 'user@example.com'),
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload['file_name'] == 'notes.txt'
    assert payload['status'] == 'COMPLETED'
    assert 'Alpha beta gamma delta' in payload['extracted_text']

    response = client.get(
        f'/api/knowledge/{knowledge_base_id}/documents?workspace_id={workspace.id}',
        headers=auth_header(1, 'user@example.com'),
    )
    assert response.status_code == 200, response.text
    documents = response.json()
    assert len(documents) == 1
    assert documents[0]['title'] == 'notes'


def test_reject_unsupported_document_type(client_and_session):
    client, _session, workspace = client_and_session
    knowledge_base_id = _create_kb(client, workspace.id)

    response = client.post(
        f'/api/knowledge/{knowledge_base_id}/documents?workspace_id={workspace.id}',
        files={'file': ('notes.md', b'# Heading', 'text/markdown')},
        headers=auth_header(1, 'user@example.com'),
    )
    assert response.status_code == 400, response.text
    assert 'Unsupported file type' in response.json()['detail']


def test_delete_document_removes_storage_record(client_and_session):
    client, _session, workspace = client_and_session
    knowledge_base_id = _create_kb(client, workspace.id)

    response = client.post(
        f'/api/knowledge/{knowledge_base_id}/documents?workspace_id={workspace.id}',
        files={'file': ('archive.txt', b'This is a final document.', 'text/plain')},
        headers=auth_header(1, 'user@example.com'),
    )
    document_id = response.json()['id']

    delete_response = client.delete(
        f'/api/knowledge/{knowledge_base_id}/documents/{document_id}?workspace_id={workspace.id}',
        headers=auth_header(1, 'user@example.com'),
    )
    assert delete_response.status_code == 200, delete_response.text

    response = client.get(
        f'/api/knowledge/{knowledge_base_id}/documents/{document_id}?workspace_id={workspace.id}',
        headers=auth_header(1, 'user@example.com'),
    )
    assert response.status_code == 404, response.text
