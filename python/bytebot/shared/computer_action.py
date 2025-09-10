"""Computer action types and models."""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, validator


class Button(str, Enum):
    """Mouse button types."""
    
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class Press(str, Enum):
    """Key press types."""
    
    # Modifier keys
    CTRL = "ctrl"
    ALT = "alt"
    SHIFT = "shift"
    CMD = "cmd"
    META = "meta"
    
    # Function keys
    F1 = "f1"
    F2 = "f2"
    F3 = "f3"
    F4 = "f4"
    F5 = "f5"
    F6 = "f6"
    F7 = "f7"
    F8 = "f8"
    F9 = "f9"
    F10 = "f10"
    F11 = "f11"
    F12 = "f12"
    
    # Navigation keys
    ENTER = "enter"
    RETURN = "return"
    TAB = "tab"
    SPACE = "space"
    BACKSPACE = "backspace"
    DELETE = "delete"
    ESCAPE = "escape"
    HOME = "home"
    END = "end"
    PAGE_UP = "pageup"
    PAGE_DOWN = "pagedown"
    
    # Arrow keys
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    
    # Number keys
    NUM_0 = "0"
    NUM_1 = "1"
    NUM_2 = "2"
    NUM_3 = "3"
    NUM_4 = "4"
    NUM_5 = "5"
    NUM_6 = "6"
    NUM_7 = "7"
    NUM_8 = "8"
    NUM_9 = "9"
    
    # Letter keys (lowercase)
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    E = "e"
    F = "f"
    G = "g"
    H = "h"
    I = "i"
    J = "j"
    K = "k"
    L = "l"
    M = "m"
    N = "n"
    O = "o"
    P = "p"
    Q = "q"
    R = "r"
    S = "s"
    T = "t"
    U = "u"
    V = "v"
    W = "w"
    X = "x"
    Y = "y"
    Z = "z"


class Coordinates(BaseModel):
    """Screen coordinates."""
    
    x: int = Field(..., description="X coordinate")
    y: int = Field(..., description="Y coordinate")
    
    @validator("x", "y")
    def validate_coordinates(cls, v: int) -> int:
        """Validate coordinates are non-negative."""
        if v < 0:
            raise ValueError("Coordinates must be non-negative")
        return v


class MoveMouseAction(BaseModel):
    """Move mouse to specific coordinates."""
    
    type: Literal["move_mouse"] = "move_mouse"
    coordinate: Coordinates = Field(..., description="Target coordinates")
    duration: Optional[float] = Field(
        default=None,
        description="Duration of movement in seconds",
        ge=0.0
    )


class ClickMouseAction(BaseModel):
    """Click mouse at specific coordinates."""
    
    type: Literal["click_mouse"] = "click_mouse"
    coordinate: Coordinates = Field(..., description="Click coordinates")
    button: Button = Field(default=Button.LEFT, description="Mouse button to click")
    click_count: int = Field(default=1, description="Number of clicks", ge=1, le=3)


class DragMouseAction(BaseModel):
    """Drag mouse from one coordinate to another."""
    
    type: Literal["drag_mouse"] = "drag_mouse"
    start_coordinate: Coordinates = Field(..., description="Start coordinates")
    end_coordinate: Coordinates = Field(..., description="End coordinates")
    button: Button = Field(default=Button.LEFT, description="Mouse button to drag with")
    duration: Optional[float] = Field(
        default=None,
        description="Duration of drag in seconds",
        ge=0.0
    )


class TypeKeysAction(BaseModel):
    """Type specific keys (for key combinations and special keys)."""
    
    type: Literal["type_keys"] = "type_keys"
    keys: List[Union[Press, str]] = Field(
        ...,
        description="List of keys to press",
        min_items=1
    )
    delay: Optional[float] = Field(
        default=None,
        description="Delay between key presses in seconds",
        ge=0.0
    )


class PressKeysAction(BaseModel):
    """Press and hold key combination."""
    
    type: Literal["press_keys"] = "press_keys"
    keys: List[Union[Press, str]] = Field(
        ...,
        description="List of keys to press simultaneously",
        min_items=1
    )
    hold_duration: Optional[float] = Field(
        default=None,
        description="Duration to hold keys in seconds",
        ge=0.0
    )


class TypeTextAction(BaseModel):
    """Type plain text."""
    
    type: Literal["type_text"] = "type_text"
    text: str = Field(..., description="Text to type")
    delay: Optional[float] = Field(
        default=None,
        description="Delay between characters in seconds",
        ge=0.0
    )


class WriteFileAction(BaseModel):
    """Write content to a file."""
    
    type: Literal["write_file"] = "write_file"
    file_path: str = Field(..., description="Path to the file")
    content: str = Field(..., description="Content to write")
    encoding: str = Field(default="utf-8", description="File encoding")
    create_dirs: bool = Field(
        default=True,
        description="Create parent directories if they don't exist"
    )


class ReadFileAction(BaseModel):
    """Read content from a file."""
    
    type: Literal["read_file"] = "read_file"
    file_path: str = Field(..., description="Path to the file")
    encoding: str = Field(default="utf-8", description="File encoding")
    max_size_mb: Optional[int] = Field(
        default=None,
        description="Maximum file size to read in MB",
        ge=1
    )


class WaitAction(BaseModel):
    """Wait for a specified duration."""
    
    type: Literal["wait"] = "wait"
    duration: float = Field(
        ...,
        description="Duration to wait in seconds",
        ge=0.0
    )


class ScreenshotAction(BaseModel):
    """Take a screenshot."""
    
    type: Literal["screenshot"] = "screenshot"
    region: Optional[Dict[str, int]] = Field(
        default=None,
        description="Region to capture (x, y, width, height)"
    )
    quality: int = Field(
        default=85,
        description="JPEG quality (1-100)",
        ge=1,
        le=100
    )
    format: Literal["png", "jpeg"] = Field(
        default="png",
        description="Image format"
    )


# Union type for all computer actions
ComputerAction = Union[
    MoveMouseAction,
    ClickMouseAction,
    DragMouseAction,
    TypeKeysAction,
    PressKeysAction,
    TypeTextAction,
    WriteFileAction,
    ReadFileAction,
    WaitAction,
    ScreenshotAction,
]


# Type aliases for better type hints
ButtonType = Literal["left", "right", "middle"]
PressType = Union[Press, str]
ComputerActionType = Literal[
    "move_mouse",
    "click_mouse",
    "drag_mouse",
    "type_keys",
    "press_keys",
    "type_text",
    "write_file",
    "read_file",
    "wait",
    "screenshot"
]


def create_computer_action(action_type: str, **kwargs: Any) -> ComputerAction:
    """Factory function to create computer actions.
    
    Args:
        action_type: Type of action to create
        **kwargs: Action-specific parameters
    
    Returns:
        Computer action instance
    
    Raises:
        ValueError: If action_type is not supported
    """
    action_map = {
        "move_mouse": MoveMouseAction,
        "click_mouse": ClickMouseAction,
        "drag_mouse": DragMouseAction,
        "type_keys": TypeKeysAction,
        "press_keys": PressKeysAction,
        "type_text": TypeTextAction,
        "write_file": WriteFileAction,
        "read_file": ReadFileAction,
        "wait": WaitAction,
        "screenshot": ScreenshotAction,
    }
    
    action_class = action_map.get(action_type)
    if action_class is None:
        raise ValueError(f"Unsupported action type: {action_type}")
    
    return action_class(**kwargs)