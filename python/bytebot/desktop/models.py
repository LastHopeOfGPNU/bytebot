"""Desktop control models and data structures."""

import base64
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class DesktopActionType(str, Enum):
    """Types of desktop actions."""
    
    # Mouse actions
    MOUSE_CLICK = "mouse_click"
    MOUSE_DOUBLE_CLICK = "mouse_double_click"
    MOUSE_RIGHT_CLICK = "mouse_right_click"
    MOUSE_MOVE = "mouse_move"
    MOUSE_DRAG = "mouse_drag"
    MOUSE_SCROLL = "mouse_scroll"
    
    # Keyboard actions
    KEY_PRESS = "key_press"
    KEY_RELEASE = "key_release"
    KEY_COMBINATION = "key_combination"
    TYPE_TEXT = "type_text"
    
    # Window actions
    WINDOW_FOCUS = "window_focus"
    WINDOW_CLOSE = "window_close"
    WINDOW_MINIMIZE = "window_minimize"
    WINDOW_MAXIMIZE = "window_maximize"
    WINDOW_RESTORE = "window_restore"
    WINDOW_MOVE = "window_move"
    WINDOW_RESIZE = "window_resize"
    
    # Screen actions
    SCREENSHOT = "screenshot"
    SCREEN_RECORD_START = "screen_record_start"
    SCREEN_RECORD_STOP = "screen_record_stop"
    
    # Application actions
    APP_LAUNCH = "app_launch"
    APP_CLOSE = "app_close"
    APP_SWITCH = "app_switch"
    
    # System actions
    SYSTEM_SLEEP = "system_sleep"
    SYSTEM_SHUTDOWN = "system_shutdown"
    SYSTEM_RESTART = "system_restart"
    SYSTEM_LOCK = "system_lock"
    
    # File system actions
    FILE_OPEN = "file_open"
    FILE_SAVE = "file_save"
    FILE_COPY = "file_copy"
    FILE_PASTE = "file_paste"
    FILE_DELETE = "file_delete"
    
    # Clipboard actions
    CLIPBOARD_GET = "clipboard_get"
    CLIPBOARD_SET = "clipboard_set"
    
    # Wait actions
    WAIT = "wait"
    WAIT_FOR_ELEMENT = "wait_for_element"
    WAIT_FOR_WINDOW = "wait_for_window"


class MouseButton(str, Enum):
    """Mouse button types."""
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"
    WHEEL_UP = "wheel_up"
    WHEEL_DOWN = "wheel_down"


class DesktopEventType(str, Enum):
    """Types of desktop events."""
    
    # Mouse events
    MOUSE_MOVED = "mouse_moved"
    MOUSE_CLICKED = "mouse_clicked"
    MOUSE_SCROLLED = "mouse_scrolled"
    
    # Keyboard events
    KEY_PRESSED = "key_pressed"
    KEY_RELEASED = "key_released"
    TEXT_TYPED = "text_typed"
    
    # Window events
    WINDOW_OPENED = "window_opened"
    WINDOW_CLOSED = "window_closed"
    WINDOW_FOCUSED = "window_focused"
    WINDOW_MOVED = "window_moved"
    WINDOW_RESIZED = "window_resized"
    
    # Application events
    APP_LAUNCHED = "app_launched"
    APP_CLOSED = "app_closed"
    APP_SWITCHED = "app_switched"
    
    # System events
    SCREEN_LOCKED = "screen_locked"
    SCREEN_UNLOCKED = "screen_unlocked"
    SYSTEM_IDLE = "system_idle"
    SYSTEM_ACTIVE = "system_active"
    
    # File system events
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    
    # Clipboard events
    CLIPBOARD_CHANGED = "clipboard_changed"
    
    # Error events
    ACTION_FAILED = "action_failed"
    CONNECTION_LOST = "connection_lost"
    PERMISSION_DENIED = "permission_denied"


class MouseEvent(BaseModel):
    """Mouse event data."""
    x: int = Field(..., description="X coordinate")
    y: int = Field(..., description="Y coordinate")
    button: Optional[MouseButton] = Field(None, description="Mouse button")
    clicks: int = Field(1, description="Number of clicks")
    modifiers: List[str] = Field(default_factory=list, description="Keyboard modifiers")


