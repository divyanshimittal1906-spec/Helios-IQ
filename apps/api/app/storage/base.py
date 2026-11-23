from __future__ import annotations

from abc import ABC, abstractmethod


class StorageError(RuntimeError):
    pass


class BaseDocumentStorage(ABC):
    @abstractmethod
    def save(self, knowledge_base_id: int, file_name: str, content: bytes) -> dict[str, str | int]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, storage_path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def read(self, storage_path: str) -> bytes:
        raise NotImplementedError
