from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_workspace_access
from app.db.models import OrganizationMember, Workspace
from app.db.models.knowledge import KnowledgeBase
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository


class KnowledgeBaseService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = KnowledgeBaseRepository(session)

    def _ensure_valid_name(self, name: str | None, *, allow_blank: bool = False) -> str | None:
        if name is None:
            return None
        normalized = name.strip()
        if not normalized and not allow_blank:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Name is required.')
        if not normalized:
            return None
        return normalized

    def _assert_access(self, user_id: int, workspace_id: int | None) -> Workspace:
        return require_workspace_access(self.session, user_id, workspace_id)

    def list_knowledge_bases(self, user_id: int, workspace_id: int) -> list[KnowledgeBase]:
        self._assert_access(user_id, workspace_id)
        return self.repository.list_by_workspace(workspace_id)

    def create_knowledge_base(self, user_id: int, *, name: str, description: str | None, workspace_id: int) -> KnowledgeBase:
        self._assert_access(user_id, workspace_id)
        normalized_name = self._ensure_valid_name(name)
        if normalized_name is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Name is required.')

        existing = self.repository.get_by_name(workspace_id, normalized_name)
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='A knowledge base with this name already exists in this workspace.')

        item = KnowledgeBase(
            workspace_id=workspace_id,
            name=normalized_name,
            description=description.strip() if description is not None else None,
            created_by=user_id,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def get_knowledge_base(self, user_id: int, knowledge_base_id: int, workspace_id: int) -> KnowledgeBase:
        self._assert_access(user_id, workspace_id)
        try:
            return self.repository.get_for_workspace(workspace_id, knowledge_base_id)
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    def update_knowledge_base(
        self,
        user_id: int,
        knowledge_base_id: int,
        *,
        workspace_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> KnowledgeBase:
        self._assert_access(user_id, workspace_id)
        item = self.get_knowledge_base(user_id, knowledge_base_id, workspace_id)

        if name is not None:
            normalized_name = self._ensure_valid_name(name)
            if normalized_name is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Name is required.')
            duplicate = self.repository.get_by_name(workspace_id, normalized_name)
            if duplicate is not None and duplicate.id != item.id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='A knowledge base with this name already exists in this workspace.')
            item.name = normalized_name

        if description is not None:
            item.description = description.strip() or None

        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def delete_knowledge_base(self, user_id: int, knowledge_base_id: int, workspace_id: int) -> None:
        self._assert_access(user_id, workspace_id)
        item = self.get_knowledge_base(user_id, knowledge_base_id, workspace_id)
        self.session.delete(item)
        self.session.commit()
