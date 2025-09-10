"""Desktop control API endpoints."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db_session
from ..core.logging import get_logger
from ..desktop import (
    DesktopAction,
    DesktopActionType,
    DesktopResponse,
    DesktopScreenshot,
    DesktopService,
    DesktopWindow,
    MouseButton,
    desktop_service,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/desktop", tags=["desktop"])


# Request/Response models

class DesktopActionRequest(BaseModel):
    """Request model for desktop actions."""
    type: DesktopActionType
    x: Optional[int] = None
    y: Optional[int] = None
    button: Optional[MouseButton] = None
    clicks: Optional[int] = 1
    text: Optional[str] = None
    keys: Optional[List[str]] = None
    window_title: Optional[str] = None
    window_id: Optional[int] = None
    app_name: Optional[str] = None
    app_args: Optional[List[str]] = None
    wait_time: Optional[float] = None
    file_path: Optional[str] = None
    clipboard_text: Optional[str] = None
    
    def to_desktop_action(self) -> DesktopAction:
        """Convert to DesktopAction."""
        return DesktopAction(
            type=self.type,
            x=self.x,
            y=self.y,
            button=self.button,
            clicks=self.clicks,
            text=self.text,
            keys=self.keys,
            window_title=self.window_title,
            window_id=self.window_id,
            app_name=self.app_name,
            app_args=self.app_args or [],
            wait_time=self.wait_time,
            file_path=self.file_path,
            clipboard_text=self.clipboard_text,
        )


class DesktopActionSequenceRequest(BaseModel):
    """Request model for desktop action sequences."""
    actions: List[DesktopActionRequest]
    stop_on_error: bool = True
    delay_between_actions: float = Field(default=0.1, ge=0.0, le=5.0)
    task_id: Optional[UUID] = None


class AutomationScriptRequest(BaseModel):
    """Request model for automation scripts."""
    script_name: str
    actions: List[DesktopActionRequest]


class ExecuteScriptRequest(BaseModel):
    """Request model for executing automation scripts."""
    script_name: str
    parameters: Optional[Dict[str, Any]] = None
    task_id: Optional[UUID] = None


class ClickRequest(BaseModel):
    """Request model for click actions."""
    x: int
    y: int
    button: MouseButton = MouseButton.LEFT
    clicks: int = Field(default=1, ge=1, le=3)
    task_id: Optional[UUID] = None


class TypeTextRequest(BaseModel):
    """Request model for typing text."""
    text: str
    task_id: Optional[UUID] = None


class KeyCombinationRequest(BaseModel):
    """Request model for key combinations."""
    keys: List[str]
    task_id: Optional[UUID] = None


class LaunchAppRequest(BaseModel):
    """Request model for launching applications."""
    app_name: str
    app_args: Optional[List[str]] = None
    task_id: Optional[UUID] = None


class FocusWindowRequest(BaseModel):
    """Request model for focusing windows."""
    window_title: Optional[str] = None
    window_id: Optional[int] = None
    task_id: Optional[UUID] = None


class ScreenshotRequest(BaseModel):
    """Request model for screenshots."""
    task_id: Optional[UUID] = None


class WindowSearchRequest(BaseModel):
    """Request model for window search."""
    title_pattern: Optional[str] = None
    process_name: Optional[str] = None
    exact_match: bool = False


class RecordingRequest(BaseModel):
    """Request model for screen recording."""
    task_id: Optional[UUID] = None


# Response models

class DesktopStatusResponse(BaseModel):
    """Response model for desktop status."""
    connected: bool
    capabilities: Dict[str, Any]
    action_history_size: int
    event_history_size: int
    automation_scripts: List[str]
    active_recordings: List[str]


class DesktopStatisticsResponse(BaseModel):
    """Response model for desktop statistics."""
    total_actions: int
    actions_by_type: Dict[str, int]
    automation_scripts: int
    active_recordings: int
    recent_events: int


# API endpoints

@router.get("/status", response_model=DesktopStatusResponse)
async def get_desktop_status():
    """Get desktop service status."""
    try:
        status_data = desktop_service.get_service_status()
        return DesktopStatusResponse(**status_data)
    except Exception as e:
        logger.error(f"Failed to get desktop status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get desktop status: {str(e)}",
        )


@router.get("/test-connection")
async def test_desktop_connection():
    """Test desktop connection."""
    try:
        connected = await desktop_service.test_connection()
        return {"connected": connected}
    except Exception as e:
        logger.error(f"Desktop connection test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection test failed: {str(e)}",
        )


@router.post("/actions/execute", response_model=DesktopResponse)
async def execute_desktop_action(
    request: DesktopActionRequest,
    task_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    """Execute a single desktop action."""
    try:
        action = request.to_desktop_action()
        response = await desktop_service.execute_action(
            action=action,
            task_id=task_id,
            notify=True,
            db=db,
        )
        return response
    except Exception as e:
        logger.error(f"Desktop action execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Action execution failed: {str(e)}",
        )


@router.post("/actions/execute-sequence", response_model=List[DesktopResponse])
async def execute_desktop_action_sequence(
    request: DesktopActionSequenceRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Execute a sequence of desktop actions."""
    try:
        actions = [action_req.to_desktop_action() for action_req in request.actions]
        responses = await desktop_service.execute_action_sequence(
            actions=actions,
            task_id=request.task_id,
            stop_on_error=request.stop_on_error,
            delay_between_actions=request.delay_between_actions,
            db=db,
        )
        return responses
    except Exception as e:
        logger.error(f"Desktop action sequence execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Action sequence execution failed: {str(e)}",
        )


