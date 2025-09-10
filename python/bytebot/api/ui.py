"""API router for UI backend service."""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..ui import ui_server
from ..core.logging import get_logger

logger = get_logger(__name__)

# Create router
ui_router = APIRouter(prefix="/ui", tags=["ui"])


class UIStatusResponse(BaseModel):
    """UI server status response."""
    status: str
    agent_base_url: str
    desktop_vnc_url: str
    static_dir: str | None
    websocket_connections: int
    http_client_initialized: bool


class UIConfigRequest(BaseModel):
    """UI server configuration request."""
    agent_base_url: str | None = None
    desktop_vnc_url: str | None = None
    static_dir: str | None = None


@ui_router.get("/status", response_model=UIStatusResponse)
async def get_ui_status():
    """Get UI server status."""
    try:
        status_data = ui_server.get_status()
        return UIStatusResponse(**status_data)
    except Exception as e:
        logger.error(f"Failed to get UI status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get UI status: {str(e)}",
        )


@ui_router.post("/start")
async def start_ui_server():
    """Start the UI server."""
    try:
        await ui_server.start()
        return {"message": "UI server started successfully"}
    except Exception as e:
        logger.error(f"Failed to start UI server: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start UI server: {str(e)}",
        )


@ui_router.post("/stop")
async def stop_ui_server():
    """Stop the UI server."""
    try:
        await ui_server.stop()
        return {"message": "UI server stopped successfully"}
    except Exception as e:
        logger.error(f"Failed to stop UI server: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop UI server: {str(e)}",
        )


@ui_router.post("/restart")
async def restart_ui_server():
    """Restart the UI server."""
    try:
        await ui_server.stop()
        await ui_server.start()
        return {"message": "UI server restarted successfully"}
    except Exception as e:
        logger.error(f"Failed to restart UI server: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart UI server: {str(e)}",
        )


@ui_router.get("/health")
async def ui_health_check():
    """Health check for UI server."""
    try:
        status_data = ui_server.get_status()
        is_healthy = (
            status_data.get("status") == "running" and
            status_data.get("http_client_initialized", False)
        )
        
        if is_healthy:
            return {
                "status": "healthy",
                "message": "UI server is running normally",
            }
        else:
            return {
                "status": "unhealthy",
                "message": "UI server is not properly initialized",
            }
    except Exception as e:
        logger.error(f"UI health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"UI health check failed: {str(e)}",
        )


@ui_router.get("/connections")
async def get_websocket_connections():
    """Get active WebSocket connections."""
    try:
        status_data = ui_server.get_status()
        return {
            "total_connections": status_data.get("websocket_connections", 0),
            "connection_types": ["tasks", "websockify"],  # Available connection types
        }
    except Exception as e:
        logger.error(f"Failed to get WebSocket connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get WebSocket connections: {str(e)}",
        )