"""Message content types and models."""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, validator

from .computer_action import ComputerAction


class MessageContentType(str, Enum):
    """Types of message content blocks."""
    
    TEXT = "text"
    IMAGE = "image"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"
    THINKING = "thinking"


class TextContent(BaseModel):
    """Text content block."""
    
    type: Literal["text"] = "text"
    text: str = Field(..., description="Text content")


class ImageContent(BaseModel):
    """Image content block."""
    
    type: Literal["image"] = "image"
    source: Dict[str, Any] = Field(..., description="Image source data")
    alt_text: Optional[str] = Field(default=None, description="Alternative text")
    
    @validator("source")
    def validate_source(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate image source format."""
        if "type" not in v:
            raise ValueError("Image source must have 'type' field")
        
        source_type = v["type"]
        if source_type == "base64":
            if "media_type" not in v or "data" not in v:
                raise ValueError("Base64 image source must have 'media_type' and 'data' fields")
        elif source_type == "url":
            if "url" not in v:
                raise ValueError("URL image source must have 'url' field")
        else:
            raise ValueError(f"Unsupported image source type: {source_type}")
        
        return v


class ToolUseContent(BaseModel):
    """Tool use content block."""
    
    type: Literal["tool_use"] = "tool_use"
    id: str = Field(..., description="Tool use ID")
    name: str = Field(..., description="Tool name")
    input: Dict[str, Any] = Field(..., description="Tool input parameters")


class ToolResultContent(BaseModel):
    """Tool result content block."""
    
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str = Field(..., description="ID of the tool use this result corresponds to")
    content: Union[str, List[Dict[str, Any]]] = Field(
        ...,
        description="Tool result content"
    )
    is_error: bool = Field(default=False, description="Whether this is an error result")


class ThinkingContent(BaseModel):
    """Thinking content block (for internal reasoning)."""
    
    type: Literal["thinking"] = "thinking"
    content: str = Field(..., description="Thinking content")


# Computer-specific tool use content blocks
class ComputerToolUseContent(ToolUseContent):
    """Computer tool use content block."""
    
    name: Literal["computer"] = "computer"
    input: Dict[str, Any] = Field(..., description="Computer action parameters")
    
    @validator("input")
    def validate_computer_input(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate computer tool input."""
        if "action" not in v:
            raise ValueError("Computer tool input must have 'action' field")
        return v


class ScreenshotToolUseContent(ToolUseContent):
    """Screenshot tool use content block."""
    
    name: Literal["screenshot"] = "screenshot"
    input: Dict[str, Any] = Field(default_factory=dict, description="Screenshot parameters")


class MouseMoveToolUseContent(ToolUseContent):
    """Mouse move tool use content block."""
    
    name: Literal["move_mouse"] = "move_mouse"
    input: Dict[str, Any] = Field(..., description="Mouse move parameters")
    
    @validator("input")
    def validate_mouse_move_input(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate mouse move input."""
        if "coordinate" not in v:
            raise ValueError("Mouse move input must have 'coordinate' field")
        
        coordinate = v["coordinate"]
        if not isinstance(coordinate, dict) or "x" not in coordinate or "y" not in coordinate:
            raise ValueError("Coordinate must be a dict with 'x' and 'y' fields")
        
        return v


class MouseClickToolUseContent(ToolUseContent):
    """Mouse click tool use content block."""
    
    name: Literal["click_mouse"] = "click_mouse"
    input: Dict[str, Any] = Field(..., description="Mouse click parameters")
    
    @validator("input")
    def validate_mouse_click_input(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate mouse click input."""
        if "coordinate" not in v:
            raise ValueError("Mouse click input must have 'coordinate' field")
        
        coordinate = v["coordinate"]
        if not isinstance(coordinate, dict) or "x" not in coordinate or "y" not in coordinate:
            raise ValueError("Coordinate must be a dict with 'x' and 'y' fields")
        
        return v


class KeyPressToolUseContent(ToolUseContent):
    """Key press tool use content block."""
    
    name: Literal["key_press"] = "key_press"
    input: Dict[str, Any] = Field(..., description="Key press parameters")
    
    @validator("input")
    def validate_key_press_input(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate key press input."""
        if "keys" not in v:
            raise ValueError("Key press input must have 'keys' field")
        return v


class TypeTextToolUseContent(ToolUseContent):
    """Type text tool use content block."""
    
    name: Literal["type_text"] = "type_text"
    input: Dict[str, Any] = Field(..., description="Type text parameters")
    
    @validator("input")
    def validate_type_text_input(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate type text input."""
        if "text" not in v:
            raise ValueError("Type text input must have 'text' field")
        return v


class FileOperationToolUseContent(ToolUseContent):
    """File operation tool use content block."""
    
    name: Literal["file_operation"] = "file_operation"
    input: Dict[str, Any] = Field(..., description="File operation parameters")
    
    @validator("input")
    def validate_file_operation_input(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate file operation input."""
        if "operation" not in v or "file_path" not in v:
            raise ValueError("File operation input must have 'operation' and 'file_path' fields")
        return v


class TaskManagementToolUseContent(ToolUseContent):
    """Task management tool use content block."""
    
    name: Literal["task_management"] = "task_management"
    input: Dict[str, Any] = Field(..., description="Task management parameters")
    
    @validator("input")
    def validate_task_management_input(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate task management input."""
        if "action" not in v:
            raise ValueError("Task management input must have 'action' field")
        return v


# Union type for all message content blocks
MessageContentBlock = Union[
    TextContent,
    ImageContent,
    ToolUseContent,
    ToolResultContent,
    ThinkingContent,
    ComputerToolUseContent,
    ScreenshotToolUseContent,
    MouseMoveToolUseContent,
    MouseClickToolUseContent,
    KeyPressToolUseContent,
    TypeTextToolUseContent,
    FileOperationToolUseContent,
    TaskManagementToolUseContent,
]


# Type aliases
MessageContentTypeType = Literal[
    "text",
    "image",
    "tool_use",
    "tool_result",
    "thinking"
]

ToolNameType = Literal[
    "computer",
    "screenshot",
    "move_mouse",
    "click_mouse",
    "key_press",
    "type_text",
    "file_operation",
    "task_management"
]


def create_text_content(text: str) -> TextContent:
    """Create a text content block."""
    return TextContent(text=text)


def create_image_content(
    source: Dict[str, Any],
    alt_text: Optional[str] = None
) -> ImageContent:
    """Create an image content block."""
    return ImageContent(source=source, alt_text=alt_text)


def create_tool_use_content(
    tool_id: str,
    name: str,
    input_params: Dict[str, Any]
) -> ToolUseContent:
    """Create a tool use content block."""
    return ToolUseContent(id=tool_id, name=name, input=input_params)


def create_tool_result_content(
    tool_use_id: str,
    content: Union[str, List[Dict[str, Any]]],
    is_error: bool = False
) -> ToolResultContent:
    """Create a tool result content block."""
    return ToolResultContent(
        tool_use_id=tool_use_id,
        content=content,
        is_error=is_error
    )


def create_thinking_content(content: str) -> ThinkingContent:
    """Create a thinking content block."""
    return ThinkingContent(content=content)