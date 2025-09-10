"""Message service for business logic operations."""

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
from ..models.message import Message
from ..models.task import Task
from ..schemas.message import MessageCreate, MessageUpdate
from ..shared.task_types import Role
from ..shared.message_content import MessageContentBlock

logger = get_logger(__name__)


class MessageService:
    """Service for message-related operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_message(self, message_data: MessageCreate) -> Message:
        """Create a new message."""
        logger.info(f"Creating new message for task {message_data.task_id}")
        
        # Validate task exists
        task_result = await self.db.execute(
            select(Task).where(Task.id == message_data.task_id)
        )
        task = task_result.scalar_one_or_none()
        if not task:
            raise BytebotNotFoundException(f"Task {message_data.task_id} not found")
        
        # Validate parent message if specified
        if message_data.parent_message_id:
            parent_message = await self.get_message(message_data.parent_message_id)
            if not parent_message:
                raise BytebotNotFoundException(f"Parent message {message_data.parent_message_id} not found")
        
        # Create message instance
        message = Message(
            task_id=message_data.task_id,
            role=message_data.role,
            content=message_data.content,
            metadata=message_data.metadata,
            parent_message_id=message_data.parent_message_id,
            model_name=message_data.model_name,
            model_provider=message_data.model_provider,
            model_version=message_data.model_version,
        )
        
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        
        logger.info(f"Created message {message.id} successfully")
        return message
    
    async def get_message(self, message_id: UUID) -> Optional[Message]:
        """Get a message by ID."""
        result = await self.db.execute(
            select(Message)
            .options(
                selectinload(Message.task),
                selectinload(Message.child_messages),
            )
            .where(Message.id == message_id)
        )
        return result.scalar_one_or_none()
    
    async def list_messages(
        self,
        skip: int = 0,
        limit: int = 50,
        task_id: Optional[UUID] = None,
        role: Optional[Role] = None,
        search: Optional[str] = None,
        has_tool_use: Optional[bool] = None,
        has_images: Optional[bool] = None,
        parent_message_id: Optional[UUID] = None,
    ) -> Tuple[List[Message], int]:
        """List messages with filtering and pagination."""
        query = select(Message)
        count_query = select(func.count(Message.id))
        
        # Apply filters
        conditions = []
        
        if task_id is not None:
            conditions.append(Message.task_id == task_id)
        
        if role is not None:
            conditions.append(Message.role == role)
        
        if parent_message_id is not None:
            conditions.append(Message.parent_message_id == parent_message_id)
        
        if search:
            # Search in text content (this is a simplified search)
            # In a real implementation, you might want to use full-text search
            search_condition = Message.content.cast(str).ilike(f"%{search}%")
            conditions.append(search_condition)
        
        # Note: has_tool_use and has_images would require more complex JSON queries
        # For now, we'll skip these filters in the database query
        # and filter in Python if needed
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Apply ordering and pagination
        query = query.order_by(desc(Message.created_at)).offset(skip).limit(limit)
        
        # Execute queries
        result = await self.db.execute(query)
        messages = result.scalars().all()
        
        # Apply Python-based filters if needed
        if has_tool_use is not None or has_images is not None:
            filtered_messages = []
            for message in messages:
                if has_tool_use is not None and message.has_tool_use != has_tool_use:
                    continue
                if has_images is not None and message.has_images != has_images:
                    continue
                filtered_messages.append(message)
            messages = filtered_messages
        
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()
        
        return list(messages), total
    
    async def update_message(self, message_id: UUID, message_data: MessageUpdate) -> Optional[Message]:
        """Update a message."""
        message = await self.get_message(message_id)
        if not message:
            return None
        
        logger.info(f"Updating message {message_id}")
        
        # Update fields
        update_data = message_data.model_dump(exclude_unset=True)
        message.update_from_dict(update_data)
        
        await self.db.commit()
        await self.db.refresh(message)
        
        logger.info(f"Updated message {message_id} successfully")
        return message
    
    async def delete_message(self, message_id: UUID) -> bool:
        """Delete a message."""
        message = await self.get_message(message_id)
        if not message:
            return False
        
        logger.info(f"Deleting message {message_id}")
        
        # Soft delete
        message.soft_delete()
        await self.db.commit()
        
        logger.info(f"Deleted message {message_id} successfully")
        return True
    
    async def add_content_block(self, message_id: UUID, content_block: MessageContentBlock) -> Optional[Message]:
        """Add a content block to a message."""
        message = await self.get_message(message_id)
        if not message:
            return None
        
        logger.info(f"Adding content block to message {message_id}")
        
        message.add_content_block(content_block)
        await self.db.commit()
        await self.db.refresh(message)
        
        return message
    
    async def mark_processed(self, message_id: UUID) -> Optional[Message]:
        """Mark a message as processed."""
        message = await self.get_message(message_id)
        if not message:
            return None
        
        logger.info(f"Marking message {message_id} as processed")
        
        message.mark_processed()
        await self.db.commit()
        await self.db.refresh(message)
        
        return message
    
    async def mark_processing_failed(self, message_id: UUID, error_message: str) -> Optional[Message]:
        """Mark message processing as failed."""
        message = await self.get_message(message_id)
        if not message:
            return None
        
        logger.info(f"Marking message {message_id} processing as failed: {error_message}")
        
        message.mark_processing_failed(error_message)
        await self.db.commit()
        await self.db.refresh(message)
        
        return message
    
    async def update_token_usage(
        self,
        message_id: UUID,
        input_tokens: int,
        output_tokens: int,
        processing_time_ms: Optional[int] = None,
    ) -> Optional[Message]:
        """Update token usage for a message."""
        message = await self.get_message(message_id)
        if not message:
            return None
        
        logger.info(f"Updating token usage for message {message_id}")
        
        message.update_token_usage(input_tokens, output_tokens)
        if processing_time_ms is not None:
            message.processing_time_ms = processing_time_ms
        
        await self.db.commit()
        await self.db.refresh(message)
        
        return message
    
    async def create_text_message(
        self,
        task_id: UUID,
        role: Role,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Create a simple text message."""
        message_data = MessageCreate(
            task_id=task_id,
            role=role,
            content=[{"type": "text", "text": text}],
            metadata=metadata or {},
        )
        return await self.create_message(message_data)
    
    async def create_tool_use_message(
        self,
        task_id: UUID,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_use_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Create a tool use message."""
        content_block = {
            "type": "tool_use",
            "name": tool_name,
            "input": tool_input,
        }
        if tool_use_id:
            content_block["id"] = tool_use_id
        
        message_data = MessageCreate(
            task_id=task_id,
            role=Role.ASSISTANT,
            content=[content_block],
            metadata=metadata or {},
        )
        return await self.create_message(message_data)
    
    async def create_tool_result_message(
        self,
        task_id: UUID,
        tool_use_id: str,
        result: Any,
        is_error: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Create a tool result message."""
        content_block = {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": result,
            "is_error": is_error,
        }
        
        message_data = MessageCreate(
            task_id=task_id,
            role=Role.TOOL,
            content=[content_block],
            metadata=metadata or {},
        )
        return await self.create_message(message_data)
    
    async def get_conversation_history(
        self,
        task_id: UUID,
        limit: int = 50,
        include_system: bool = True,
    ) -> List[Message]:
        """Get conversation history for a task."""
        conditions = [Message.task_id == task_id]
        
        if not include_system:
            conditions.append(Message.role != Role.SYSTEM)
        
        query = (
            select(Message)
            .where(and_(*conditions))
            .order_by(Message.created_at)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_message_stats(self) -> Dict[str, Any]:
        """Get message statistics."""
        # Count messages by role
        role_query = (
            select(Message.role, func.count(Message.id))
            .group_by(Message.role)
        )
        role_result = await self.db.execute(role_query)
        role_counts = dict(role_result.fetchall())
        
        # Count messages by task
        task_query = (
            select(Message.task_id, func.count(Message.id))
            .group_by(Message.task_id)
            .limit(10)  # Top 10 tasks by message count
        )
        task_result = await self.db.execute(task_query)
        task_counts = dict(task_result.fetchall())
        
        # Calculate token statistics
        token_query = (
            select(
                func.sum(Message.input_tokens),
                func.sum(Message.output_tokens),
                func.avg(Message.input_tokens),
                func.avg(Message.output_tokens),
            )
            .where(
                and_(
                    Message.input_tokens.is_not(None),
                    Message.output_tokens.is_not(None),
                )
            )
        )
        token_result = await self.db.execute(token_query)
        token_stats = token_result.fetchone()
        
        # Calculate processing statistics
        processing_query = (
            select(
                func.count(Message.id).filter(Message.is_processed == True),
                func.count(Message.id).filter(Message.processing_error.is_not(None)),
                func.avg(Message.processing_time_ms),
            )
        )
        processing_result = await self.db.execute(processing_query)
        processing_stats = processing_result.fetchone()
        
        total_messages = sum(role_counts.values())
        
        return {
            "total_messages": total_messages,
            "role_counts": {str(k): v for k, v in role_counts.items()},
            "top_tasks_by_messages": {str(k): v for k, v in task_counts.items()},
            "token_stats": {
                "total_input_tokens": int(token_stats[0]) if token_stats[0] else 0,
                "total_output_tokens": int(token_stats[1]) if token_stats[1] else 0,
                "avg_input_tokens": float(token_stats[2]) if token_stats[2] else 0.0,
                "avg_output_tokens": float(token_stats[3]) if token_stats[3] else 0.0,
            },
            "processing_stats": {
                "processed_messages": int(processing_stats[0]) if processing_stats[0] else 0,
                "failed_messages": int(processing_stats[1]) if processing_stats[1] else 0,
                "avg_processing_time_ms": float(processing_stats[2]) if processing_stats[2] else 0.0,
            },
        }