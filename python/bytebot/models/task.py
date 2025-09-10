"""Task model for database operations."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, String, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..shared.task_types import TaskStatus, TaskPriority, TaskType
from .base import Base, TimestampMixin, UUIDMixin


class Task(Base, UUIDMixin, TimestampMixin):
    """Task model representing a task in the system."""
    
    # Basic task information
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Task title"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed task description"
    )
    
    # Task status and priority
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus),
        nullable=False,
        default=TaskStatus.PENDING,
        doc="Current task status"
    )
    
    priority: Mapped[TaskPriority] = mapped_column(
        SQLEnum(TaskPriority),
        nullable=False,
        default=TaskPriority.MEDIUM,
        doc="Task priority level"
    )
    
    task_type: Mapped[TaskType] = mapped_column(
        SQLEnum(TaskType),
        nullable=False,
        default=TaskType.COMPUTER_USE,
        doc="Type of task"
    )
    
    # Task execution details
    input_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        doc="Input data for the task"
    )
    
    output_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        doc="Output data from the task"
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Error message if task failed"
    )
    
    # Task timing
    started_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Timestamp when task execution started"
    )
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
        doc="Timestamp when task execution completed"
    )
    
    # Task metadata
    task_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        doc="Additional task metadata"
    )
    
    # Progress tracking
    progress_percentage: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        default=0,
        doc="Task completion percentage (0-100)"
    )
    
    # Relationships
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="task",
        cascade="all, delete-orphan",
        doc="Messages associated with this task"
    )
    
    summaries: Mapped[List["Summary"]] = relationship(
        "Summary",
        back_populates="task",
        cascade="all, delete-orphan",
        doc="Summaries associated with this task"
    )
    
    def __init__(self, **kwargs):
        """Initialize task with default values."""
        super().__init__(**kwargs)
    
    @property
    def is_running(self) -> bool:
        """Check if task is currently running."""
        return self.status == TaskStatus.RUNNING
    
    @property
    def is_completed(self) -> bool:
        """Check if task is completed (successfully or failed)."""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
    
    @property
    def is_pending(self) -> bool:
        """Check if task is pending execution."""
        return self.status == TaskStatus.PENDING
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get task duration in seconds if completed."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def start(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.progress_percentage = 0
    
    def complete(self, output_data: Optional[dict] = None) -> None:
        """Mark task as completed successfully."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.progress_percentage = 100
        if output_data is not None:
            self.output_data = output_data
    
    def fail(self, error_message: str, output_data: Optional[dict] = None) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        if output_data is not None:
            self.output_data = output_data
    
    def cancel(self) -> None:
        """Mark task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.utcnow()
    
    def pause(self) -> None:
        """Mark task as paused."""
        if self.status == TaskStatus.RUNNING:
            self.status = TaskStatus.PAUSED
    
    def resume(self) -> None:
        """Resume a paused task."""
        if self.status == TaskStatus.PAUSED:
            self.status = TaskStatus.RUNNING
    
    def update_progress(self, percentage: int) -> None:
        """Update task progress percentage.
        
        Args:
            percentage: Progress percentage (0-100)
        """
        if 0 <= percentage <= 100:
            self.progress_percentage = percentage
        else:
            raise ValueError("Progress percentage must be between 0 and 100")
    
    def to_dict(self, exclude: Optional[set] = None) -> dict:
        """Convert task to dictionary with additional computed fields."""
        result = super().to_dict(exclude=exclude)
        
        # Add computed fields
        result.update({
            "is_running": self.is_running,
            "is_completed": self.is_completed,
            "is_pending": self.is_pending,
            "duration_seconds": self.duration_seconds,
        })
        
        return result
    
    def __repr__(self) -> str:
        """String representation of the task."""
        return f"<Task({self.id}): {self.title} - {self.status.value}>"