class KeyboardEvent(BaseModel):
    """Keyboard event data."""
    key: str = Field(..., description="Key name or character")
    modifiers: List[str] = Field(default_factory=list, description="Keyboard modifiers")
    text: Optional[str] = Field(None, description="Text to type")


class WindowInfo(BaseModel):
    """Window information."""
    id: int = Field(..., description="Window ID")
    title: str = Field(..., description="Window title")
    class_name: Optional[str] = Field(None, description="Window class name")
    process_name: Optional[str] = Field(None, description="Process name")
    process_id: Optional[int] = Field(None, description="Process ID")
    x: int = Field(..., description="Window X position")
    y: int = Field(..., description="Window Y position")
    width: int = Field(..., description="Window width")
    height: int = Field(..., description="Window height")
    is_visible: bool = Field(True, description="Whether window is visible")
    is_minimized: bool = Field(False, description="Whether window is minimized")
    is_maximized: bool = Field(False, description="Whether window is maximized")
    is_focused: bool = Field(False, description="Whether window has focus")


class DesktopWindow(BaseModel):
    """Desktop window model."""
    info: WindowInfo = Field(..., description="Window information")
    screenshot: Optional[str] = Field(None, description="Base64 encoded screenshot")
    children: List["DesktopWindow"] = Field(default_factory=list, description="Child windows")
    
    def get_center(self) -> Tuple[int, int]:
        """Get window center coordinates."""
        return (
            self.info.x + self.info.width // 2,
            self.info.y + self.info.height // 2,
        )
    
    def contains_point(self, x: int, y: int) -> bool:
        """Check if point is within window bounds."""
        return (
            self.info.x <= x <= self.info.x + self.info.width
            and self.info.y <= y <= self.info.y + self.info.height
        )


class DesktopScreenshot(BaseModel):
    """Desktop screenshot model."""
    id: UUID = Field(default_factory=uuid4, description="Screenshot ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Screenshot timestamp")
    width: int = Field(..., description="Screenshot width")
    height: int = Field(..., description="Screenshot height")
    format: str = Field("png", description="Image format")
    data: str = Field(..., description="Base64 encoded image data")
    file_size: int = Field(..., description="File size in bytes")
    
    @validator("data")
    def validate_base64_data(cls, v):
        """Validate base64 encoded data."""
        try:
            base64.b64decode(v)
            return v
        except Exception:
            raise ValueError("Invalid base64 encoded data")
    
    def get_image_bytes(self) -> bytes:
        """Get image data as bytes."""
        return base64.b64decode(self.data)
    
    def save_to_file(self, file_path: str):
        """Save screenshot to file."""
        with open(file_path, "wb") as f:
            f.write(self.get_image_bytes())


