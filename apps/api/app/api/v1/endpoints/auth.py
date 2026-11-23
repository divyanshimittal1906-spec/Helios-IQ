from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.core.config import get_settings
from app.core.security import (
    SecurityError,
    TokenExpiredError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models import User
from app.schemas.auth import (
    MessageResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)

router = APIRouter(prefix='/auth', tags=['authentication'])


@router.post('/register', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserRegister,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Register a new user account with secure password hashing."""
    existing_user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='An account with this email already exists.',
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.post('/login', response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(
    payload: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate user credentials, establish HttpOnly cookie session, and return access token."""
    settings = get_settings()
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid email or password.',
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Account is inactive.',
        )

    access_token = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id, user.email)

    access_expire_seconds = settings.access_token_expire_minutes * 60
    refresh_expire_seconds = settings.refresh_token_expire_days * 86400

    response.set_cookie(
        key='access_token',
        value=access_token,
        httponly=True,
        secure=settings.is_cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=access_expire_seconds,
        path='/',
    )
    response.set_cookie(
        key='refresh_token',
        value=refresh_token,
        httponly=True,
        secure=settings.is_cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=refresh_expire_seconds,
        path='/api/auth',
    )

    return TokenResponse(
        access_token=access_token,
        token_type='bearer',
        expires_in=access_expire_seconds,
        user=UserResponse.model_validate(user),
    )


@router.post('/logout', response_model=MessageResponse, status_code=status.HTTP_200_OK)
def logout(response: Response) -> MessageResponse:
    """Clear authentication cookies."""
    response.delete_cookie(key='access_token', path='/')
    response.delete_cookie(key='refresh_token', path='/api/auth')
    response.delete_cookie(key='refresh_token', path='/')
    return MessageResponse(message='Successfully logged out.')


@router.post('/refresh', response_model=TokenResponse, status_code=status.HTTP_200_OK)
def refresh_token_endpoint(
    request: Request,
    response: Response,
    payload: RefreshTokenRequest | None = None,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Validate refresh token and issue a fresh access token."""
    settings = get_settings()

    raw_token: str | None = None
    if payload and payload.refresh_token:
        raw_token = payload.refresh_token.strip()
    if not raw_token:
        cookie_token = request.cookies.get('refresh_token')
        if cookie_token and cookie_token.strip():
            raw_token = cookie_token.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Refresh token required.',
        )

    try:
        claims = decode_token(raw_token, expected_type='refresh')
        user_id = int(claims['sub'])
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Refresh token has expired. Please log in again.',
        ) from exc
    except (SecurityError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid refresh token.',
        ) from exc

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User account not found.',
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='User account is inactive.',
        )

    new_access_token = create_access_token(user.id, user.email)
    new_refresh_token = create_refresh_token(user.id, user.email)

    access_expire_seconds = settings.access_token_expire_minutes * 60
    refresh_expire_seconds = settings.refresh_token_expire_days * 86400

    response.set_cookie(
        key='access_token',
        value=new_access_token,
        httponly=True,
        secure=settings.is_cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=access_expire_seconds,
        path='/',
    )
    response.set_cookie(
        key='refresh_token',
        value=new_refresh_token,
        httponly=True,
        secure=settings.is_cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=refresh_expire_seconds,
        path='/api/auth',
    )

    return TokenResponse(
        access_token=new_access_token,
        token_type='bearer',
        expires_in=access_expire_seconds,
        user=UserResponse.model_validate(user),
    )


@router.get('/me', response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return profile details for the currently authenticated user."""
    return UserResponse.model_validate(current_user)
