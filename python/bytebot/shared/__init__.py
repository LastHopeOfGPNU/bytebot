"""Shared types and utilities for Bytebot.

This module contains shared data types, enums, and utilities that are used
across different services in the Bytebot application.
"""

# Re-export commonly used types
from .message_content import (
    MessageContentType,
    MessageContentBlock,
    TextContent,
    ImageContent,
    ToolUseContent,
    ToolResultContent,
    ThinkingContent,
)
from .computer_action import (
    ComputerAction,
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
    Coordinates,
    Button,
    Press,
)
from .task_types import (
    TaskStatus,
    TaskPriority,
    TaskType,
    Role,
)

__all__ = [
    # Message content types
    "MessageContentType",
    "MessageContentBlock",
    "TextContent",
    "ImageContent",
    "ToolUseContent",
    "ToolResultContent",
    "ThinkingContent",
    # Computer action types
    "ComputerAction",
    "MoveMouseAction",
    "ClickMouseAction",
    "DragMouseAction",
    "TypeKeysAction",
    "PressKeysAction",
    "TypeTextAction",
    "WriteFileAction",
    "ReadFileAction",
    "WaitAction",
    "ScreenshotAction",
    "Coordinates",
    "Button",
    "Press",
    # Task types
    "TaskStatus",
    "TaskPriority",
    "TaskType",
    "Role",
]