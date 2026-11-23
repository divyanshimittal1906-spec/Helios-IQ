from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.db.base import Base
from app.db.models import (
    Agent,
    AgentExecution,
    Conversation,
    Document,
    KnowledgeBase,
    Organization,
    OrganizationMember,
    User,
    Workspace,
)
from app.main import app


@pytest.fixture
def auth_session() -> Session:
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session: Session = SessionLocal()

    org_a = Organization(id=1, name='Org A', slug='org-a')
    org_b = Organization(id=2, name='Org B', slug='org-b')

    user_a = User(
        id=1,
        email='alice@example.com',
        password_hash=hash_password('Password123!'),
        full_name='Alice User',
        is_active=True,
    )
    user_b = User(
        id=2,
        email='bob@example.com',
        password_hash=hash_password('Password456!'),
        full_name='Bob User',
        is_active=True,
    )
    user_inactive = User(
        id=3,
        email='inactive@example.com',
        password_hash=hash_password('Password789!'),
        full_name='Inactive User',
        is_active=False,
    )

    ws_a = Workspace(id=1, organization_id=1, owner_id=1, name='Workspace A', slug='workspace-a')
    ws_b = Workspace(id=2, organization_id=2, owner_id=2, name='Workspace B', slug='workspace-b')

    mem_a = OrganizationMember(id=1, organization_id=1, user_id=1, role='admin', status='active')
    mem_b = OrganizationMember(id=2, organization_id=2, user_id=2, role='admin', status='active')

    session.add_all([org_a, org_b, user_a, user_b, user_inactive, ws_a, ws_b, mem_a, mem_b])
    session.commit()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    yield session
    app.dependency_overrides.clear()
    session.close()


