from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id, get_db, require_workspace_access
from app.schemas.conversation import ConversationCreate, ConversationRead, MessageCreate, MessageRead
from app.services.conversation_service import ConversationService

router = APIRouter(prefix='/conversations', tags=['conversations'])


@router.post('', response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ConversationRead:
    require_workspace_access(db, user_id, payload.workspace_id)
    service = ConversationService(db)
    conversation = service.create_conversation(
        user_id,
        workspace_id=payload.workspace_id,
        title=payload.title,
        initial_message=payload.initial_message,
    )
    return ConversationRead.model_validate(conversation)


@router.get('', response_model=list[ConversationRead])
def list_conversations(
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[ConversationRead]:
    require_workspace_access(db, user_id, workspace_id)
    service = ConversationService(db)
    conversations = service.list_conversations(user_id, workspace_id)
    return [ConversationRead.model_validate(item) for item in conversations]


@router.get('/{conversation_id}', response_model=ConversationRead)
def get_conversation(
    conversation_id: int = Path(..., gt=0),
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ConversationRead:
    service = ConversationService(db)
    conversation = service.get_conversation(user_id, conversation_id, workspace_id)
    return ConversationRead.model_validate(conversation)


@router.post('/{conversation_id}/messages', response_model=MessageRead, status_code=status.HTTP_201_CREATED)
def add_message(
    conversation_id: int = Path(..., gt=0),
    payload: MessageCreate = None,
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> MessageRead:
    if payload is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Message payload is required.')
    service = ConversationService(db)
    message = service.add_message(
        user_id,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        role=payload.role,
        content=payload.content,
        metadata=payload.metadata,
    )
    return MessageRead.model_validate(message)


@router.get('/{conversation_id}/messages', response_model=list[MessageRead])
def list_messages(
    conversation_id: int = Path(..., gt=0),
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[MessageRead]:
    service = ConversationService(db)
    messages = service.list_messages(user_id, conversation_id=conversation_id, workspace_id=workspace_id)
    return [MessageRead.model_validate(item) for item in messages]
