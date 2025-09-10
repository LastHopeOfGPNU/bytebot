"""WebSocket router for real-time communication."""

import json
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db_session as get_db
from ..core.logging import get_logger
from .events import WebSocketEvent, WebSocketEventType
from .manager import websocket_manager

logger = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Main WebSocket endpoint for real-time communication."""
    connection_id = str(uuid4())
    connection = None
    
    try:
        # Accept connection
        connection = await websocket_manager.connect(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
            session_id=session_id,
        )
        
        logger.info(f"WebSocket connection established: {connection_id}")
        
        # Listen for messages
        while True:
            try:
                # Receive message
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                logger.debug(f"Received message from {connection_id}: {message_data}")
                
                # Handle message
                response = await websocket_manager.handle_message(
                    connection_id=connection_id,
                    message_data=message_data,
                    db=db,
                )
                
                # Send response if available
                if response:
                    await connection.send_response(response)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket client {connection_id} disconnected")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from {connection_id}: {e}")
                error_event = WebSocketEvent.create_error_event(
                    "Invalid JSON format",
                    {"error": str(e)},
                    user_id=user_id,
                    session_id=session_id,
                )
                await connection.send_event(error_event)
            except Exception as e:
                logger.error(f"Error handling WebSocket message from {connection_id}: {e}")
                error_event = WebSocketEvent.create_error_event(
                    f"Message handling error: {str(e)}",
                    {"error": str(e)},
                    user_id=user_id,
                    session_id=session_id,
                )
                await connection.send_event(error_event)
    
    except Exception as e:
        logger.error(f"WebSocket connection error for {connection_id}: {e}")
    
    finally:
        # Clean up connection
        if connection:
            await websocket_manager.disconnect(connection_id)


@router.websocket("/ws/task/{task_id}")
async def task_websocket_endpoint(
    websocket: WebSocket,
    task_id: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """WebSocket endpoint for task-specific communication."""
    connection_id = str(uuid4())
    connection = None
    
    try:
        # Validate task_id format
        from uuid import UUID
        try:
            task_uuid = UUID(task_id)
        except ValueError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid task ID format")
            return
        
        # Accept connection
        connection = await websocket_manager.connect(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
            session_id=session_id,
        )
        
        # Auto-subscribe to the task
        connection.subscribe_to_task(task_uuid)
        if task_uuid not in websocket_manager.task_subscribers:
            websocket_manager.task_subscribers[task_uuid] = set()
        websocket_manager.task_subscribers[task_uuid].add(connection_id)
        
        logger.info(f"Task WebSocket connection established: {connection_id} for task {task_id}")
        
        # Send subscription confirmation
        subscription_event = WebSocketEvent.create_task_event(
            WebSocketEventType.TASK_SUBSCRIBED,
            {"task_id": task_id, "subscribed": True},
            task_id=task_uuid,
            user_id=user_id,
            session_id=session_id,
        )
        await connection.send_event(subscription_event)
        
        # Listen for messages
        while True:
            try:
                # Receive message
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                logger.debug(f"Received task message from {connection_id}: {message_data}")
                
                # Handle message
                response = await websocket_manager.handle_message(
                    connection_id=connection_id,
                    message_data=message_data,
                    db=db,
                )
                
                # Send response if available
                if response:
                    await connection.send_response(response)
                
            except WebSocketDisconnect:
                logger.info(f"Task WebSocket client {connection_id} disconnected from task {task_id}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from task WebSocket {connection_id}: {e}")
                error_event = WebSocketEvent.create_error_event(
                    "Invalid JSON format",
                    {"error": str(e), "task_id": task_id},
                    task_id=task_uuid,
                    user_id=user_id,
                    session_id=session_id,
                )
                await connection.send_event(error_event)
            except Exception as e:
                logger.error(f"Error handling task WebSocket message from {connection_id}: {e}")
                error_event = WebSocketEvent.create_error_event(
                    f"Message handling error: {str(e)}",
                    {"error": str(e), "task_id": task_id},
                    task_id=task_uuid,
                    user_id=user_id,
                    session_id=session_id,
                )
                await connection.send_event(error_event)
    
    except Exception as e:
        logger.error(f"Task WebSocket connection error for {connection_id}: {e}")
    
    finally:
        # Clean up connection
        if connection:
            await websocket_manager.disconnect(connection_id)


@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    return websocket_manager.get_connection_stats()


@router.post("/ws/broadcast")
async def broadcast_event(
    event_type: str,
    data: Dict[str, Any],
    task_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
):
    """Broadcast an event to WebSocket connections (for testing/admin use)."""
    try:
        # Convert task_id to UUID if provided
        task_uuid = None
        if task_id:
            from uuid import UUID
            task_uuid = UUID(task_id)
        
        # Create event
        event = WebSocketEvent(
            type=WebSocketEventType(event_type),
            data=data,
            task_id=task_uuid,
            user_id=user_id,
            session_id=session_id,
        )
        
        # Broadcast event
        await websocket_manager.broadcast_event(event)
        
        return {
            "success": True,
            "message": "Event broadcasted successfully",
            "event_type": event_type,
            "connections": len(websocket_manager.connections),
        }
    
    except Exception as e:
        logger.error(f"Error broadcasting event: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# Helper functions for other services to send WebSocket events

async def notify_task_created(task_id: str, task_data: Dict[str, Any], user_id: Optional[str] = None):
    """Notify about task creation."""
    from uuid import UUID
    
    event = WebSocketEvent.create_task_event(
        WebSocketEventType.TASK_CREATED,
        task_data,
        task_id=UUID(task_id),
        user_id=user_id,
    )
    await websocket_manager.broadcast_event(event)


async def notify_task_updated(task_id: str, task_data: Dict[str, Any], user_id: Optional[str] = None):
    """Notify about task updates."""
    from uuid import UUID
    
    event = WebSocketEvent.create_task_event(
        WebSocketEventType.TASK_UPDATED,
        task_data,
        task_id=UUID(task_id),
        user_id=user_id,
    )
    await websocket_manager.send_to_task_subscribers(UUID(task_id), event)


async def notify_task_status_changed(
    task_id: str,
    status: str,
    task_data: Dict[str, Any],
    user_id: Optional[str] = None,
):
    """Notify about task status changes."""
    from uuid import UUID
    
    event_type_map = {
        "running": WebSocketEventType.TASK_STARTED,
        "paused": WebSocketEventType.TASK_PAUSED,
        "completed": WebSocketEventType.TASK_COMPLETED,
        "failed": WebSocketEventType.TASK_FAILED,
        "cancelled": WebSocketEventType.TASK_CANCELLED,
    }
    
    event_type = event_type_map.get(status, WebSocketEventType.TASK_UPDATED)
    
    event = WebSocketEvent.create_task_event(
        event_type,
        {**task_data, "status": status},
        task_id=UUID(task_id),
        user_id=user_id,
    )
    await websocket_manager.send_to_task_subscribers(UUID(task_id), event)


async def notify_task_progress(
    task_id: str,
    progress_data: Dict[str, Any],
    user_id: Optional[str] = None,
):
    """Notify about task progress updates."""
    from uuid import UUID
    
    event = WebSocketEvent.create_task_event(
        WebSocketEventType.TASK_PROGRESS,
        progress_data,
        task_id=UUID(task_id),
        user_id=user_id,
    )
    await websocket_manager.send_to_task_subscribers(UUID(task_id), event)


async def notify_message_created(
    task_id: str,
    message_data: Dict[str, Any],
    user_id: Optional[str] = None,
):
    """Notify about new messages."""
    from uuid import UUID
    
    event = WebSocketEvent.create_message_event(
        WebSocketEventType.MESSAGE_CREATED,
        message_data,
        task_id=UUID(task_id),
        user_id=user_id,
    )
    await websocket_manager.send_to_task_subscribers(UUID(task_id), event)


async def notify_message_updated(
    task_id: str,
    message_data: Dict[str, Any],
    user_id: Optional[str] = None,
):
    """Notify about message updates."""
    from uuid import UUID
    
    event = WebSocketEvent.create_message_event(
        WebSocketEventType.MESSAGE_UPDATED,
        message_data,
        task_id=UUID(task_id),
        user_id=user_id,
    )
    await websocket_manager.send_to_task_subscribers(UUID(task_id), event)


async def notify_ai_thinking(
    task_id: str,
    thinking_data: Dict[str, Any],
    user_id: Optional[str] = None,
):
    """Notify about AI thinking process."""
    from uuid import UUID
    
    event = WebSocketEvent.create_ai_event(
        WebSocketEventType.AI_THINKING,
        thinking_data,
        task_id=UUID(task_id),
        user_id=user_id,
    )
    await websocket_manager.send_to_task_subscribers(UUID(task_id), event)


async def notify_ai_response(
    task_id: str,
    response_data: Dict[str, Any],
    user_id: Optional[str] = None,
):
    """Notify about AI responses."""
    from uuid import UUID
    
    event = WebSocketEvent.create_ai_event(
        WebSocketEventType.AI_RESPONSE,
        response_data,
        task_id=UUID(task_id),
        user_id=user_id,
    )
    await websocket_manager.send_to_task_subscribers(UUID(task_id), event)


async def notify_desktop_action(
    action_data: Dict[str, Any],
    task_id: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """Notify about desktop actions."""
    from uuid import UUID
    
    task_uuid = UUID(task_id) if task_id else None
    
    event = WebSocketEvent.create_desktop_event(
        WebSocketEventType.DESKTOP_ACTION,
        action_data,
        task_id=task_uuid,
        user_id=user_id,
    )
    
    if task_uuid:
        await websocket_manager.send_to_task_subscribers(task_uuid, event)
    else:
        await websocket_manager.broadcast_event(event)


async def notify_system_status(
    status_data: Dict[str, Any],
    user_id: Optional[str] = None,
):
    """Notify about system status changes."""
    event = WebSocketEvent.create_system_event(
        WebSocketEventType.SYSTEM_STATUS,
        status_data,
        user_id=user_id,
    )
    await websocket_manager.broadcast_event(event)


async def notify_error(
    error_message: str,
    error_data: Dict[str, Any],
    task_id: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """Notify about errors."""
    from uuid import UUID
    
    task_uuid = UUID(task_id) if task_id else None
    
    event = WebSocketEvent.create_error_event(
        error_message,
        error_data,
        task_id=task_uuid,
        user_id=user_id,
    )
    
    if task_uuid:
        await websocket_manager.send_to_task_subscribers(task_uuid, event)
    else:
        await websocket_manager.broadcast_event(event)