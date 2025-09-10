"""WebSocket connection manager."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logging import get_logger
from .events import WebSocketEvent, WebSocketEventType, WebSocketMessage, WebSocketResponse

logger = get_logger(__name__)


class WebSocketConnection:
    """Represents a WebSocket connection."""
    
    def __init__(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        self.websocket = websocket
        self.connection_id = connection_id
        self.user_id = user_id
        self.session_id = session_id
        self.connected_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        self.subscribed_tasks: Set[UUID] = set()
        self.is_active = True
    
    async def send_event(self, event: WebSocketEvent) -> bool:
        """Send an event to this connection."""
        try:
            await self.websocket.send_text(json.dumps(event.to_dict()))
            return True
        except Exception as e:
            logger.error(f"Failed to send event to connection {self.connection_id}: {e}")
            self.is_active = False
            return False
    
    async def send_response(self, response: WebSocketResponse) -> bool:
        """Send a response to this connection."""
        try:
            await self.websocket.send_text(json.dumps(response.to_dict()))
            return True
        except Exception as e:
            logger.error(f"Failed to send response to connection {self.connection_id}: {e}")
            self.is_active = False
            return False
    
    def subscribe_to_task(self, task_id: UUID):
        """Subscribe this connection to task events."""
        self.subscribed_tasks.add(task_id)
        logger.info(f"Connection {self.connection_id} subscribed to task {task_id}")
    
    def unsubscribe_from_task(self, task_id: UUID):
        """Unsubscribe this connection from task events."""
        self.subscribed_tasks.discard(task_id)
        logger.info(f"Connection {self.connection_id} unsubscribed from task {task_id}")
    
    def is_subscribed_to_task(self, task_id: UUID) -> bool:
        """Check if this connection is subscribed to a task."""
        return task_id in self.subscribed_tasks
    
    def update_heartbeat(self):
        """Update the last heartbeat timestamp."""
        self.last_heartbeat = datetime.utcnow()


class WebSocketManager:
    """Manages WebSocket connections and event broadcasting."""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        self.task_subscribers: Dict[UUID, Set[str]] = {}  # task_id -> connection_ids
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the WebSocket manager."""
        logger.info("Starting WebSocket manager")
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        """Stop the WebSocket manager."""
        logger.info("Stopping WebSocket manager")
        
        # Cancel background tasks
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Close all connections
        for connection in list(self.connections.values()):
            await self.disconnect(connection.connection_id)
    
    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> WebSocketConnection:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        connection = WebSocketConnection(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
            session_id=session_id,
        )
        
        self.connections[connection_id] = connection
        
        # Track user connections
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)
        
        logger.info(f"WebSocket connection established: {connection_id} (user: {user_id})")
        
        # Send connection confirmation
        event = WebSocketEvent.create_system_event(
            WebSocketEventType.CONNECT,
            {"connection_id": connection_id, "timestamp": datetime.utcnow().isoformat()},
            user_id=user_id,
            session_id=session_id,
        )
        await connection.send_event(event)
        
        return connection
    
    async def disconnect(self, connection_id: str):
        """Disconnect a WebSocket connection."""
        connection = self.connections.get(connection_id)
        if not connection:
            return
        
        logger.info(f"WebSocket connection disconnected: {connection_id}")
        
        # Remove from user connections
        if connection.user_id and connection.user_id in self.user_connections:
            self.user_connections[connection.user_id].discard(connection_id)
            if not self.user_connections[connection.user_id]:
                del self.user_connections[connection.user_id]
        
        # Remove from task subscriptions
        for task_id in connection.subscribed_tasks:
            if task_id in self.task_subscribers:
                self.task_subscribers[task_id].discard(connection_id)
                if not self.task_subscribers[task_id]:
                    del self.task_subscribers[task_id]
        
        # Close WebSocket if still active
        try:
            if connection.is_active:
                await connection.websocket.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket connection {connection_id}: {e}")
        
        # Remove from connections
        del self.connections[connection_id]
    
    async def handle_message(
        self,
        connection_id: str,
        message_data: Dict[str, Any],
        db: AsyncSession,
    ) -> Optional[WebSocketResponse]:
        """Handle incoming WebSocket message."""
        connection = self.connections.get(connection_id)
        if not connection:
            return WebSocketResponse.error_response(
                "error",
                "Connection not found",
            )
        
        try:
            message = WebSocketMessage(**message_data)
        except Exception as e:
            logger.error(f"Invalid message format from {connection_id}: {e}")
            return WebSocketResponse.error_response(
                "error",
                "Invalid message format",
                message_data.get("request_id"),
            )
        
        # Update heartbeat
        connection.update_heartbeat()
        
        # Handle different message types
        try:
            if message.type == "subscribe_task":
                return await self._handle_subscribe_task(connection, message, db)
            elif message.type == "unsubscribe_task":
                return await self._handle_unsubscribe_task(connection, message, db)
            elif message.type == "heartbeat":
                return await self._handle_heartbeat(connection, message)
            elif message.type == "get_status":
                return await self._handle_get_status(connection, message, db)
            else:
                return WebSocketResponse.error_response(
                    message.type,
                    f"Unknown message type: {message.type}",
                    message.request_id,
                )
        except Exception as e:
            logger.error(f"Error handling message {message.type} from {connection_id}: {e}")
            return WebSocketResponse.error_response(
                message.type,
                f"Internal error: {str(e)}",
                message.request_id,
            )
    
    async def _handle_subscribe_task(
        self,
        connection: WebSocketConnection,
        message: WebSocketMessage,
        db: AsyncSession,
    ) -> WebSocketResponse:
        """Handle task subscription request."""
        task_id_str = message.data.get("task_id")
        if not task_id_str:
            return WebSocketResponse.error_response(
                message.type,
                "task_id is required",
                message.request_id,
            )
        
        try:
            task_id = UUID(task_id_str)
        except ValueError:
            return WebSocketResponse.error_response(
                message.type,
                "Invalid task_id format",
                message.request_id,
            )
        
        # Subscribe connection to task
        connection.subscribe_to_task(task_id)
        
        # Track task subscribers
        if task_id not in self.task_subscribers:
            self.task_subscribers[task_id] = set()
        self.task_subscribers[task_id].add(connection.connection_id)
        
        return WebSocketResponse.success_response(
            message.type,
            {"task_id": str(task_id), "subscribed": True},
            message.request_id,
        )
    
    async def _handle_unsubscribe_task(
        self,
        connection: WebSocketConnection,
        message: WebSocketMessage,
        db: AsyncSession,
    ) -> WebSocketResponse:
        """Handle task unsubscription request."""
        task_id_str = message.data.get("task_id")
        if not task_id_str:
            return WebSocketResponse.error_response(
                message.type,
                "task_id is required",
                message.request_id,
            )
        
        try:
            task_id = UUID(task_id_str)
        except ValueError:
            return WebSocketResponse.error_response(
                message.type,
                "Invalid task_id format",
                message.request_id,
            )
        
        # Unsubscribe connection from task
        connection.unsubscribe_from_task(task_id)
        
        # Remove from task subscribers
        if task_id in self.task_subscribers:
            self.task_subscribers[task_id].discard(connection.connection_id)
            if not self.task_subscribers[task_id]:
                del self.task_subscribers[task_id]
        
        return WebSocketResponse.success_response(
            message.type,
            {"task_id": str(task_id), "subscribed": False},
            message.request_id,
        )
    
    async def _handle_heartbeat(
        self,
        connection: WebSocketConnection,
        message: WebSocketMessage,
    ) -> WebSocketResponse:
        """Handle heartbeat message."""
        connection.update_heartbeat()
        
        return WebSocketResponse.success_response(
            message.type,
            {"timestamp": datetime.utcnow().isoformat()},
            message.request_id,
        )
    
    async def _handle_get_status(
        self,
        connection: WebSocketConnection,
        message: WebSocketMessage,
        db: AsyncSession,
    ) -> WebSocketResponse:
        """Handle status request."""
        return WebSocketResponse.success_response(
            message.type,
            {
                "connection_id": connection.connection_id,
                "user_id": connection.user_id,
                "session_id": connection.session_id,
                "connected_at": connection.connected_at.isoformat(),
                "subscribed_tasks": [str(task_id) for task_id in connection.subscribed_tasks],
                "total_connections": len(self.connections),
            },
            message.request_id,
        )
    
    async def broadcast_event(self, event: WebSocketEvent):
        """Broadcast an event to all relevant connections."""
        if not self.connections:
            return
        
        # Determine target connections
        target_connections = set()
        
        # If event has a task_id, send to task subscribers
        if event.task_id and event.task_id in self.task_subscribers:
            target_connections.update(self.task_subscribers[event.task_id])
        
        # If event has a user_id, send to user connections
        if event.user_id and event.user_id in self.user_connections:
            target_connections.update(self.user_connections[event.user_id])
        
        # For system events, broadcast to all connections
        if event.type in [WebSocketEventType.SYSTEM_STATUS, WebSocketEventType.ERROR]:
            target_connections.update(self.connections.keys())
        
        # Send event to target connections
        failed_connections = []
        for connection_id in target_connections:
            connection = self.connections.get(connection_id)
            if connection and connection.is_active:
                success = await connection.send_event(event)
                if not success:
                    failed_connections.append(connection_id)
        
        # Clean up failed connections
        for connection_id in failed_connections:
            await self.disconnect(connection_id)
        
        logger.debug(f"Broadcasted event {event.type} to {len(target_connections)} connections")
    
    async def send_to_user(self, user_id: str, event: WebSocketEvent):
        """Send an event to all connections of a specific user."""
        if user_id not in self.user_connections:
            return
        
        failed_connections = []
        for connection_id in self.user_connections[user_id]:
            connection = self.connections.get(connection_id)
            if connection and connection.is_active:
                success = await connection.send_event(event)
                if not success:
                    failed_connections.append(connection_id)
        
        # Clean up failed connections
        for connection_id in failed_connections:
            await self.disconnect(connection_id)
    
    async def send_to_task_subscribers(self, task_id: UUID, event: WebSocketEvent):
        """Send an event to all subscribers of a specific task."""
        if task_id not in self.task_subscribers:
            return
        
        failed_connections = []
        for connection_id in self.task_subscribers[task_id]:
            connection = self.connections.get(connection_id)
            if connection and connection.is_active:
                success = await connection.send_event(event)
                if not success:
                    failed_connections.append(connection_id)
        
        # Clean up failed connections
        for connection_id in failed_connections:
            await self.disconnect(connection_id)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        active_connections = sum(1 for conn in self.connections.values() if conn.is_active)
        
        return {
            "total_connections": len(self.connections),
            "active_connections": active_connections,
            "users_connected": len(self.user_connections),
            "tasks_with_subscribers": len(self.task_subscribers),
            "connections_by_user": {
                user_id: len(connection_ids)
                for user_id, connection_ids in self.user_connections.items()
            },
        }
    
    async def _heartbeat_loop(self):
        """Background task to send heartbeat events."""
        while True:
            try:
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                
                if self.connections:
                    heartbeat_event = WebSocketEvent.create_heartbeat_event()
                    await self.broadcast_event(heartbeat_event)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    async def _cleanup_loop(self):
        """Background task to clean up inactive connections."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                now = datetime.utcnow()
                inactive_connections = []
                
                for connection_id, connection in self.connections.items():
                    # Consider connection inactive if no heartbeat for 5 minutes
                    if (now - connection.last_heartbeat).total_seconds() > 300:
                        inactive_connections.append(connection_id)
                
                # Disconnect inactive connections
                for connection_id in inactive_connections:
                    logger.info(f"Cleaning up inactive connection: {connection_id}")
                    await self.disconnect(connection_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")


# Global WebSocket manager instance
websocket_manager = WebSocketManager()