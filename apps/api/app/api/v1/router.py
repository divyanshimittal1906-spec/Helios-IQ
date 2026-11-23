from fastapi import APIRouter

from app.api.v1.endpoints.agents import router as agents_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.content import router as content_router
from app.api.v1.endpoints.conversations import router as conversation_router
from app.api.v1.endpoints.data_analysis import router as data_analysis_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.knowledge import router as knowledge_router
from app.api.v1.endpoints.orchestration import router as orchestration_router
from app.api.v1.endpoints.research import router as research_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(agents_router)
api_router.include_router(knowledge_router)
api_router.include_router(research_router)
api_router.include_router(content_router)
api_router.include_router(data_analysis_router)
api_router.include_router(conversation_router)
api_router.include_router(orchestration_router)