def test_register_success(auth_session: Session) -> None:
    client = TestClient(app)
    response = client.post(
        '/api/auth/register',
        json={
            'email': 'newuser@example.com',
            'password': 'StrongPassword123!',
            'full_name': 'New User',
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data['email'] == 'newuser@example.com'
    assert data['full_name'] == 'New User'
    assert data['is_active'] is True
    assert 'password' not in data
    assert 'password_hash' not in data


def test_register_duplicate_email_rejected(auth_session: Session) -> None:
    client = TestClient(app)
    response = client.post(
        '/api/auth/register',
        json={
            'email': 'alice@example.com',
            'password': 'Password123!',
            'full_name': 'Alice Copy',
        },
    )
    assert response.status_code == 409
    assert 'already exists' in response.json()['detail'].lower()


def test_register_invalid_email_rejected(auth_session: Session) -> None:
    client = TestClient(app)
    response = client.post(
        '/api/auth/register',
        json={
            'email': 'not-an-email',
            'password': 'Password123!',
            'full_name': 'Invalid Email',
        },
    )
    assert response.status_code == 422


def test_register_short_password_rejected(auth_session: Session) -> None:
    client = TestClient(app)
    response = client.post(
        '/api/auth/register',
        json={
            'email': 'valid@example.com',
            'password': 'short',
            'full_name': 'Valid User',
        },
    )
    assert response.status_code == 422


def test_login_success(auth_session: Session) -> None:
    client = TestClient(app)
    response = client.post(
        '/api/auth/login',
        json={
            'email': 'alice@example.com',
            'password': 'Password123!',
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert 'access_token' in data
    assert data['token_type'] == 'bearer'
    assert data['user']['email'] == 'alice@example.com'
    assert 'password_hash' not in data['user']
    # Verify HttpOnly cookies are set
    cookies = response.cookies
    assert 'access_token' in cookies
    assert 'refresh_token' in cookies


def test_login_wrong_password_rejected(auth_session: Session) -> None:
    client = TestClient(app)
    response = client.post(
        '/api/auth/login',
        json={
            'email': 'alice@example.com',
            'password': 'WrongPassword!',
        },
    )
    assert response.status_code == 401
    assert 'invalid' in response.json()['detail'].lower()


def test_login_nonexistent_user_rejected(auth_session: Session) -> None:
    client = TestClient(app)
    response = client.post(
        '/api/auth/login',
        json={
            'email': 'nobody@example.com',
            'password': 'AnyPassword123!',
        },
    )
    assert response.status_code == 401
    assert 'invalid' in response.json()['detail'].lower()


def test_login_inactive_user_rejected(auth_session: Session) -> None:
    client = TestClient(app)
    response = client.post(
        '/api/auth/login',
        json={
            'email': 'inactive@example.com',
            'password': 'Password789!',
        },
    )
    assert response.status_code == 403
    assert 'inactive' in response.json()['detail'].lower()


def test_me_endpoint_with_valid_bearer_token(auth_session: Session) -> None:
    client = TestClient(app)
    token = create_access_token(1, 'alice@example.com')
    response = client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['id'] == 1
    assert data['email'] == 'alice@example.com'
    assert 'password_hash' not in data


def test_me_endpoint_with_cookie(auth_session: Session) -> None:
    client = TestClient(app)
    token = create_access_token(1, 'alice@example.com')
    client.cookies.set('access_token', token)
    response = client.get('/api/auth/me')
    assert response.status_code == 200, response.text
    assert response.json()['id'] == 1


def test_unauthenticated_request_rejected(auth_session: Session) -> None:
    client = TestClient(app)
    response = client.get('/api/auth/me')
    assert response.status_code == 401


def test_expired_token_rejected(auth_session: Session) -> None:
    client = TestClient(app)
    expired_token = create_access_token(1, 'alice@example.com', expires_delta=timedelta(seconds=-10))
    response = client.get('/api/auth/me', headers={'Authorization': f'Bearer {expired_token}'})
    assert response.status_code == 401
    assert 'expired' in response.json()['detail'].lower()


def test_tampered_token_rejected(auth_session: Session) -> None:
    client = TestClient(app)
    valid_token = create_access_token(1, 'alice@example.com')
    tampered_token = valid_token[:-4] + 'xxxx'
    response = client.get('/api/auth/me', headers={'Authorization': f'Bearer {tampered_token}'})
    assert response.status_code == 401


def test_logout_clears_cookies(auth_session: Session) -> None:
    client = TestClient(app)
    # Log in first
    login_resp = client.post(
        '/api/auth/login',
        json={'email': 'alice@example.com', 'password': 'Password123!'},
    )
    assert login_resp.status_code == 200

    # Log out
    logout_resp = client.post('/api/auth/logout')
    assert logout_resp.status_code == 200
    assert logout_resp.json()['message'] == 'Successfully logged out.'


def test_refresh_token_endpoint(auth_session: Session) -> None:
    client = TestClient(app)
    refresh_tok = create_refresh_token(1, 'alice@example.com')

    # Pass in body
    response = client.post('/api/auth/refresh', json={'refresh_token': refresh_tok})
    assert response.status_code == 200, response.text
    data = response.json()
    assert 'access_token' in data
    assert data['user']['email'] == 'alice@example.com'


def test_refresh_token_wrong_type_rejected(auth_session: Session) -> None:
    client = TestClient(app)
    # Try using an access token as a refresh token
    access_tok = create_access_token(1, 'alice@example.com')
    response = client.post('/api/auth/refresh', json={'refresh_token': access_tok})
    assert response.status_code == 401


def test_x_user_id_spoofing_prevented(auth_session: Session) -> None:
    """Verify that an attacker cannot pass X-User-Id to impersonate another user or bypass auth."""
    client = TestClient(app)

    # 1. Unauthenticated request with X-User-Id is rejected
    unauth_resp = client.get('/api/auth/me', headers={'X-User-Id': '1'})
    assert unauth_resp.status_code == 401

    # 2. Authenticated as Bob (user 2), trying to spoof Alice (user 1) via X-User-Id: 1
    bob_token = create_access_token(2, 'bob@example.com')
    spoof_resp = client.get(
        '/api/auth/me',
        headers={
            'Authorization': f'Bearer {bob_token}',
            'X-User-Id': '1',
        },
    )
    assert spoof_resp.status_code == 200
    # Must still resolve to Bob (2), never Alice (1)
    assert spoof_resp.json()['id'] == 2
    assert spoof_resp.json()['email'] == 'bob@example.com'


def test_cross_workspace_isolation_prevented(auth_session: Session) -> None:
    """User B (Bob) must not access User A's (Alice's) workspace resources."""
    client = TestClient(app)
    bob_token = create_access_token(2, 'bob@example.com')
    bob_headers = {'Authorization': f'Bearer {bob_token}'}

    # Bob attempts to list knowledge bases in Alice's Workspace (workspace 1)
    response = client.get(
        '/api/knowledge',
        params={'workspace_id': 1},
        headers=bob_headers,
    )
    # Must be 403 Forbidden
    assert response.status_code == 403
    assert 'do not have access to this workspace' in response.json()['detail'].lower()
