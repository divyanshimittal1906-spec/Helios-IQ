from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.agents.base import AgentContext
from app.ai.agents.content_agent import ContentAgent, get_content_agent_registry
from app.ai.agents.service import AgentExecutionService
from app.api.dependencies import get_current_user_id, get_db, require_workspace_access
from app.schemas.content import ContentGenerationRequest, ContentGenerationResponse

router = APIRouter(prefix='/content', tags=['content'])


@router.post('/generate', response_model=ContentGenerationResponse, status_code=status.HTTP_200_OK)
def generate_content(
    payload: ContentGenerationRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ContentGenerationResponse:
    require_workspace_access(db, user_id, payload.workspace_id)

    registry = get_content_agent_registry()
    if not registry.exists('content-agent'):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Content agent is not registered.')

    service = AgentExecutionService(db, registry=registry)
    execution = service.create_execution(
        user_id=user_id,
        workspace_id=payload.workspace_id,
        agent_id='content-agent',
        input_payload=payload.model_dump(mode='json'),
        allowed_tools=[],
    )

    context = AgentContext(
        user_id=user_id,
        workspace_id=payload.workspace_id,
        execution_id=execution.id,
        allowed_tools=[],
        config={'db': db},
    )

    result = service.execute_agent_execution(execution, payload=payload.model_dump(mode='json'), context=context)
    return ContentGenerationResponse(**result)
