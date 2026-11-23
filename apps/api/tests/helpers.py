from __future__ import annotations

from app.core.security import create_access_token


def auth_header(user_id: int = 1, email: str | None = None) -> dict[str, str]:
    """Generate a valid Authorization header with signed JWT access token for testing."""
    user_email = email or f'user{user_id}@example.com'
    token = create_access_token(user_id, user_email)
    return {'Authorization': f'Bearer {token}'}
