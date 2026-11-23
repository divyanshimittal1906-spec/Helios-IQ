from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_workspace_access
from app.db.models import Conversation, Message
from app.repositories.workspace_repository import ConversationRepository, MessageRepository

VALID_MESSAGE_ROLES = {'user', 'assistant', 'system'}
MAX_TITLE_LENGTH = 255


class ConversationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.conversation_repository = ConversationRepository(session)
        self.message_repository = MessageRepository(session)

    @staticmethod
    def _normalize_text(value: str | None, *, allow_blank: bool = False) -> str | None:
        if value is None:
            return None
        normalized = ' '.join(value.split())
        if not normalized and not allow_blank:
            return None
        return normalized

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _truncate_title(value: str, *, limit: int = MAX_TITLE_LENGTH) -> str:
        normalized = ' '.join(value.split())
        if len(normalized) <= limit:
            return normalized
        return normalized[:limit].rstrip()

    @staticmethod
    def _derive_title_from_message(content: str) -> str:
        normalized = ConversationService._normalize_text(content)
        if not normalized:
            return 'New conversation'
        return ConversationService._truncate_title(normalized)

    def _assert_workspace_access(self, user_id: int, workspace_id: int) -> None:
        require_workspace_access(self.session, user_id, workspace_id)

    def _get_conversation_for_workspace(self, user_id: int, conversation_id: int, workspace_id: int) -> Conversation:
        self._assert_workspace_access(user_id, workspace_id)
        conversation = self.session.get(Conversation, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Conversation not found.')
        if conversation.workspace_id != workspace_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Conversation does not belong to this workspace.')
        return conversation

    def create_conversation(self, user_id: int, *, workspace_id: int, title: str | None = None, initial_message: str | None = None) -> Conversation:
        self._assert_workspace_access(user_id, workspace_id)

        if title is not None:
            safe_title = self._normalize_text(title)
            if not safe_title:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Conversation title cannot be empty.')
            final_title = self._truncate_title(safe_title)
        elif initial_message is not None:
            safe_message = self._normalize_text(initial_message)
            if not safe_message:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Initial message cannot be empty.')
            final_title = self._derive_title_from_message(safe_message)
        else:
            final_title = 'New conversation'

        conversation = Conversation(
            workspace_id=workspace_id,
            user_id=user_id,
            title=final_title,
        )

        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)

        if initial_message is not None:
            message = self._add_message_internal(
                conversation,
                role='user',
                content=initial_message,
                user_id=user_id,
                metadata={'source': 'initial_message'},
            )
            self.session.add(message)
            self.session.commit()
            self.session.refresh(message)
            conversation.updated_at = self._normalize_datetime(datetime.now(timezone.utc))
            self.session.add(conversation)
            self.session.commit()
            self.session.refresh(conversation)

        return conversation

    def list_conversations(self, user_id: int, workspace_id: int) -> list[Conversation]:
        self._assert_workspace_access(user_id, workspace_id)
        return self.conversation_repository.list_for_workspace_ordered(workspace_id)

    def get_conversation(self, user_id: int, conversation_id: int, workspace_id: int) -> Conversation:
        return self._get_conversation_for_workspace(user_id, conversation_id, workspace_id)

    def add_message(self, user_id: int, *, conversation_id: int, workspace_id: int, role: str, content: str, metadata: dict[str, Any] | None = None) -> Message:
        conversation = self._get_conversation_for_workspace(user_id, conversation_id, workspace_id)
        normalized_role = str(role or '').strip().lower()
        if normalized_role not in VALID_MESSAGE_ROLES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid message role.')

        normalized_content = self._normalize_text(content)
        if normalized_content is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Message content cannot be empty.')
        if len(normalized_content) > 20000:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Message content is too large.')

        message = self._add_message_internal(
            conversation,
            role=normalized_role,
            content=normalized_content,
            user_id=user_id,
            metadata=metadata,
        )
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)

        current_updated_at = self._normalize_datetime(conversation.updated_at)
        conversation.updated_at = max(datetime.now(timezone.utc), current_updated_at + timedelta(seconds=1))
        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)
        return message

    def _add_message_internal(
        self,
        conversation: Conversation,
        *,
        role: str,
        content: str,
        user_id: int | None,
        metadata: dict[str, Any] | None,
    ) -> Message:
        return Message(
            workspace_id=conversation.workspace_id,
            conversation_id=conversation.id,
            user_id=user_id,
            role=role,
            content=content,
            message_metadata=metadata,
        )

    def list_messages(self, user_id: int, *, conversation_id: int, workspace_id: int) -> list[Message]:
        conversation = self._get_conversation_for_workspace(user_id, conversation_id, workspace_id)
        return self.message_repository.list_for_conversation(conversation.id, workspace_id)

    def ensure_title_for_conversation(self, conversation: Conversation) -> None:
        if conversation.title and conversation.title.strip():
            return
        latest_user_message = self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id, Message.role == 'user')
            .order_by(Message.created_at.asc(), Message.id.asc())
            .limit(1)
        ).scalar_one_or_none()
        if latest_user_message is None:
            conversation.title = 'New conversation'
        else:
            conversation.title = self._derive_title_from_message(latest_user_message.content)
        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)
