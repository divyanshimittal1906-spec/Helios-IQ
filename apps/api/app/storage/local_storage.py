from __future__ import annotations

import re
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.storage.base import BaseDocumentStorage, StorageError


class LocalDocumentStorage(BaseDocumentStorage):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.root_dir = Path(self.settings.document_storage_path)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _safe_name(self, file_name: str) -> str:
        name = file_name.strip()
        if not name:
            raise StorageError('Filename is required.')

        safe_name = Path(name).name
        if safe_name in {'.', '..'} or not safe_name:
            raise StorageError('Filename is invalid.')

        safe_name = re.sub(r'[^A-Za-z0-9._-]+', '_', safe_name)
        safe_name = safe_name.strip('._')
        if not safe_name:
            raise StorageError('Filename is invalid.')
        return safe_name

    def save(self, knowledge_base_id: int, file_name: str, content: bytes) -> dict[str, str | int]:
        safe_name = self._safe_name(file_name)
        target_dir = self.root_dir / str(knowledge_base_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        unique_name = f'{uuid.uuid4().hex}_{safe_name}'
        target_path = target_dir / unique_name
        target_path.write_bytes(content)
        return {
            'storage_path': str(target_path),
            'file_name': safe_name,
            'size': len(content),
        }

    def delete(self, storage_path: str) -> None:
        target_path = Path(storage_path)
        if target_path.exists():
            target_path.unlink()

    def read(self, storage_path: str) -> bytes:
        target_path = Path(storage_path)
        if not target_path.exists() or not target_path.is_file():
            raise StorageError('Stored document file is missing.')
        return target_path.read_bytes()
