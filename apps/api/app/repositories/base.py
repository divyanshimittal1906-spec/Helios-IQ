from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

ModelType = TypeVar('ModelType')


class BaseRepository(Generic[ModelType]):
    model_type: type[ModelType]

    def __init__(self, session: Session, model_type: type[ModelType]) -> None:
        self.session = session
        self.model_type = model_type

    def get_by_id(self, resource_id: int) -> ModelType | None:
        return self.session.get(self.model_type, resource_id)

    def list_for_workspace(self, workspace_id: int) -> list[ModelType]:
        stmt: Select[tuple[ModelType]] = select(self.model_type).where(self.model_type.workspace_id == workspace_id)
        return self.session.execute(stmt).scalars().all()

    def get_for_workspace(self, workspace_id: int, resource_id: int) -> ModelType:
        resource = self.get_by_id(resource_id)
        if resource is None:
            raise LookupError(f'{self.model_type.__name__} {resource_id} does not exist.')
        if getattr(resource, 'workspace_id', None) != workspace_id:
            raise PermissionError('Resource does not belong to the requested workspace.')
        return resource
