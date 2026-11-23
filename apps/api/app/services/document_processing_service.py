from __future__ import annotations

import hashlib
import re
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Document, DocumentChunk, KnowledgeBase, Workspace
from app.services.embedding_service import EmbeddingService, EmbeddingProviderError
from app.storage.local_storage import LocalDocumentStorage


class DocumentProcessingError(RuntimeError):
    pass


class DocumentProcessingService:
    SUPPORTED_EXTENSIONS = {
        '.pdf': {'mime_types': {'application/pdf'}, 'kind': 'pdf'},
        '.txt': {'mime_types': {'text/plain', 'application/octet-stream'}, 'kind': 'txt'},
        '.docx': {'mime_types': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/zip'}, 'kind': 'docx'},
    }

    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()
        self.storage = LocalDocumentStorage()
        self.embedding_service = EmbeddingService(session)

    def _require_knowledge_base(self, user_id: int, workspace_id: int, knowledge_base_id: int) -> KnowledgeBase:
        workspace = self.session.get(Workspace, workspace_id)
        if workspace is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Workspace not found.')

        if workspace.owner_id != user_id:
            from app.db.models import OrganizationMember

            membership = self.session.execute(
                select(OrganizationMember).where(
                    OrganizationMember.organization_id == workspace.organization_id,
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.status == 'active',
                )
            ).scalar_one_or_none()
            if membership is None:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='You do not have access to this workspace.')

        knowledge_base = self.session.get(KnowledgeBase, knowledge_base_id)
        if knowledge_base is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Knowledge base not found.')
        if knowledge_base.workspace_id != workspace_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Knowledge base does not belong to the requested workspace.')
        return knowledge_base

    def _get_document(self, user_id: int, workspace_id: int, knowledge_base_id: int, document_id: int) -> Document:
        self._require_knowledge_base(user_id, workspace_id, knowledge_base_id)
        document = self.session.get(Document, document_id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Document not found.')
        if document.workspace_id != workspace_id or document.knowledge_base_id != knowledge_base_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Document does not belong to the requested knowledge base.')
        return document

    def _validate_upload(self, file_name: str, content: bytes, mime_type: str | None) -> dict[str, str]:
        if not file_name or not file_name.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='File name is required.')

        suffix = Path(file_name).suffix.lower()
        expected = self.SUPPORTED_EXTENSIONS.get(suffix)
        if expected is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unsupported file type. Supported formats: PDF, TXT, DOCX.')

        max_size = self.settings.max_document_size
        if len(content) > max_size:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f'File exceeds the maximum allowed size of {max_size} bytes.')

        if suffix == '.pdf':
            if not content.startswith(b'%PDF'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Uploaded PDF is malformed or unreadable.')
        elif suffix == '.docx':
            if not content.startswith(b'PK'):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Uploaded DOCX is malformed or unreadable.')
        elif suffix == '.txt':
            if b'\x00' in content:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Uploaded TXT file contains invalid binary content.')

        content_type = (mime_type or '').lower()
        if content_type and content_type not in expected['mime_types'] and content_type not in {'application/octet-stream', 'binary/octet-stream'}:
            # We deliberately do not trust client MIME alone, but allow a mismatch when the extension is correct.
            pass

        return {'extension': suffix, 'mime_type': content_type or expected['mime_types'].__iter__().__next__()}

    def _extract_pdf_text(self, content: bytes) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover
            raise DocumentProcessingError('PDF extraction is unavailable because pypdf is not installed.') from exc

        reader = PdfReader(BytesIO(content))
        pages = []
        for page in reader.pages:
            page_text = page.extract_text() or ''
            if page_text:
                pages.append(page_text)
        return '\n\n'.join(pages)

    def _extract_txt_text(self, content: bytes) -> str:
        for encoding in ('utf-8-sig', 'utf-8', 'cp1252', 'latin-1'):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise DocumentProcessingError('TXT file could not be decoded as text.')

    def _extract_docx_text(self, content: bytes) -> str:
        try:
            from docx import Document
        except ImportError as exc:  # pragma: no cover
            raise DocumentProcessingError('DOCX extraction is unavailable because python-docx is not installed.') from exc

        document = Document(BytesIO(content))
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text and paragraph.text.strip()]
        return '\n\n'.join(paragraphs)

    def extract_text(self, file_name: str, content: bytes, mime_type: str | None) -> str:
        suffix = Path(file_name).suffix.lower()
        if suffix == '.pdf':
            text = self._extract_pdf_text(content)
        elif suffix == '.txt':
            text = self._extract_txt_text(content)
        elif suffix == '.docx':
            text = self._extract_docx_text(content)
        else:
            raise DocumentProcessingError('Unsupported document type.')

        if not text or not text.strip():
            raise DocumentProcessingError('No meaningful text could be extracted from the document.')
        return text

    def normalize_text(self, text: str) -> str:
        normalized = text.replace('\r\n', '\n').replace('\r', '\n')
        normalized = normalized.replace('\u00a0', ' ')
        normalized = re.sub(r'\n{3,}', '\n\n', normalized)
        normalized = re.sub(r'[ \t]+', ' ', normalized)
        normalized = re.sub(r'\n +', '\n', normalized)
        normalized = re.sub(r' +\n', '\n', normalized)
        normalized = normalized.strip()
        if not normalized:
            raise DocumentProcessingError('Extracted text is empty after normalization.')
        return normalized

    def chunk_text(self, text: str) -> list[dict[str, object]]:
        chunk_size = self.settings.chunk_size
        chunk_overlap = self.settings.chunk_overlap
        if chunk_overlap >= chunk_size:
            raise ValueError('chunk_overlap must be smaller than chunk_size.')

        chunks: list[dict[str, object]] = []
        step = chunk_size - chunk_overlap
        for index in range(0, len(text), step):
            chunk = text[index:index + chunk_size].strip()
            if not chunk:
                continue
            chunks.append({
                'chunk_index': len(chunks),
                'content': chunk,
                'metadata': {
                    'start_char': index,
                    'end_char': index + len(chunk),
                },
            })
        if not chunks:
            raise DocumentProcessingError('No chunks were produced from the extracted text.')
        return chunks

    def _clear_previous_chunks(self, document_id: int) -> None:
        self.session.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete(synchronize_session=False)

    def upload_document(self, user_id: int, knowledge_base_id: int, workspace_id: int, file_name: str, content: bytes, mime_type: str | None) -> Document:
        self._require_knowledge_base(user_id, workspace_id, knowledge_base_id)
        validation = self._validate_upload(file_name, content, mime_type)
        safe_file_name = Path(file_name).name

        stored = self.storage.save(knowledge_base_id, safe_file_name, content)
        document = Document(
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            created_by=user_id,
            title=Path(safe_file_name).stem or safe_file_name,
            file_name=safe_file_name,
            mime_type=validation['mime_type'],
            storage_path=str(stored['storage_path']),
            checksum=hashlib.sha256(content).hexdigest(),
            status='PENDING',
            document_metadata={
                'file_size': len(content),
                'storage_backend': 'local',
                'content_type': validation['mime_type'],
            },
        )
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)

        try:
            return self.process_document(document.id, user_id, workspace_id, knowledge_base_id)
        except DocumentProcessingError as exc:
            document.status = 'FAILED'
            document.document_metadata = {
                **(document.document_metadata or {}),
                'error': str(exc),
            }
            self.session.add(document)
            self.session.commit()
            self.session.refresh(document)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    def process_document(self, document_id: int, user_id: int, workspace_id: int, knowledge_base_id: int) -> Document:
        document = self._get_document(user_id, workspace_id, knowledge_base_id, document_id)
        document.status = 'PROCESSING'
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)

        try:
            raw_content = self.storage.read(document.storage_path)
            extracted_text = self.extract_text(document.file_name, raw_content, document.mime_type)
            normalized_text = self.normalize_text(extracted_text)
            chunk_payload = self.chunk_text(normalized_text)
            self._clear_previous_chunks(document.id)
            for chunk in chunk_payload:
                self.session.add(
                    DocumentChunk(
                        workspace_id=workspace_id,
                        document_id=document.id,
                        chunk_index=chunk['chunk_index'],
                        content=str(chunk['content']),
                        chunk_metadata=chunk['metadata'],
                    )
                )
            self.session.commit()
            self.embedding_service.generate_document_embeddings(document.id)

            document.status = 'COMPLETED'
            document.extracted_text = normalized_text
            document.document_metadata = {
                **(document.document_metadata or {}),
                'chunks_created': len(chunk_payload),
                'embedding_model': self.settings.embedding_model,
                'embedding_dimension': self.settings.embedding_dimension,
                'error': None,
            }
            self.session.add(document)
            self.session.commit()
            self.session.refresh(document)
            return document
        except (DocumentProcessingError, ValueError, EmbeddingProviderError, RuntimeError) as exc:
            document.status = 'FAILED'
            document.extracted_text = None
            document.document_metadata = {
                **(document.document_metadata or {}),
                'error': str(exc),
            }
            self.session.add(document)
            self.session.commit()
            self.session.refresh(document)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    def list_documents(self, user_id: int, workspace_id: int, knowledge_base_id: int) -> list[Document]:
        self._require_knowledge_base(user_id, workspace_id, knowledge_base_id)
        return self.session.execute(
            select(Document).where(
                Document.workspace_id == workspace_id,
                Document.knowledge_base_id == knowledge_base_id,
            ).order_by(Document.created_at.desc())
        ).scalars().all()

    def get_document(self, user_id: int, workspace_id: int, knowledge_base_id: int, document_id: int) -> Document:
        return self._get_document(user_id, workspace_id, knowledge_base_id, document_id)

    def delete_document(self, user_id: int, workspace_id: int, knowledge_base_id: int, document_id: int) -> None:
        document = self._get_document(user_id, workspace_id, knowledge_base_id, document_id)
        self.session.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete(synchronize_session=False)
        try:
            self.storage.delete(document.storage_path)
        except Exception:
            pass
        self.session.delete(document)
        self.session.commit()

    def reprocess_document(self, user_id: int, workspace_id: int, knowledge_base_id: int, document_id: int) -> Document:
        document = self._get_document(user_id, workspace_id, knowledge_base_id, document_id)
        return self.process_document(document.id, user_id, workspace_id, knowledge_base_id)
