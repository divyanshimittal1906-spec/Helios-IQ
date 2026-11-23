from collections.abc import Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    SecurityError,
    TokenExpiredError,
    decode_token,
)
from app.db.models import OrganizationMember, User, Workspace
from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def extract_token_from_request(request: Request) -> str | None:
    auth_header = request.headers.get('Authorization')
    if auth_header:
        parts = auth_header.strip().split(' ', 1)
        if len(parts) == 2 and parts[0].lower() == 'bearer':
            token = parts[1].strip()
            if token:
                return token

    cookie_token = request.cookies.get('access_token')
    if cookie_token and cookie_token.strip():
        return cookie_token.strip()

    return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    token = extract_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authentication required.',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    try:
        payload = decode_token(token, expected_type='access')
        user_id_str = payload.get('sub')
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid or expired authentication credential.',
                headers={'WWW-Authenticate': 'Bearer'},
            )
        user_id = int(user_id_str)
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authentication credential has expired.',
            headers={'WWW-Authenticate': 'Bearer'},
        ) from exc
    except (SecurityError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or expired authentication credential.',
            headers={'WWW-Authenticate': 'Bearer'},
        ) from exc

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authenticated user account not found.',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='User account is inactive.',
        )

    return user


def get_current_user_id(current_user: User = Depends(get_current_user)) -> int:
    return current_user.id


def require_workspace_access(session: Session, user_id: int, workspace_id: int | None) -> Workspace:
    if workspace_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='workspace_id is required.')

    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Workspace not found.')

    if workspace.owner_id == user_id:
        return workspace

    membership = session.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == workspace.organization_id,
            OrganizationMember.user_id == user_id,
            OrganizationMember.status == 'active',
        )
    ).scalar_one_or_none()

    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You do not have access to this workspace.')

    return workspace
