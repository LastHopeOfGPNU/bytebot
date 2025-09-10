"""Desktop service for high-level desktop operations and automation."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db_session
from ..core.logging import get_logger
from ..models import Task
from ..websocket.router import notify_desktop_action
from .client import DesktopClient
from .models import (
    DesktopAction,
    DesktopActionType,
    DesktopEvent,
    DesktopEventType,
    DesktopResponse,
    DesktopScreenshot,
    DesktopWindow,
    MouseButton,
    WindowInfo,
)

logger = get_logger(__name__)


class DesktopService:
    """High-level desktop service for automation and control."""
    
    def __init__(self):
        self.client = DesktopClient()
        self.action_history: List[DesktopAction] = []
        self.event_history: List[DesktopEvent] = []
        self.active_recordings: Dict[UUID, Dict[str, Any]] = {}
        self.automation_scripts: Dict[str, List[DesktopAction]] = {}
    
    async def execute_action(
        self,
        action: DesktopAction,
        task_id: Optional[UUID] = None,
        notify: bool = True,
        db: Optional[AsyncSession] = None,
    ) -> DesktopResponse:
        """Execute a desktop action with logging and notifications."""
        try:
            logger.info(f"Executing desktop action: {action.type} (ID: {action.id})")
            
            # Add to history
            self.action_history.append(action)
            
            # Notify action started
            if notify and task_id:
                await notify_desktop_action(
                    task_id=str(task_id),
                    action_data={
                        "action_id": str(action.id),
                        "type": action.type.value,
                        "status": "started",
                        "timestamp": action.timestamp.isoformat(),
                    },
                )
            
            # Execute action
            response = await self.client.execute_action(action)
            
            # Save to database if available
            if db and task_id:
                await self._save_action_to_db(db, task_id, action, response)
            
            # Notify action completed
            if notify and task_id:
                await notify_desktop_action(
                    task_id=str(task_id),
                    action_data={
                        "action_id": str(action.id),
                        "type": action.type.value,
                        "status": "completed" if response.success else "failed",
                        "success": response.success,
                        "message": response.message,
                        "error": response.error,
                        "execution_time": response.execution_time,
                        "timestamp": response.timestamp.isoformat(),
                    },
                )
            
            logger.info(
                f"Desktop action {action.type} {'completed' if response.success else 'failed'}: "
                f"{response.message or response.error}"
            )
            
            return response
        
        except Exception as e:
            logger.error(f"Desktop action execution failed: {e}")
            
            error_response = DesktopResponse.error_response(
                action_id=action.id,
                error=str(e),
            )
            
            # Notify error
            if notify and task_id:
                await notify_desktop_action(
                    task_id=str(task_id),
                    action_data={
                        "action_id": str(action.id),
                        "type": action.type.value,
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
            
            return error_response
    
    async def execute_action_sequence(
        self,
        actions: List[DesktopAction],
        task_id: Optional[UUID] = None,
        stop_on_error: bool = True,
        delay_between_actions: float = 0.1,
        db: Optional[AsyncSession] = None,
    ) -> List[DesktopResponse]:
        """Execute a sequence of desktop actions."""
        responses = []
        
        try:
            logger.info(f"Executing desktop action sequence: {len(actions)} actions")
            
            for i, action in enumerate(actions):
                logger.info(f"Executing action {i + 1}/{len(actions)}: {action.type}")
                
                response = await self.execute_action(
                    action=action,
                    task_id=task_id,
                    notify=True,
                    db=db,
                )
                
                responses.append(response)
                
                # Stop on error if requested
                if not response.success and stop_on_error:
                    logger.warning(f"Stopping action sequence due to error: {response.error}")
                    break
                
                # Delay between actions
                if delay_between_actions > 0 and i < len(actions) - 1:
                    await asyncio.sleep(delay_between_actions)
            
            successful_actions = sum(1 for r in responses if r.success)
            logger.info(
                f"Desktop action sequence completed: {successful_actions}/{len(actions)} successful"
            )
            
            return responses
        
        except Exception as e:
            logger.error(f"Desktop action sequence failed: {e}")
            raise
    
    # High-level action methods
    
    async def click_at_position(
        self,
        x: int,
        y: int,
        button: MouseButton = MouseButton.LEFT,
        clicks: int = 1,
        task_id: Optional[UUID] = None,
    ) -> DesktopResponse:
        """Click at a specific position."""
        action_type = DesktopActionType.MOUSE_DOUBLE_CLICK if clicks == 2 else DesktopActionType.MOUSE_CLICK
        if button == MouseButton.RIGHT:
            action_type = DesktopActionType.MOUSE_RIGHT_CLICK
        
        action = DesktopAction(
            type=action_type,
            x=x,
            y=y,
            button=button,
            clicks=clicks,
        )
        
        return await self.execute_action(action, task_id)
    
    async def type_text(
        self,
        text: str,
        task_id: Optional[UUID] = None,
    ) -> DesktopResponse:
        """Type text at current cursor position."""
        action = DesktopAction(
            type=DesktopActionType.TYPE_TEXT,
            text=text,
        )
        
        return await self.execute_action(action, task_id)
    
    async def press_key_combination(
        self,
        keys: List[str],
        task_id: Optional[UUID] = None,
    ) -> DesktopResponse:
        """Press a key combination (e.g., ['ctrl', 'c'])."""
        action = DesktopAction(
            type=DesktopActionType.KEY_COMBINATION,
            keys=keys,
        )
        
        return await self.execute_action(action, task_id)
    
    async def take_screenshot(
        self,
        task_id: Optional[UUID] = None,
    ) -> DesktopResponse:
        """Take a screenshot of the desktop."""
        action = DesktopAction(type=DesktopActionType.SCREENSHOT)
        
        return await self.execute_action(action, task_id)
    
    async def focus_window(
        self,
        window_title: Optional[str] = None,
        window_id: Optional[int] = None,
        task_id: Optional[UUID] = None,
    ) -> DesktopResponse:
        """Focus a window by title or ID."""
        action = DesktopAction(
            type=DesktopActionType.WINDOW_FOCUS,
            window_title=window_title,
            window_id=window_id,
        )
        
        return await self.execute_action(action, task_id)
    
    async def launch_application(
        self,
        app_name: str,
        app_args: Optional[List[str]] = None,
        task_id: Optional[UUID] = None,
    ) -> DesktopResponse:
        """Launch an application."""
        action = DesktopAction(
            type=DesktopActionType.APP_LAUNCH,
            app_name=app_name,
            app_args=app_args or [],
        )
        
        return await self.execute_action(action, task_id)
    
    async def wait_for_window(
        self,
        window_title: str,
        timeout: float = 10.0,
        task_id: Optional[UUID] = None,
    ) -> DesktopResponse:
        """Wait for a window to appear."""
        action = DesktopAction(
            type=DesktopActionType.WAIT_FOR_WINDOW,
            window_title=window_title,
            wait_time=timeout,
        )
        
        return await self.execute_action(action, task_id)
    
    # Automation and scripting
    
    def create_automation_script(
        self,
        script_name: str,
        actions: List[DesktopAction],
    ):
        """Create an automation script."""
        self.automation_scripts[script_name] = actions
        logger.info(f"Created automation script '{script_name}' with {len(actions)} actions")
    
    async def execute_automation_script(
        self,
        script_name: str,
        task_id: Optional[UUID] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[DesktopResponse]:
        """Execute an automation script."""
        if script_name not in self.automation_scripts:
            raise ValueError(f"Automation script '{script_name}' not found")
        
        actions = self.automation_scripts[script_name]
        
        # Apply parameters if provided
        if parameters:
            actions = self._apply_script_parameters(actions, parameters)
        
        return await self.execute_action_sequence(
            actions=actions,
            task_id=task_id,
        )
    
    def _apply_script_parameters(
        self,
        actions: List[DesktopAction],
        parameters: Dict[str, Any],
    ) -> List[DesktopAction]:
        """Apply parameters to automation script actions."""
        # Create copies of actions with parameter substitution
        updated_actions = []
        
        for action in actions:
            action_dict = action.dict()
            
            # Replace parameter placeholders
            for key, value in action_dict.items():
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    param_name = value[2:-1]
                    if param_name in parameters:
                        action_dict[key] = parameters[param_name]
            
            updated_actions.append(DesktopAction(**action_dict))
        
        return updated_actions
    
    # Window management
    
    async def get_windows(self) -> List[DesktopWindow]:
        """Get list of desktop windows."""
        return await self.client.get_windows()
    
    async def get_active_window(self) -> Optional[DesktopWindow]:
        """Get the currently active window."""
        return await self.client.get_active_window()
    
    async def find_window_by_title(
        self,
        title_pattern: str,
        exact_match: bool = False,
    ) -> Optional[DesktopWindow]:
        """Find window by title pattern."""
        windows = await self.get_windows()
        
        for window in windows:
            if exact_match:
                if window.info.title == title_pattern:
                    return window
            else:
                if title_pattern.lower() in window.info.title.lower():
                    return window
        
        return None
    
    async def find_windows_by_process(
        self,
        process_name: str,
    ) -> List[DesktopWindow]:
        """Find windows by process name."""
        windows = await self.get_windows()
        
        return [
            window
            for window in windows
            if window.info.process_name and process_name.lower() in window.info.process_name.lower()
        ]
    
    # Screen recording and monitoring
    
    async def start_screen_recording(
        self,
        recording_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
    ) -> UUID:
        """Start screen recording."""
        if recording_id is None:
            recording_id = uuid4()
        
        # TODO: Implement actual screen recording
        self.active_recordings[recording_id] = {
            "task_id": task_id,
            "start_time": datetime.utcnow(),
            "frames": [],
        }
        
        logger.info(f"Started screen recording: {recording_id}")
        
        if task_id:
            await notify_desktop_event(
                task_id=str(task_id),
                event_data={
                    "type": "screen_recording_started",
                    "recording_id": str(recording_id),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        
        return recording_id
    
    async def stop_screen_recording(
        self,
        recording_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        """Stop screen recording."""
        if recording_id not in self.active_recordings:
            return None
        
        recording_data = self.active_recordings.pop(recording_id)
        recording_data["end_time"] = datetime.utcnow()
        recording_data["duration"] = (
            recording_data["end_time"] - recording_data["start_time"]
        ).total_seconds()
        
        logger.info(f"Stopped screen recording: {recording_id}")
        
        if recording_data.get("task_id"):
            await notify_desktop_event(
                task_id=str(recording_data["task_id"]),
                event_data={
                    "type": "screen_recording_stopped",
                    "recording_id": str(recording_id),
                    "duration": recording_data["duration"],
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
        
        return recording_data
    
    # Event handling
    
    async def emit_event(
        self,
        event: DesktopEvent,
        task_id: Optional[UUID] = None,
    ):
        """Emit a desktop event."""
        self.event_history.append(event)
        
        if task_id:
            await notify_desktop_event(
                task_id=str(task_id),
                event_data={
                    "event_id": str(event.id),
                    "type": event.type.value,
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.data,
                },
            )
        
        logger.debug(f"Desktop event emitted: {event.type}")
    
    # Database operations
    
    async def _save_action_to_db(
        self,
        db: AsyncSession,
        task_id: UUID,
        action: DesktopAction,
        response: DesktopResponse,
    ):
        """Save desktop action to database."""
        try:
            # TODO: Create desktop action table and model
            # For now, we'll store as task metadata or in a generic log table
            
            action_data = {
                "action_id": str(action.id),
                "type": action.type.value,
                "parameters": action.dict(),
                "response": {
                    "success": response.success,
                    "message": response.message,
                    "error": response.error,
                    "execution_time": response.execution_time,
                },
                "timestamp": action.timestamp.isoformat(),
            }
            
            logger.debug(f"Desktop action saved to database: {action.id}")
        
        except Exception as e:
            logger.error(f"Failed to save desktop action to database: {e}")
    
    # Statistics and monitoring
    
    async def get_action_statistics(
        self,
        task_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get desktop action statistics."""
        # Filter actions by criteria
        filtered_actions = self.action_history
        
        if start_date:
            filtered_actions = [
                action for action in filtered_actions
                if action.timestamp >= start_date
            ]
        
        if end_date:
            filtered_actions = [
                action for action in filtered_actions
                if action.timestamp <= end_date
            ]
        
        # Calculate statistics
        total_actions = len(filtered_actions)
        actions_by_type = {}
        
        for action in filtered_actions:
            action_type = action.type.value
            actions_by_type[action_type] = actions_by_type.get(action_type, 0) + 1
        
        return {
            "total_actions": total_actions,
            "actions_by_type": actions_by_type,
            "automation_scripts": len(self.automation_scripts),
            "active_recordings": len(self.active_recordings),
            "recent_events": len(self.event_history[-100:]),  # Last 100 events
        }
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get desktop service status."""
        return {
            "connected": self.client.is_connected,
            "capabilities": self.client.get_capabilities(),
            "action_history_size": len(self.action_history),
            "event_history_size": len(self.event_history),
            "automation_scripts": list(self.automation_scripts.keys()),
            "active_recordings": list(self.active_recordings.keys()),
        }
    
    async def test_connection(self) -> bool:
        """Test desktop connection."""
        return await self.client.test_connection()
    
    # Cleanup methods
    
    async def cleanup_old_history(self, max_age_hours: int = 24):
        """Clean up old action and event history."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        # Clean action history
        old_action_count = len(self.action_history)
        self.action_history = [
            action for action in self.action_history
            if action.timestamp > cutoff_time
        ]
        
        # Clean event history
        old_event_count = len(self.event_history)
        self.event_history = [
            event for event in self.event_history
            if event.timestamp > cutoff_time
        ]
        
        cleaned_actions = old_action_count - len(self.action_history)
        cleaned_events = old_event_count - len(self.event_history)
        
        if cleaned_actions > 0 or cleaned_events > 0:
            logger.info(
                f"Cleaned up old history: {cleaned_actions} actions, {cleaned_events} events"
            )
    
    def clear_automation_scripts(self):
        """Clear all automation scripts."""
        script_count = len(self.automation_scripts)
        self.automation_scripts.clear()
        logger.info(f"Cleared {script_count} automation scripts")
    
    async def stop_all_recordings(self):
        """Stop all active screen recordings."""
        recording_ids = list(self.active_recordings.keys())
        
        for recording_id in recording_ids:
            await self.stop_screen_recording(recording_id)
        
        logger.info(f"Stopped {len(recording_ids)} active recordings")


# Global desktop service instance
desktop_service = DesktopService()