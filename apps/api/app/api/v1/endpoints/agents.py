from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id, get_db, require_workspace_access
from app.db.models import Agent, AgentExecution
from app.schemas.agent import AgentExecutionRead, AgentRead

router = APIRouter(prefix='/agents', tags=['agents'])


@router.get('', response_model=list[AgentRead])
def list_agents(
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[AgentRead]:
    require_workspace_access(db, user_id, workspace_id)
    rows = db.execute(select(Agent).where(Agent.workspace_id == workspace_id).order_by(Agent.name.asc())).scalars().all()
    return [
        AgentRead(
            id=agent.id,
            name=agent.name,
            slug=agent.slug,
            description=agent.description,
            provider=agent.provider,
            model_name=agent.model_name,
            status=agent.status,
            workspace_id=agent.workspace_id,
        )
        for agent in rows
    ]


@router.get('/executions', response_model=list[AgentExecutionRead])
def list_executions(
    workspace_id: int = Query(..., gt=0),
    status: str | None = Query(default=None),
    agent_id: int | None = Query(default=None, gt=0),
    conversation_id: int | None = Query(default=None, gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[AgentExecutionRead]:
    require_workspace_access(db, user_id, workspace_id)
    stmt = select(AgentExecution).where(AgentExecution.workspace_id == workspace_id)
    if status is not None:
        stmt = stmt.where(AgentExecution.status == str(status).strip().upper())
    if agent_id is not None:
        stmt = stmt.where(AgentExecution.agent_id == agent_id)
    if conversation_id is not None:
        stmt = stmt.where(AgentExecution.conversation_id == conversation_id)
    stmt = stmt.order_by(AgentExecution.created_at.desc(), AgentExecution.id.desc())
    rows = db.execute(stmt).scalars().all()
    return [
        AgentExecutionRead(
            id=execution.id,
            workspace_id=execution.workspace_id,
            user_id=execution.user_id,
            agent_id=execution.agent_id,
            conversation_id=execution.conversation_id,
            status=execution.status,
            started_at=execution.started_at.isoformat() if execution.started_at else None,
            completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
            duration_ms=execution.duration_ms,
            error_message=execution.error_message,
        )
        for execution in rows
    ]


@router.get('/executions/{execution_id}', response_model=AgentExecutionRead)
def get_execution(
    execution_id: int,
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> AgentExecutionRead:
    require_workspace_access(db, user_id, workspace_id)
    execution = db.get(AgentExecution, execution_id)
    if execution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Execution not found.')
    if execution.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Execution does not belong to this workspace.')
    return AgentExecutionRead(
        id=execution.id,
        workspace_id=execution.workspace_id,
        user_id=execution.user_id,
        agent_id=execution.agent_id,
        conversation_id=execution.conversation_id,
        status=execution.status,
        started_at=execution.started_at.isoformat() if execution.started_at else None,
        completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
        duration_ms=execution.duration_ms,
        error_message=execution.error_message,
    )


@router.get('/{agent_id}', response_model=AgentRead)
def get_agent(
    agent_id: int,
    workspace_id: int = Query(..., gt=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> AgentRead:
    require_workspace_access(db, user_id, workspace_id)
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Agent not found.')
    if agent.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Agent does not belong to this workspace.')
    return AgentRead(
        id=agent.id,
        name=agent.name,
        slug=agent.slug,
        description=agent.description,
        provider=agent.provider,
        model_name=agent.model_name,
        status=agent.status,
        workspace_id=agent.workspace_id,
    )
