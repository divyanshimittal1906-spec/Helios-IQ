from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.agents.base import AgentContext
from app.ai.agents.research_agent import ResearchRequest, ResearchResponse, get_research_agent_registry
from app.ai.agents.service import AgentExecutionService
from app.api.dependencies import get_current_user_id, get_db, require_workspace_access

router = APIRouter(prefix='/research', tags=['research'])


@router.post('', response_model=ResearchResponse, status_code=status.HTTP_200_OK)
def run_research(
    payload: ResearchRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ResearchResponse:
    require_workspace_access(db, user_id, payload.workspace_id)

    registry = get_research_agent_registry()
    if not registry.exists('research-agent'):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Research agent is not registered.')

    service = AgentExecutionService(db, registry=registry)
    execution = service.create_execution(
        user_id=user_id,
        workspace_id=payload.workspace_id,
        agent_id='research-agent',
        input_payload=payload.model_dump(),
        allowed_tools=['research-search'],
    )

    context = AgentContext(
        user_id=user_id,
        workspace_id=payload.workspace_id,
        allowed_tools=['research-search'],
        config={'db': db},
    )

    result = service.execute_agent_execution(execution, payload=payload.model_dump(), context=context)
    return ResearchResponse(**result)
