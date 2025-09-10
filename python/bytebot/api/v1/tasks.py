"""Tasks API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db_session
from ...core.logging import get_logger
from ...schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
    TaskWithMessages,
)
from ...schemas.message import MessageCreate, MessageResponse
from ...services.task_service import TaskService
from ...services.agent_service import AgentService
from ...shared.task_types import TaskStatus, TaskPriority, TaskType

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    """Create a new task."""
    logger.info(f"Creating new task: {task_data.title}")
    
    task_service = TaskService(db)
    agent_service = AgentService(db)
    
    # Create the task
    task = await task_service.create_task(task_data)
    
    # Start task processing in background if auto_start is True
    if task_data.auto_start:
        background_tasks.add_task(
            agent_service.process_task,
            task.id
        )
    
    return TaskResponse.model_validate(task)


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    skip: int = Query(0, ge=0, description="Number of tasks to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of tasks to return"),
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by task priority"),
    task_type: Optional[TaskType] = Query(None, description="Filter by task type"),
    search: Optional[str] = Query(None, description="Search in task title and description"),
    db: AsyncSession = Depends(get_db_session),
) -> TaskListResponse:
    """List tasks with optional filtering."""
    task_service = TaskService(db)
    
    tasks, total = await task_service.list_tasks(
        skip=skip,
        limit=limit,
        status=status,
        priority=priority,
        task_type=task_type,
        search=search,
    )
    
    return TaskListResponse(
        tasks=[TaskResponse.model_validate(task) for task in tasks],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{task_id}", response_model=TaskWithMessages)
async def get_task(
    task_id: UUID,
    include_messages: bool = Query(True, description="Include task messages"),
    db: AsyncSession = Depends(get_db_session),
) -> TaskWithMessages:
    """Get a specific task by ID."""
    task_service = TaskService(db)
    
    task = await task_service.get_task(task_id, include_messages=include_messages)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskWithMessages.model_validate(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> TaskResponse:
    """Update a task."""
    task_service = TaskService(db)
    
    task = await task_service.update_task(task_id, task_data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}")
async def delete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Delete a task."""
    task_service = TaskService(db)
    
    success = await task_service.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task deleted successfully"}


@router.post("/{task_id}/start")
async def start_task(
    task_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Start task execution."""
    task_service = TaskService(db)
    agent_service = AgentService(db)
    
    # Check if task exists and can be started
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status not in [TaskStatus.PENDING, TaskStatus.PAUSED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start task with status: {task.status}"
        )
    
    # Start task processing in background
    background_tasks.add_task(
        agent_service.process_task,
        task_id
    )
    
    return {"message": "Task started successfully"}


@router.post("/{task_id}/pause")
async def pause_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Pause task execution."""
    task_service = TaskService(db)
    
    success = await task_service.pause_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task paused successfully"}


@router.post("/{task_id}/resume")
async def resume_task(
    task_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Resume task execution."""
    task_service = TaskService(db)
    agent_service = AgentService(db)
    
    # Check if task can be resumed
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != TaskStatus.PAUSED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume task with status: {task.status}"
        )
    
    # Resume task processing in background
    background_tasks.add_task(
        agent_service.process_task,
        task_id
    )
    
    return {"message": "Task resumed successfully"}


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Cancel task execution."""
    task_service = TaskService(db)
    
    success = await task_service.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task cancelled successfully"}


@router.post("/{task_id}/messages", response_model=MessageResponse)
async def add_task_message(
    task_id: UUID,
    message_data: MessageCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Add a message to a task."""
    task_service = TaskService(db)
    agent_service = AgentService(db)
    
    # Check if task exists
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Add message to task
    message = await task_service.add_message(task_id, message_data)
    
    # If this is a user message and task is running, continue processing
    if (message_data.role.value == "user" and 
        task.status == TaskStatus.RUNNING):
        background_tasks.add_task(
            agent_service.process_task,
            task_id
        )
    
    return MessageResponse.model_validate(message)


@router.get("/{task_id}/messages", response_model=List[MessageResponse])
async def get_task_messages(
    task_id: UUID,
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(100, ge=1, le=500, description="Number of messages to return"),
    db: AsyncSession = Depends(get_db_session),
) -> List[MessageResponse]:
    """Get messages for a task."""
    task_service = TaskService(db)
    
    # Check if task exists
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    messages = await task_service.get_messages(task_id, skip=skip, limit=limit)
    
    return [MessageResponse.model_validate(message) for message in messages]


@router.get("/{task_id}/status")
async def get_task_status(
    task_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get task status and progress."""
    task_service = TaskService(db)
    
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "id": str(task.id),
        "status": task.status,
        "progress": task.progress,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "error_message": task.error_message,
        "duration": task.duration,
    }