from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id, get_db
from app.schemas.orchestration import OrchestrationDecision, OrchestrationRequest, OrchestrationResponse
from app.services.orchestration_service import AIOrchestrator, execute_orchestration_request, route_orchestration_request

router = APIRouter(prefix='/orchestration', tags=['orchestration'])


@router.post('/route', response_model=OrchestrationDecision, status_code=status.HTTP_200_OK)
def route_request(
    payload: OrchestrationRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> OrchestrationDecision:
    try:
        return route_orchestration_request(payload, user_id=user_id, db=db)
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post('/execute', response_model=OrchestrationResponse, status_code=status.HTTP_200_OK)
def execute_request(
    payload: OrchestrationRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> OrchestrationResponse:
    try:
        return execute_orchestration_request(payload, user_id=user_id, db=db)
    except (PermissionError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
