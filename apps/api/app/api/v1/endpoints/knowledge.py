from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id, get_db
from app.schemas.document import DocumentRead
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseRead, KnowledgeBaseUpdate
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse
from app.services.document_processing_service import DocumentProcessingService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.rag_service import RAGService

router = APIRouter(prefix='/knowledge', tags=['knowledge'])


@router.get('', response_model=list[KnowledgeBaseRead])
def list_knowledge_bases(
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[KnowledgeBaseRead]:
    service = KnowledgeBaseService(db)
    return service.list_knowledge_bases(user_id, workspace_id)


@router.post('', response_model=KnowledgeBaseRead, status_code=status.HTTP_201_CREATED)
def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> KnowledgeBaseRead:
    service = KnowledgeBaseService(db)
    item = service.create_knowledge_base(
        user_id,
        name=payload.name,
        description=payload.description,
        workspace_id=payload.workspace_id,
    )
    return item


@router.get('/{knowledge_base_id}', response_model=KnowledgeBaseRead)
def get_knowledge_base(
    knowledge_base_id: int,
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> KnowledgeBaseRead:
    service = KnowledgeBaseService(db)
    return service.get_knowledge_base(user_id, knowledge_base_id, workspace_id)


@router.patch('/{knowledge_base_id}', response_model=KnowledgeBaseRead)
def update_knowledge_base(
    knowledge_base_id: int,
    payload: KnowledgeBaseUpdate,
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> KnowledgeBaseRead:
    if payload.name is None and payload.description is None and payload.workspace_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='At least one field must be provided for update.')

    service = KnowledgeBaseService(db)
    requested_workspace_id = payload.workspace_id if payload.workspace_id is not None else workspace_id
    if requested_workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='workspace_id in payload does not match the requested workspace.')

    return service.update_knowledge_base(
        user_id,
        knowledge_base_id,
        workspace_id=workspace_id,
        name=payload.name,
        description=payload.description,
    )


@router.delete('/{knowledge_base_id}', status_code=status.HTTP_200_OK)
def delete_knowledge_base(
    knowledge_base_id: int,
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    service = KnowledgeBaseService(db)
    service.delete_knowledge_base(user_id, knowledge_base_id, workspace_id)
    return {'message': 'Knowledge base deleted successfully.'}


@router.post('/{knowledge_base_id}/documents', response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    knowledge_base_id: int,
    workspace_id: int = Query(..., gt=0),
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> DocumentRead:
    if file.filename is None or not file.filename.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='A valid file name is required.')

    contents = await file.read()
    service = DocumentProcessingService(db)
    document = service.upload_document(
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        workspace_id=workspace_id,
        file_name=file.filename,
        content=contents,
        mime_type=file.content_type,
    )
    return document


@router.get('/{knowledge_base_id}/documents', response_model=list[DocumentRead])
def list_documents(
    knowledge_base_id: int,
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[DocumentRead]:
    service = DocumentProcessingService(db)
    return service.list_documents(user_id, workspace_id, knowledge_base_id)


@router.get('/{knowledge_base_id}/documents/{document_id}', response_model=DocumentRead)
def get_document(
    knowledge_base_id: int,
    document_id: int,
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> DocumentRead:
    service = DocumentProcessingService(db)
    return service.get_document(user_id, workspace_id, knowledge_base_id, document_id)


@router.post('/{knowledge_base_id}/documents/{document_id}/reprocess', response_model=DocumentRead)
def reprocess_document(
    knowledge_base_id: int,
    document_id: int,
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> DocumentRead:
    service = DocumentProcessingService(db)
    return service.reprocess_document(user_id, workspace_id, knowledge_base_id, document_id)


@router.delete('/{knowledge_base_id}/documents/{document_id}', status_code=status.HTTP_200_OK)
def delete_document(
    knowledge_base_id: int,
    document_id: int,
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    service = DocumentProcessingService(db)
    service.delete_document(user_id, workspace_id, knowledge_base_id, document_id)
    return {'message': 'Document deleted successfully.'}


@router.post('/{knowledge_base_id}/rag/query', response_model=RAGQueryResponse)
def rag_query(
    knowledge_base_id: int,
    payload: RAGQueryRequest,
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> RAGQueryResponse:
    service = RAGService(db)
    result = service.query(
        user_id=user_id,
        workspace_id=workspace_id,
        knowledge_base_id=knowledge_base_id,
        query_text=payload.query,
        top_k=payload.top_k,
        max_context_chunks=payload.max_context_chunks,
        max_context_tokens=payload.max_context_tokens,
        min_similarity=payload.min_similarity,
    )
    return RAGQueryResponse(**result)
