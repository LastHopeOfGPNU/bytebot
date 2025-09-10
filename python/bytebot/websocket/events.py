"""WebSocket event types and models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WebSocketEventType(str, Enum):
    """WebSocket event types."""
    
    # Connection events
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    
    # Task events
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_STARTED = "task_started"
    TASK_PAUSED = "task_paused"
    TASK_RESUMED = "task_resumed"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    TASK_PROGRESS = "task_progress"
    
    # Message events
    MESSAGE_CREATED = "message_created"
    MESSAGE_UPDATED = "message_updated"
    MESSAGE_PROCESSED = "message_processed"
    MESSAGE_FAILED = "message_failed"
    
    # Summary events
    SUMMARY_CREATED = "summary_created"
    SUMMARY_UPDATED = "summary_updated"
    SUMMARY_APPROVED = "summary_approved"
    SUMMARY_ARCHIVED = "summary_archived"
    
    # AI events
    AI_THINKING = "ai_thinking"
    AI_TOOL_USE = "ai_tool_use"
    AI_TOOL_RESULT = "ai_tool_result"
    AI_RESPONSE = "ai_response"
    
    # System events
    SYSTEM_STATUS = "system_status"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    
    # Desktop events
    DESKTOP_ACTION = "desktop_action"
    DESKTOP_SCREENSHOT = "desktop_screenshot"
    DESKTOP_STATUS = "desktop_status"


class WebSocketEvent(BaseModel):
    """WebSocket event model."""
    
    id: UUID = Field(default_factory=uuid4)
    type: WebSocketEventType
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    task_id: Optional[UUID] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "task_id": str(self.task_id) if self.task_id else None,
            "user_id": self.user_id,
            "session_id": self.session_id,
        }
    
    @classmethod
    def create_task_event(
        cls,
        event_type: WebSocketEventType,
        task_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> "WebSocketEvent":
        """Create a task-related event."""
        return cls(
            type=event_type,
            task_id=task_id,
            data=data,
            user_id=user_id,
            session_id=session_id,
        )
    
    @classmethod
    def create_message_event(
        cls,
        event_type: WebSocketEventType,
        message_id: UUID,
        task_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> "WebSocketEvent":
        """Create a message-related event."""
        event_data = {"message_id": str(message_id), **data}
        return cls(
            type=event_type,
            task_id=task_id,
            data=event_data,
            user_id=user_id,
            session_id=session_id,
        )
    
    @classmethod
    def create_summary_event(
        cls,
        event_type: WebSocketEventType,
        summary_id: UUID,
        task_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> "WebSocketEvent":
        """Create a summary-related event."""
        event_data = {"summary_id": str(summary_id), **data}
        return cls(
            type=event_type,
            task_id=task_id,
            data=event_data,
            user_id=user_id,
            session_id=session_id,
        )
    
    @classmethod
    def create_ai_event(
        cls,
        event_type: WebSocketEventType,
        task_id: UUID,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> "WebSocketEvent":
        """Create an AI-related event."""
        return cls(
            type=event_type,
            task_id=task_id,
            data=data,
            user_id=user_id,
            session_id=session_id,
        )
    
    @classmethod
    def create_system_event(
        cls,
        event_type: WebSocketEventType,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> "WebSocketEvent":
        """Create a system-related event."""
        return cls(
            type=event_type,
            data=data,
            user_id=user_id,
            session_id=session_id,
        )
    
    @classmethod
    def create_error_event(
        cls,
        error_message: str,
        error_code: Optional[str] = None,
        task_id: Optional[UUID] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> "WebSocketEvent":
        """Create an error event."""
        data = {"message": error_message}
        if error_code:
            data["code"] = error_code
        
        return cls(
            type=WebSocketEventType.ERROR,
            task_id=task_id,
            data=data,
            user_id=user_id,
            session_id=session_id,
        )
    
    @classmethod
    def create_heartbeat_event(
        cls,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> "WebSocketEvent":
        """Create a heartbeat event."""
        return cls(
            type=WebSocketEventType.HEARTBEAT,
            data={"timestamp": datetime.utcnow().isoformat()},
            user_id=user_id,
            session_id=session_id,
        )


class WebSocketMessage(BaseModel):
    """WebSocket message model for client-server communication."""
    
    type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "data": self.data,
            "request_id": self.request_id,
        }


class WebSocketResponse(BaseModel):
    """WebSocket response model."""
    
    type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "data": self.data,
            "success": self.success,
            "error": self.error,
            "request_id": self.request_id,
        }
    
    @classmethod
    def success_response(
        cls,
        message_type: str,
        data: Dict[str, Any],
        request_id: Optional[str] = None,
    ) -> "WebSocketResponse":
        """Create a success response."""
        return cls(
            type=message_type,
            data=data,
            success=True,
            request_id=request_id,
        )
    
    @classmethod
    def error_response(
        cls,
        message_type: str,
        error_message: str,
        request_id: Optional[str] = None,
    ) -> "WebSocketResponse":
        """Create an error response."""
        return cls(
            type=message_type,
            data={},
            success=False,
            error=error_message,
            request_id=request_id,
        )