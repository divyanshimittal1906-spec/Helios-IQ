from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.ai.agents.base import AgentContext
from app.ai.agents.data_analyst_agent import DataAnalystAgent, get_data_analyst_registry
from app.ai.agents.service import AgentExecutionService
from app.api.dependencies import get_current_user_id, get_db, require_workspace_access
from app.core.config import get_settings
from app.schemas.data_analyst import DataAnalysisResponse

router = APIRouter(prefix='/data', tags=['data'])


@router.post('/analyze', response_model=DataAnalysisResponse, status_code=status.HTTP_200_OK)
async def analyze_dataset(
    file: UploadFile = File(...),
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> DataAnalysisResponse:
    require_workspace_access(db, user_id, workspace_id)

    if file.filename is None or not file.filename.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='A valid dataset filename is required.')

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {'.csv', '.xlsx'}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unsupported dataset type. Only CSV and XLSX files are supported.')

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Uploaded dataset is empty.')

    max_size = get_settings().max_document_size
    if len(content) > max_size:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f'Dataset exceeds the maximum size of {max_size} bytes.')

    registry = get_data_analyst_registry()
    if not registry.exists('data-analyst-agent'):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Data analyst agent is not registered.')

    service = AgentExecutionService(db, registry=registry)
    execution = service.create_execution(
        user_id=user_id,
        workspace_id=workspace_id,
        agent_id='data-analyst-agent',
        input_payload={'filename': file.filename, 'content_type': suffix.lstrip('.'), 'workspace_id': workspace_id},
        allowed_tools=[],
    )

    context = AgentContext(
        user_id=user_id,
        workspace_id=workspace_id,
        execution_id=execution.id,
        allowed_tools=[],
        config={'db': db},
    )

    try:
        result = await service.execute_agent_execution_async(
            execution,
            payload={
                'filename': file.filename,
                'content_type': suffix.lstrip('.'),
                'workspace_id': workspace_id,
                'file_content': content,
            },
            context=context,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return DataAnalysisResponse(**result)
