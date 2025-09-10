"""Task-related Pydantic schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from ..shared.task_types import TaskStatus, TaskPriority, TaskType


class TaskBase(BaseModel):
    """Base task schema with common fields."""
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, max_length=2000, description="Task description")
    task_type: TaskType = Field(default=TaskType.CUSTOM, description="Type of task")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    task_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    tags: Optional[List[str]] = Field(default_factory=list, description="Task tags")
    estimated_duration_minutes: Optional[int] = Field(None, ge=1, description="Estimated duration in minutes")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    timeout_seconds: Optional[int] = Field(None, ge=1, description="Task timeout in seconds")


class TaskCreate(TaskBase):
    """Schema for creating a new task."""
    input_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Input data for the task")
    parent_task_id: Optional[UUID] = Field(None, description="Parent task ID for subtasks")


class TaskUpdate(BaseModel):
    """Schema for updating an existing task."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    task_type: Optional[TaskType] = None
    priority: Optional[TaskPriority] = None
    task_metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=1)
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    timeout_seconds: Optional[int] = Field(None, ge=1)
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    progress_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    current_step: Optional[str] = None
    total_steps: Optional[int] = Field(None, ge=1)


class TaskResponse(TaskBase):
    """Schema for task responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    status: TaskStatus
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    progress_percentage: float = 0.0
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    resumed_at: Optional[datetime] = None
    
    # Relationships
    parent_task_id: Optional[UUID] = None
    
    # Computed properties
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate task duration in seconds."""
        if self.started_at:
            end_time = self.completed_at or self.failed_at or self.cancelled_at or datetime.utcnow()
            return (end_time - self.started_at).total_seconds()
        return None
    
    @property
    def is_active(self) -> bool:
        """Check if task is currently active."""
        return self.status in [TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.PAUSED]
    
    @property
    def is_completed(self) -> bool:
        """Check if task is completed (success or failure)."""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]


class TaskListResponse(BaseModel):
    """Schema for paginated task list responses."""
    tasks: List[TaskResponse]
    total: int = Field(..., ge=0, description="Total number of tasks")
    skip: int = Field(..., ge=0, description="Number of tasks skipped")
    limit: int = Field(..., ge=1, description="Number of tasks returned")
    has_more: bool = Field(..., description="Whether there are more tasks available")
    
    @property
    def page(self) -> int:
        """Calculate current page number (1-based)."""
        return (self.skip // self.limit) + 1 if self.limit > 0 else 1
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return (self.total + self.limit - 1) // self.limit if self.limit > 0 else 1


class TaskStats(BaseModel):
    """Schema for task statistics."""
    total_tasks: int = 0
    pending_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    paused_tasks: int = 0
    
    average_duration_seconds: Optional[float] = None
    success_rate: float = Field(0.0, ge=0.0, le=1.0)
    
    tasks_by_type: Dict[str, int] = Field(default_factory=dict)
    tasks_by_priority: Dict[str, int] = Field(default_factory=dict)
    
    @property
    def completion_rate(self) -> float:
        """Calculate completion rate (completed / total)."""
        return self.completed_tasks / self.total_tasks if self.total_tasks > 0 else 0.0
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate (failed / total)."""
        return self.failed_tasks / self.total_tasks if self.total_tasks > 0 else 0.0


class TaskAction(BaseModel):
    """Schema for task actions (start, pause, resume, cancel)."""
    action: str = Field(..., pattern=r"^(start|pause|resume|cancel)$")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for the action")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TaskProgress(BaseModel):
    """Schema for task progress updates."""
    progress_percentage: float = Field(..., ge=0.0, le=100.0)
    current_step: Optional[str] = Field(None, max_length=255)
    total_steps: Optional[int] = Field(None, ge=1)
    message: Optional[str] = Field(None, max_length=500)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TaskWithMessages(TaskResponse):
    """Schema for task responses that include messages."""
    messages: List["MessageResponse"] = Field(default_factory=list, description="Task messages")