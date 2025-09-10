"""Task-related types and enums."""

from enum import Enum
from typing import Literal


class TaskStatus(str, Enum):
    """Task execution status."""
    
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"


class TaskPriority(str, Enum):
    """Task priority levels."""
    
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskType(str, Enum):
    """Types of tasks that can be executed."""
    
    COMPUTER_USE = "COMPUTER_USE"
    TEXT_GENERATION = "TEXT_GENERATION"
    IMAGE_ANALYSIS = "IMAGE_ANALYSIS"
    FILE_OPERATION = "FILE_OPERATION"
    WEB_BROWSING = "WEB_BROWSING"
    AUTOMATION = "AUTOMATION"
    CUSTOM = "CUSTOM"


class Role(str, Enum):
    """Message roles in conversations."""
    
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


# Type aliases for better type hints
TaskStatusType = Literal[
    "PENDING",
    "RUNNING", 
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    "PAUSED"
]

TaskPriorityType = Literal[
    "LOW",
    "MEDIUM",
    "HIGH", 
    "URGENT"
]

TaskTypeType = Literal[
    "COMPUTER_USE",
    "TEXT_GENERATION",
    "IMAGE_ANALYSIS",
    "FILE_OPERATION",
    "WEB_BROWSING",
    "AUTOMATION",
    "CUSTOM"
]

RoleType = Literal[
    "user",
    "assistant",
    "system",
    "tool"
]