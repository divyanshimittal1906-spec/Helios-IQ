from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import uuid

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError, PyJWTError

from app.core.config import get_settings

_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=1,
    hash_len=32,
    salt_len=16,
)


class SecurityError(Exception):
    """Base exception for authentication and token validation errors."""


class TokenExpiredError(SecurityError):
    """Raised when a token signature is valid but expired."""


class InvalidTokenClaimsError(SecurityError):
    """Raised when token claims are malformed, missing, or have wrong type."""


def hash_password(password: str) -> str:
    """Securely hash a plaintext password using Argon2id."""
    if not password:
        raise ValueError('Password cannot be empty.')
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against an Argon2 hash.
    
    Returns False on mismatch, invalid hash format, or corrupt data.
    Never raises an exception on invalid credentials.
    """
    if not password or not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception:
        return False


def create_access_token(
    user_id: int,
    email: str,
    *,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload: dict[str, Any] = {
        'sub': str(user_id),
        'email': email.lower().strip(),
        'type': 'access',
        'iat': int(now.timestamp()),
        'exp': int(expire.timestamp()),
        'jti': str(uuid.uuid4()),
    }
    if extra_claims:
        # Prevent overriding critical claims
        safe_extra = {k: v for k, v in extra_claims.items() if k not in payload}
        payload.update(safe_extra)

    secret = settings.get_jwt_secret()
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    user_id: int,
    email: str,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT refresh token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.refresh_token_expire_days)

    payload: dict[str, Any] = {
        'sub': str(user_id),
        'email': email.lower().strip(),
        'type': 'refresh',
        'iat': int(now.timestamp()),
        'exp': int(expire.timestamp()),
        'jti': str(uuid.uuid4()),
    }

    secret = settings.get_jwt_secret()
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, *, expected_type: str | None = None) -> dict[str, Any]:
    """Decode and validate a signed JWT token.
    
    Validates signature, expiration, required claims ('sub', 'type', 'exp').
    Raises SecurityError subclasses on failure.
    """
    if not token or not isinstance(token, str):
        raise InvalidTokenClaimsError('Missing or malformed token.')

    settings = get_settings()
    secret = settings.get_jwt_secret()

    try:
        payload = jwt.decode(
            token.strip(),
            secret,
            algorithms=[settings.jwt_algorithm],
            options={'require': ['sub', 'type', 'exp', 'iat']},
        )
    except ExpiredSignatureError as exc:
        raise TokenExpiredError('Authentication token has expired.') from exc
    except (InvalidTokenError, PyJWTError) as exc:
        raise InvalidTokenClaimsError('Invalid token signature or payload.') from exc

    if not payload.get('sub'):
        raise InvalidTokenClaimsError('Token missing subject claim.')

    token_type = payload.get('type')
    if expected_type is not None and token_type != expected_type:
        raise InvalidTokenClaimsError(
            f'Invalid token type: expected {expected_type}, got {token_type}.'
        )

    return payload
