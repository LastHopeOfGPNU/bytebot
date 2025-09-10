"""Task service for business logic operations."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ..core.exceptions import (
    BytebotNotFoundException,
    BytebotValidationException,
    BytebotConflictException,
)
from ..core.logging import get_logger
from ..models.task import Task
from ..models.message import Message
from ..schemas.task import TaskCreate, TaskUpdate
from ..shared.task_types import TaskStatus, TaskPriority, TaskType

logger = get_logger(__name__)


class TaskService:
    """Service for task-related operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_task(self, task_data: TaskCreate) -> Task:
        """Create a new task."""
        logger.info(f"Creating new task: {task_data.title}")
        
        # Validate parent task if specified
        if task_data.parent_task_id:
            parent_task = await self.get_task(task_data.parent_task_id)
            if not parent_task:
                raise BytebotNotFoundException(f"Parent task {task_data.parent_task_id} not found")
        
        # Create task instance
        task = Task(
            title=task_data.title,
            description=task_data.description,
            task_type=task_data.task_type,
            priority=task_data.priority,
            input_data=task_data.input_data,
            metadata=task_data.metadata,
            tags=task_data.tags,
            estimated_duration_minutes=task_data.estimated_duration_minutes,
            max_retries=task_data.max_retries,
            timeout_seconds=task_data.timeout_seconds,
            parent_task_id=task_data.parent_task_id,
        )
        
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(f"Created task {task.id} successfully")
        return task
    
    async def get_task(self, task_id: UUID) -> Optional[Task]:
        """Get a task by ID."""
        result = await self.db.execute(
            select(Task)
            .options(
                selectinload(Task.messages),
                selectinload(Task.summaries),
                selectinload(Task.subtasks),
            )
            .where(Task.id == task_id)
        )
        return result.scalar_one_or_none()
    
    async def list_tasks(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[TaskStatus] = None,
        task_type: Optional[TaskType] = None,
        priority: Optional[TaskPriority] = None,
        parent_task_id: Optional[UUID] = None,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Tuple[List[Task], int]:
        """List tasks with filtering and pagination."""
        query = select(Task)
        count_query = select(func.count(Task.id))
        
        # Apply filters
        conditions = []
        
        if status is not None:
            conditions.append(Task.status == status)
        
        if task_type is not None:
            conditions.append(Task.task_type == task_type)
        
        if priority is not None:
            conditions.append(Task.priority == priority)
        
        if parent_task_id is not None:
            conditions.append(Task.parent_task_id == parent_task_id)
        
        if search:
            search_condition = or_(
                Task.title.ilike(f"%{search}%"),
                Task.description.ilike(f"%{search}%"),
            )
            conditions.append(search_condition)
        
        if tags:
            # PostgreSQL array contains operation
            for tag in tags:
                conditions.append(Task.tags.contains([tag]))
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Apply ordering and pagination
        query = query.order_by(desc(Task.created_at)).offset(skip).limit(limit)
        
        # Execute queries
        result = await self.db.execute(query)
        tasks = result.scalars().all()
        
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()
        
        return list(tasks), total
    
    async def update_task(self, task_id: UUID, task_data: TaskUpdate) -> Optional[Task]:
        """Update a task."""
        task = await self.get_task(task_id)
        if not task:
            return None
        
        logger.info(f"Updating task {task_id}")
        
        # Update fields
        update_data = task_data.model_dump(exclude_unset=True)
        task.update_from_dict(update_data)
        
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(f"Updated task {task_id} successfully")
        return task
    
    async def delete_task(self, task_id: UUID) -> bool:
        """Delete a task."""
        task = await self.get_task(task_id)
        if not task:
            return False
        
        logger.info(f"Deleting task {task_id}")
        
        # Check if task can be deleted
        if task.status == TaskStatus.RUNNING:
            raise BytebotConflictException("Cannot delete a running task")
        
        # Soft delete
        task.soft_delete()
        await self.db.commit()
        
        logger.info(f"Deleted task {task_id} successfully")
        return True
    
    async def start_task(self, task_id: UUID) -> Optional[Task]:
        """Start a task."""
        task = await self.get_task(task_id)
        if not task:
            return None
        
        logger.info(f"Starting task {task_id}")
        
        if task.status != TaskStatus.PENDING:
            raise BytebotConflictException(f"Task {task_id} cannot be started from status {task.status}")
        
        task.start()
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(f"Started task {task_id} successfully")
        return task
    
    async def pause_task(self, task_id: UUID) -> Optional[Task]:
        """Pause a task."""
        task = await self.get_task(task_id)
        if not task:
            return None
        
        logger.info(f"Pausing task {task_id}")
        
        if task.status != TaskStatus.RUNNING:
            raise BytebotConflictException(f"Task {task_id} cannot be paused from status {task.status}")
        
        task.pause()
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(f"Paused task {task_id} successfully")
        return task
    
    async def resume_task(self, task_id: UUID) -> Optional[Task]:
        """Resume a paused task."""
        task = await self.get_task(task_id)
        if not task:
            return None
        
        logger.info(f"Resuming task {task_id}")
        
        if task.status != TaskStatus.PAUSED:
            raise BytebotConflictException(f"Task {task_id} cannot be resumed from status {task.status}")
        
        task.resume()
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(f"Resumed task {task_id} successfully")
        return task
    
    async def cancel_task(self, task_id: UUID) -> Optional[Task]:
        """Cancel a task."""
        task = await self.get_task(task_id)
        if not task:
            return None
        
        logger.info(f"Cancelling task {task_id}")
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            raise BytebotConflictException(f"Task {task_id} cannot be cancelled from status {task.status}")
        
        task.cancel()
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(f"Cancelled task {task_id} successfully")
        return task
    
    async def complete_task(self, task_id: UUID, output_data: Optional[Dict[str, Any]] = None) -> Optional[Task]:
        """Complete a task."""
        task = await self.get_task(task_id)
        if not task:
            return None
        
        logger.info(f"Completing task {task_id}")
        
        if task.status != TaskStatus.RUNNING:
            raise BytebotConflictException(f"Task {task_id} cannot be completed from status {task.status}")
        
        task.complete(output_data)
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(f"Completed task {task_id} successfully")
        return task
    
    async def fail_task(self, task_id: UUID, error_message: str) -> Optional[Task]:
        """Mark a task as failed."""
        task = await self.get_task(task_id)
        if not task:
            return None
        
        logger.info(f"Failing task {task_id}: {error_message}")
        
        if task.status not in [TaskStatus.RUNNING, TaskStatus.PAUSED]:
            raise BytebotConflictException(f"Task {task_id} cannot be failed from status {task.status}")
        
        task.fail(error_message)
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.error(f"Failed task {task_id}: {error_message}")
        return task
    
    async def update_progress(self, task_id: UUID, progress: float, current_step: Optional[str] = None) -> Optional[Task]:
        """Update task progress."""
        task = await self.get_task(task_id)
        if not task:
            return None
        
        if not (0.0 <= progress <= 100.0):
            raise BytebotValidationException("Progress must be between 0 and 100")
        
        task.update_progress(progress, current_step)
        await self.db.commit()
        await self.db.refresh(task)
        
        return task
    
    async def add_message_to_task(self, task_id: UUID, message: Message) -> Optional[Task]:
        """Add a message to a task."""
        task = await self.get_task(task_id)
        if not task:
            return None
        
        message.task_id = task_id
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(task)
        
        return task
    
    async def get_task_messages(self, task_id: UUID, skip: int = 0, limit: int = 50) -> Tuple[List[Message], int]:
        """Get messages for a task."""
        query = (
            select(Message)
            .where(Message.task_id == task_id)
            .order_by(desc(Message.created_at))
            .offset(skip)
            .limit(limit)
        )
        
        count_query = select(func.count(Message.id)).where(Message.task_id == task_id)
        
        result = await self.db.execute(query)
        messages = result.scalars().all()
        
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()
        
        return list(messages), total
    
    async def get_task_stats(self) -> Dict[str, Any]:
        """Get task statistics."""
        # Count tasks by status
        status_query = (
            select(Task.status, func.count(Task.id))
            .group_by(Task.status)
        )
        status_result = await self.db.execute(status_query)
        status_counts = dict(status_result.fetchall())
        
        # Count tasks by type
        type_query = (
            select(Task.task_type, func.count(Task.id))
            .group_by(Task.task_type)
        )
        type_result = await self.db.execute(type_query)
        type_counts = dict(type_result.fetchall())
        
        # Count tasks by priority
        priority_query = (
            select(Task.priority, func.count(Task.id))
            .group_by(Task.priority)
        )
        priority_result = await self.db.execute(priority_query)
        priority_counts = dict(priority_result.fetchall())
        
        # Calculate average duration for completed tasks
        duration_query = (
            select(func.avg(
                func.extract('epoch', Task.completed_at - Task.started_at)
            ))
            .where(
                and_(
                    Task.status == TaskStatus.COMPLETED,
                    Task.started_at.is_not(None),
                    Task.completed_at.is_not(None),
                )
            )
        )
        duration_result = await self.db.execute(duration_query)
        avg_duration = duration_result.scalar()
        
        # Calculate success rate
        total_completed = status_counts.get(TaskStatus.COMPLETED, 0) + status_counts.get(TaskStatus.FAILED, 0)
        success_rate = status_counts.get(TaskStatus.COMPLETED, 0) / total_completed if total_completed > 0 else 0.0
        
        return {
            "total_tasks": sum(status_counts.values()),
            "status_counts": {str(k): v for k, v in status_counts.items()},
            "type_counts": {str(k): v for k, v in type_counts.items()},
            "priority_counts": {str(k): v for k, v in priority_counts.items()},
            "average_duration_seconds": float(avg_duration) if avg_duration else None,
            "success_rate": success_rate,
        }