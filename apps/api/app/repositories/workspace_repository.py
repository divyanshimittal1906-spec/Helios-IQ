from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Conversation, Document, DocumentChunk, Message, Project, Task, Workspace
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Workspace)


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Project)


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Task)


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Conversation)

    def list_for_workspace_ordered(self, workspace_id: int) -> list[Conversation]:
        stmt = select(Conversation).where(Conversation.workspace_id == workspace_id).order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        return self.session.execute(stmt).scalars().all()


class MessageRepository(BaseRepository[Message]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Message)

    def list_for_conversation(self, conversation_id: int, workspace_id: int) -> list[Message]:
        stmt = select(Message).where(Message.conversation_id == conversation_id, Message.workspace_id == workspace_id).order_by(Message.created_at.asc(), Message.id.asc())
        return self.session.execute(stmt).scalars().all()


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Document)


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, DocumentChunk)