class DesktopAction(BaseModel):
    """Desktop action model."""
    id: UUID = Field(default_factory=uuid4, description="Action ID")
    type: DesktopActionType = Field(..., description="Action type")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Action timestamp")
    
    # Action parameters
    x: Optional[int] = Field(None, description="X coordinate")
    y: Optional[int] = Field(None, description="Y coordinate")
    width: Optional[int] = Field(None, description="Width")
    height: Optional[int] = Field(None, description="Height")
    
    # Mouse parameters
    button: Optional[MouseButton] = Field(None, description="Mouse button")
    clicks: int = Field(1, description="Number of clicks")
    scroll_delta: Optional[int] = Field(None, description="Scroll delta")
    
    # Keyboard parameters
    key: Optional[str] = Field(None, description="Key name")
    keys: Optional[List[str]] = Field(None, description="Key combination")
    text: Optional[str] = Field(None, description="Text to type")
    modifiers: List[str] = Field(default_factory=list, description="Keyboard modifiers")
    
    # Window parameters
    window_id: Optional[int] = Field(None, description="Window ID")
    window_title: Optional[str] = Field(None, description="Window title")
    
    # Application parameters
    app_name: Optional[str] = Field(None, description="Application name")
    app_path: Optional[str] = Field(None, description="Application path")
    app_args: Optional[List[str]] = Field(None, description="Application arguments")
    
    # File parameters
    file_path: Optional[str] = Field(None, description="File path")
    file_content: Optional[str] = Field(None, description="File content")
    
    # Wait parameters
    wait_time: Optional[float] = Field(None, description="Wait time in seconds")
    wait_condition: Optional[str] = Field(None, description="Wait condition")
    
    # Additional parameters
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")
    
    def get_mouse_event(self) -> Optional[MouseEvent]:
        """Get mouse event data if applicable."""
        if self.type in [
            DesktopActionType.MOUSE_CLICK,
            DesktopActionType.MOUSE_DOUBLE_CLICK,
            DesktopActionType.MOUSE_RIGHT_CLICK,
            DesktopActionType.MOUSE_MOVE,
            DesktopActionType.MOUSE_DRAG,
        ]:
            return MouseEvent(
                x=self.x or 0,
                y=self.y or 0,
                button=self.button,
                clicks=self.clicks,
                modifiers=self.modifiers,
            )
        return None
    
    def get_keyboard_event(self) -> Optional[KeyboardEvent]:
        """Get keyboard event data if applicable."""
        if self.type in [
            DesktopActionType.KEY_PRESS,
            DesktopActionType.KEY_RELEASE,
            DesktopActionType.KEY_COMBINATION,
            DesktopActionType.TYPE_TEXT,
        ]:
            return KeyboardEvent(
                key=self.key or "",
                modifiers=self.modifiers,
                text=self.text,
            )
        return None


class DesktopEvent(BaseModel):
    """Desktop event model."""
    id: UUID = Field(default_factory=uuid4, description="Event ID")
    type: DesktopEventType = Field(..., description="Event type")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    
    # Event data
    x: Optional[int] = Field(None, description="X coordinate")
    y: Optional[int] = Field(None, description="Y coordinate")
    button: Optional[MouseButton] = Field(None, description="Mouse button")
    key: Optional[str] = Field(None, description="Key name")
    text: Optional[str] = Field(None, description="Text content")
    window_info: Optional[WindowInfo] = Field(None, description="Window information")
    app_name: Optional[str] = Field(None, description="Application name")
    file_path: Optional[str] = Field(None, description="File path")
    error_message: Optional[str] = Field(None, description="Error message")
    
    # Additional event data
    data: Dict[str, Any] = Field(default_factory=dict, description="Additional event data")


class DesktopResponse(BaseModel):
    """Desktop action response model."""
    id: UUID = Field(default_factory=uuid4, description="Response ID")
    action_id: UUID = Field(..., description="Related action ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    success: bool = Field(..., description="Whether action was successful")
    
    # Response data
    message: Optional[str] = Field(None, description="Response message")
    error: Optional[str] = Field(None, description="Error message")
    data: Dict[str, Any] = Field(default_factory=dict, description="Response data")
    
    # Screenshot data
    screenshot: Optional[DesktopScreenshot] = Field(None, description="Screenshot taken")
    
    # Window data
    windows: List[DesktopWindow] = Field(default_factory=list, description="Window information")
    
    # File data
    file_content: Optional[str] = Field(None, description="File content")
    file_list: Optional[List[str]] = Field(None, description="File list")
    
    # Clipboard data
    clipboard_content: Optional[str] = Field(None, description="Clipboard content")
    
    # System data
    system_info: Dict[str, Any] = Field(default_factory=dict, description="System information")
    
    # Performance data
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    
    @classmethod
    def success_response(
        cls,
        action_id: UUID,
        message: str = "Action completed successfully",
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> "DesktopResponse":
        """Create a success response."""
        return cls(
            action_id=action_id,
            success=True,
            message=message,
            data=data or {},
            **kwargs,
        )
    
    @classmethod
    def error_response(
        cls,
        action_id: UUID,
        error: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> "DesktopResponse":
        """Create an error response."""
        return cls(
            action_id=action_id,
            success=False,
            error=error,
            data=data or {},
            **kwargs,
        )


# Update forward references
DesktopWindow.model_rebuild()