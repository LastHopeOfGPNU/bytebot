"""API v1 package."""

from fastapi import APIRouter

from .tasks import router as tasks_router
from .messages import router as messages_router
from .summaries import router as summaries_router
from .models import router as models_router

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_router.include_router(messages_router, prefix="/messages", tags=["messages"])
api_router.include_router(summaries_router, prefix="/summaries", tags=["summaries"])
api_router.include_router(models_router, prefix="/models", tags=["models"])

__all__ = ["api_router"]