# High-level action endpoints

@router.post("/click", response_model=DesktopResponse)
async def click_at_position(request: ClickRequest):
    """Click at a specific position."""
    try:
        response = await desktop_service.click_at_position(
            x=request.x,
            y=request.y,
            button=request.button,
            clicks=request.clicks,
            task_id=request.task_id,
        )
        return response
    except Exception as e:
        logger.error(f"Click action failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Click action failed: {str(e)}",
        )


@router.post("/type", response_model=DesktopResponse)
async def type_text(request: TypeTextRequest):
    """Type text at current cursor position."""
    try:
        response = await desktop_service.type_text(
            text=request.text,
            task_id=request.task_id,
        )
        return response
    except Exception as e:
        logger.error(f"Type text action failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Type text action failed: {str(e)}",
        )


@router.post("/key-combination", response_model=DesktopResponse)
async def press_key_combination(request: KeyCombinationRequest):
    """Press a key combination."""
    try:
        response = await desktop_service.press_key_combination(
            keys=request.keys,
            task_id=request.task_id,
        )
        return response
    except Exception as e:
        logger.error(f"Key combination action failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Key combination action failed: {str(e)}",
        )


@router.post("/screenshot", response_model=DesktopResponse)
async def take_screenshot(request: ScreenshotRequest):
    """Take a screenshot of the desktop."""
    try:
        response = await desktop_service.take_screenshot(
            task_id=request.task_id,
        )
        return response
    except Exception as e:
        logger.error(f"Screenshot action failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Screenshot action failed: {str(e)}",
        )


@router.post("/launch-app", response_model=DesktopResponse)
async def launch_application(request: LaunchAppRequest):
    """Launch an application."""
    try:
        response = await desktop_service.launch_application(
            app_name=request.app_name,
            app_args=request.app_args,
            task_id=request.task_id,
        )
        return response
    except Exception as e:
        logger.error(f"Launch application action failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Launch application action failed: {str(e)}",
        )


@router.post("/focus-window", response_model=DesktopResponse)
async def focus_window(request: FocusWindowRequest):
    """Focus a window by title or ID."""
    try:
        response = await desktop_service.focus_window(
            window_title=request.window_title,
            window_id=request.window_id,
            task_id=request.task_id,
        )
        return response
    except Exception as e:
        logger.error(f"Focus window action failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Focus window action failed: {str(e)}",
        )


# Window management endpoints

@router.get("/windows", response_model=List[DesktopWindow])
async def get_windows():
    """Get list of desktop windows."""
    try:
        windows = await desktop_service.get_windows()
        return windows
    except Exception as e:
        logger.error(f"Failed to get windows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get windows: {str(e)}",
        )


@router.get("/windows/active", response_model=Optional[DesktopWindow])
async def get_active_window():
    """Get the currently active window."""
    try:
        window = await desktop_service.get_active_window()
        return window
    except Exception as e:
        logger.error(f"Failed to get active window: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active window: {str(e)}",
        )


