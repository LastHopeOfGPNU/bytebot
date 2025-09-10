"""Summary service for business logic operations."""

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
from ..models.summary import Summary
from ..models.task import Task
from ..schemas.summary import SummaryCreate, SummaryUpdate
from ..shared.summary_types import SummaryType, SummaryStatus

logger = get_logger(__name__)


class SummaryService:
    """Service for summary-related operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_summary(self, summary_data: SummaryCreate) -> Summary:
        """Create a new summary."""
        logger.info(f"Creating new summary for task {summary_data.task_id}")
        
        # Validate task exists
        task_result = await self.db.execute(
            select(Task).where(Task.id == summary_data.task_id)
        )
        task = task_result.scalar_one_or_none()
        if not task:
            raise BytebotNotFoundException(f"Task {summary_data.task_id} not found")
        
        # Validate parent summary if specified
        if summary_data.parent_summary_id:
            parent_summary = await self.get_summary(summary_data.parent_summary_id)
            if not parent_summary:
                raise BytebotNotFoundException(f"Parent summary {summary_data.parent_summary_id} not found")
        
        # Create summary instance
        summary = Summary(
            task_id=summary_data.task_id,
            title=summary_data.title,
            content=summary_data.content,
            type=summary_data.type,
            metadata=summary_data.metadata,
            parent_summary_id=summary_data.parent_summary_id,
            model_name=summary_data.model_name,
            model_provider=summary_data.model_provider,
            model_version=summary_data.model_version,
        )
        
        self.db.add(summary)
        await self.db.commit()
        await self.db.refresh(summary)
        
        logger.info(f"Created summary {summary.id} successfully")
        return summary
    
    async def get_summary(self, summary_id: UUID) -> Optional[Summary]:
        """Get a summary by ID."""
        result = await self.db.execute(
            select(Summary)
            .options(
                selectinload(Summary.task),
                selectinload(Summary.child_summaries),
            )
            .where(Summary.id == summary_id)
        )
        return result.scalar_one_or_none()
    
    async def list_summaries(
        self,
        skip: int = 0,
        limit: int = 50,
        task_id: Optional[UUID] = None,
        type: Optional[SummaryType] = None,
        status: Optional[SummaryStatus] = None,
        search: Optional[str] = None,
        parent_summary_id: Optional[UUID] = None,
        min_quality_score: Optional[float] = None,
    ) -> Tuple[List[Summary], int]:
        """List summaries with filtering and pagination."""
        query = select(Summary)
        count_query = select(func.count(Summary.id))
        
        # Apply filters
        conditions = []
        
        if task_id is not None:
            conditions.append(Summary.task_id == task_id)
        
        if type is not None:
            conditions.append(Summary.type == type)
        
        if status is not None:
            conditions.append(Summary.status == status)
        
        if parent_summary_id is not None:
            conditions.append(Summary.parent_summary_id == parent_summary_id)
        
        if search:
            # Search in title and content
            search_condition = or_(
                Summary.title.ilike(f"%{search}%"),
                Summary.content.ilike(f"%{search}%")
            )
            conditions.append(search_condition)
        
        if min_quality_score is not None:
            # This would require calculating the average quality score
            # For now, we'll use a simple approach
            conditions.append(
                func.coalesce(
                    (Summary.quality_scores['clarity'].astext.cast(func.numeric()) +
                     Summary.quality_scores['completeness'].astext.cast(func.numeric()) +
                     Summary.quality_scores['accuracy'].astext.cast(func.numeric()) +
                     Summary.quality_scores['relevance'].astext.cast(func.numeric())) / 4,
                    0
                ) >= min_quality_score
            )
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # Apply ordering and pagination
        query = query.order_by(desc(Summary.created_at)).offset(skip).limit(limit)
        
        # Execute queries
        result = await self.db.execute(query)
        summaries = result.scalars().all()
        
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()
        
        return list(summaries), total
    
    async def update_summary(self, summary_id: UUID, summary_data: SummaryUpdate) -> Optional[Summary]:
        """Update a summary."""
        summary = await self.get_summary(summary_id)
        if not summary:
            return None
        
        logger.info(f"Updating summary {summary_id}")
        
        # Update fields
        update_data = summary_data.model_dump(exclude_unset=True)
        summary.update_from_dict(update_data)
        
        await self.db.commit()
        await self.db.refresh(summary)
        
        logger.info(f"Updated summary {summary_id} successfully")
        return summary
    
    async def delete_summary(self, summary_id: UUID) -> bool:
        """Delete a summary."""
        summary = await self.get_summary(summary_id)
        if not summary:
            return False
        
        logger.info(f"Deleting summary {summary_id}")
        
        # Soft delete
        summary.soft_delete()
        await self.db.commit()
        
        logger.info(f"Deleted summary {summary_id} successfully")
        return True
    
    async def approve_summary(self, summary_id: UUID) -> Optional[Summary]:
        """Approve a summary."""
        summary = await self.get_summary(summary_id)
        if not summary:
            return None
        
        logger.info(f"Approving summary {summary_id}")
        
        summary.approve()
        await self.db.commit()
        await self.db.refresh(summary)
        
        return summary
    
    async def archive_summary(self, summary_id: UUID) -> Optional[Summary]:
        """Archive a summary."""
        summary = await self.get_summary(summary_id)
        if not summary:
            return None
        
        logger.info(f"Archiving summary {summary_id}")
        
        summary.archive()
        await self.db.commit()
        await self.db.refresh(summary)
        
        return summary
    
    async def update_quality_scores(
        self,
        summary_id: UUID,
        clarity: Optional[float] = None,
        completeness: Optional[float] = None,
        accuracy: Optional[float] = None,
        relevance: Optional[float] = None,
    ) -> Optional[Summary]:
        """Update quality scores for a summary."""
        summary = await self.get_summary(summary_id)
        if not summary:
            return None
        
        logger.info(f"Updating quality scores for summary {summary_id}")
        
        summary.update_quality_scores(clarity, completeness, accuracy, relevance)
        await self.db.commit()
        await self.db.refresh(summary)
        
        return summary
    
    async def update_token_usage(
        self,
        summary_id: UUID,
        input_tokens: int,
        output_tokens: int,
        processing_time_ms: Optional[int] = None,
    ) -> Optional[Summary]:
        """Update token usage for a summary."""
        summary = await self.get_summary(summary_id)
        if not summary:
            return None
        
        logger.info(f"Updating token usage for summary {summary_id}")
        
        summary.update_token_usage(input_tokens, output_tokens)
        if processing_time_ms is not None:
            summary.processing_time_ms = processing_time_ms
        
        await self.db.commit()
        await self.db.refresh(summary)
        
        return summary
    
    async def calculate_compression_ratio(self, summary_id: UUID) -> Optional[float]:
        """Calculate compression ratio for a summary."""
        summary = await self.get_summary(summary_id)
        if not summary:
            return None
        
        return summary.calculate_compression_ratio()
    
    async def create_execution_summary(
        self,
        task_id: UUID,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Summary:
        """Create an execution summary."""
        summary_data = SummaryCreate(
            task_id=task_id,
            title=title,
            content=content,
            type=SummaryType.EXECUTION,
            metadata=metadata or {},
        )
        return await self.create_summary(summary_data)
    
    async def create_error_summary(
        self,
        task_id: UUID,
        title: str,
        content: str,
        error_details: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Summary:
        """Create an error summary."""
        merged_metadata = metadata or {}
        merged_metadata.update({"error_details": error_details})
        
        summary_data = SummaryCreate(
            task_id=task_id,
            title=title,
            content=content,
            type=SummaryType.ERROR,
            metadata=merged_metadata,
        )
        return await self.create_summary(summary_data)
    
    async def create_completion_summary(
        self,
        task_id: UUID,
        title: str,
        content: str,
        completion_stats: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Summary:
        """Create a completion summary."""
        merged_metadata = metadata or {}
        merged_metadata.update({"completion_stats": completion_stats})
        
        summary_data = SummaryCreate(
            task_id=task_id,
            title=title,
            content=content,
            type=SummaryType.COMPLETION,
            metadata=merged_metadata,
        )
        return await self.create_summary(summary_data)
    
    async def get_task_summaries(
        self,
        task_id: UUID,
        type: Optional[SummaryType] = None,
        limit: int = 10,
    ) -> List[Summary]:
        """Get summaries for a specific task."""
        conditions = [Summary.task_id == task_id]
        
        if type is not None:
            conditions.append(Summary.type == type)
        
        query = (
            select(Summary)
            .where(and_(*conditions))
            .order_by(desc(Summary.created_at))
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        # Count summaries by type
        type_query = (
            select(Summary.type, func.count(Summary.id))
            .group_by(Summary.type)
        )
        type_result = await self.db.execute(type_query)
        type_counts = dict(type_result.fetchall())
        
        # Count summaries by status
        status_query = (
            select(Summary.status, func.count(Summary.id))
            .group_by(Summary.status)
        )
        status_result = await self.db.execute(status_query)
        status_counts = dict(status_result.fetchall())
        
        # Count summaries by task
        task_query = (
            select(Summary.task_id, func.count(Summary.id))
            .group_by(Summary.task_id)
            .limit(10)  # Top 10 tasks by summary count
        )
        task_result = await self.db.execute(task_query)
        task_counts = dict(task_result.fetchall())
        
        # Calculate token statistics
        token_query = (
            select(
                func.sum(Summary.input_tokens),
                func.sum(Summary.output_tokens),
                func.avg(Summary.input_tokens),
                func.avg(Summary.output_tokens),
            )
            .where(
                and_(
                    Summary.input_tokens.is_not(None),
                    Summary.output_tokens.is_not(None),
                )
            )
        )
        token_result = await self.db.execute(token_query)
        token_stats = token_result.fetchone()
        
        # Calculate quality statistics
        quality_query = (
            select(
                func.avg(
                    (Summary.quality_scores['clarity'].astext.cast(func.numeric()) +
                     Summary.quality_scores['completeness'].astext.cast(func.numeric()) +
                     Summary.quality_scores['accuracy'].astext.cast(func.numeric()) +
                     Summary.quality_scores['relevance'].astext.cast(func.numeric())) / 4
                ),
                func.count(Summary.id).filter(Summary.quality_scores.is_not(None)),
            )
        )
        quality_result = await self.db.execute(quality_query)
        quality_stats = quality_result.fetchone()
        
        # Calculate content statistics
        content_query = (
            select(
                func.avg(func.length(Summary.content)),
                func.min(func.length(Summary.content)),
                func.max(func.length(Summary.content)),
            )
        )
        content_result = await self.db.execute(content_query)
        content_stats = content_result.fetchone()
        
        total_summaries = sum(type_counts.values())
        
        return {
            "total_summaries": total_summaries,
            "type_counts": {str(k): v for k, v in type_counts.items()},
            "status_counts": {str(k): v for k, v in status_counts.items()},
            "top_tasks_by_summaries": {str(k): v for k, v in task_counts.items()},
            "token_stats": {
                "total_input_tokens": int(token_stats[0]) if token_stats[0] else 0,
                "total_output_tokens": int(token_stats[1]) if token_stats[1] else 0,
                "avg_input_tokens": float(token_stats[2]) if token_stats[2] else 0.0,
                "avg_output_tokens": float(token_stats[3]) if token_stats[3] else 0.0,
            },
            "quality_stats": {
                "avg_quality_score": float(quality_stats[0]) if quality_stats[0] else 0.0,
                "summaries_with_quality_scores": int(quality_stats[1]) if quality_stats[1] else 0,
            },
            "content_stats": {
                "avg_content_length": float(content_stats[0]) if content_stats[0] else 0.0,
                "min_content_length": int(content_stats[1]) if content_stats[1] else 0,
                "max_content_length": int(content_stats[2]) if content_stats[2] else 0,
            },
        }