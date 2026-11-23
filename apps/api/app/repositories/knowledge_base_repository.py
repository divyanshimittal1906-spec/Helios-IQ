from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.knowledge import KnowledgeBase
from app.repositories.base import BaseRepository


class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, KnowledgeBase)

    def list_by_workspace(self, workspace_id: int) -> list[KnowledgeBase]:
        return self.session.execute(
            select(KnowledgeBase).where(KnowledgeBase.workspace_id == workspace_id).order_by(KnowledgeBase.created_at.desc())
        ).scalars().all()

    def get_by_name(self, workspace_id: int, name: str) -> KnowledgeBase | None:
        normalized_name = name.strip()
        return self.session.execute(
            select(KnowledgeBase).where(KnowledgeBase.workspace_id == workspace_id, KnowledgeBase.name == normalized_name)
        ).scalar_one_or_none()

    def get_for_workspace(self, workspace_id: int, knowledge_base_id: int) -> KnowledgeBase:
        item = self.session.get(KnowledgeBase, knowledge_base_id)
        if item is None:
            raise LookupError('Knowledge base not found.')
        if item.workspace_id != workspace_id:
            raise PermissionError('Knowledge base does not belong to the requested workspace.')
        return item