@router.post("/windows/search", response_model=List[DesktopWindow])
async def search_windows(request: WindowSearchRequest):
    """Search for windows by title or process name."""
    try:
        if request.title_pattern:
            window = await desktop_service.find_window_by_title(
                title_pattern=request.title_pattern,
                exact_match=request.exact_match,
            )
            return [window] if window else []
        elif request.process_name:
            windows = await desktop_service.find_windows_by_process(
                process_name=request.process_name,
            )
            return windows
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either title_pattern or process_name must be provided",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Window search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Window search failed: {str(e)}",
        )


# Automation script endpoints

@router.post("/scripts/create")
async def create_automation_script(request: AutomationScriptRequest):
    """Create an automation script."""
    try:
        actions = [action_req.to_desktop_action() for action_req in request.actions]
        desktop_service.create_automation_script(
            script_name=request.script_name,
            actions=actions,
        )
        return {
            "message": f"Automation script '{request.script_name}' created successfully",
            "script_name": request.script_name,
            "action_count": len(actions),
        }
    except Exception as e:
        logger.error(f"Failed to create automation script: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create automation script: {str(e)}",
        )


@router.post("/scripts/execute", response_model=List[DesktopResponse])
async def execute_automation_script(request: ExecuteScriptRequest):
    """Execute an automation script."""
    try:
        responses = await desktop_service.execute_automation_script(
            script_name=request.script_name,
            task_id=request.task_id,
            parameters=request.parameters,
        )
        return responses
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to execute automation script: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute automation script: {str(e)}",
        )


@router.get("/scripts")
async def list_automation_scripts():
    """List available automation scripts."""
    try:
        status_data = desktop_service.get_service_status()
        return {
            "scripts": status_data["automation_scripts"],
            "count": len(status_data["automation_scripts"]),
        }
    except Exception as e:
        logger.error(f"Failed to list automation scripts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list automation scripts: {str(e)}",
        )


@router.delete("/scripts/clear")
async def clear_automation_scripts():
    """Clear all automation scripts."""
    try:
        desktop_service.clear_automation_scripts()
        return {"message": "All automation scripts cleared successfully"}
    except Exception as e:
        logger.error(f"Failed to clear automation scripts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear automation scripts: {str(e)}",
        )


# Screen recording endpoints

@router.post("/recording/start")
async def start_screen_recording(request: RecordingRequest):
    """Start screen recording."""
    try:
        recording_id = await desktop_service.start_screen_recording(
            task_id=request.task_id,
        )
        return {
            "message": "Screen recording started",
            "recording_id": str(recording_id),
        }
    except Exception as e:
        logger.error(f"Failed to start screen recording: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start screen recording: {str(e)}",
        )


@router.post("/recording/stop/{recording_id}")
async def stop_screen_recording(recording_id: UUID):
    """Stop screen recording."""
    try:
        recording_data = await desktop_service.stop_screen_recording(recording_id)
        if recording_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recording {recording_id} not found",
            )
        
        return {
            "message": "Screen recording stopped",
            "recording_id": str(recording_id),
            "duration": recording_data["duration"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop screen recording: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop screen recording: {str(e)}",
        )


@router.post("/recording/stop-all")
async def stop_all_recordings():
    """Stop all active screen recordings."""
    try:
        await desktop_service.stop_all_recordings()
        return {"message": "All screen recordings stopped"}
    except Exception as e:
        logger.error(f"Failed to stop all recordings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop all recordings: {str(e)}",
        )


# Statistics and monitoring endpoints

@router.get("/statistics", response_model=DesktopStatisticsResponse)
async def get_desktop_statistics(
    task_id: Optional[UUID] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
):
    """Get desktop action statistics."""
    try:
        stats = await desktop_service.get_action_statistics(
            task_id=task_id,
            start_date=start_date,
            end_date=end_date,
        )
        return DesktopStatisticsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get desktop statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get desktop statistics: {str(e)}",
        )


# Maintenance endpoints

@router.post("/maintenance/cleanup-history")
async def cleanup_desktop_history(
    max_age_hours: int = Query(default=24, ge=1, le=168),  # 1 hour to 1 week
):
    """Clean up old desktop action and event history."""
    try:
        await desktop_service.cleanup_old_history(max_age_hours=max_age_hours)
        return {
            "message": f"Desktop history cleanup completed (max age: {max_age_hours} hours)"
        }
    except Exception as e:
        logger.error(f"Desktop history cleanup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Desktop history cleanup failed: {str(e)}",
        )