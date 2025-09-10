"""Summaries API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db_session
from ...core.logging import get_logger
from ...schemas.summary import (
    SummaryCreate,
    SummaryUpdate,
    SummaryResponse,
    SummaryListResponse,
)
from ...services.summary_service import SummaryService
from ...shared.task_types import TaskType

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=SummaryListResponse)
async def list_summaries(
    skip: int = Query(0, ge=0, description="Number of summaries to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of summaries to return"),
    task_id: Optional[UUID] = Query(None, description="Filter by task ID"),
    summary_type: Optional[str] = Query(None, description="Filter by summary type"),
    status: Optional[str] = Query(None, description="Filter by status (approved/archived)"),
    search: Optional[str] = Query(None, description="Search in summary content"),
    db: AsyncSession = Depends(get_db_session),
) -> SummaryListResponse:
    """List summaries with optional filtering."""
    summary_service = SummaryService(db)
    
    summaries, total = await summary_service.list_summaries(
        skip=skip,
        limit=limit,
        task_id=task_id,
        summary_type=summary_type,
        status=status,
        search=search,
    )
    
    return SummaryListResponse(
        summaries=[SummaryResponse.model_validate(summary) for summary in summaries],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/", response_model=SummaryResponse)
async def create_summary(
    summary_data: SummaryCreate,
    db: AsyncSession = Depends(get_db_session),
) -> SummaryResponse:
    """Create a new summary."""
    summary_service = SummaryService(db)
    
    summary = await summary_service.create_summary(summary_data)
    return SummaryResponse.model_validate(summary)


@router.get("/{summary_id}", response_model=SummaryResponse)
async def get_summary(
    summary_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> SummaryResponse:
    """Get a specific summary by ID."""
    summary_service = SummaryService(db)
    
    summary = await summary_service.get_summary(summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    
    return SummaryResponse.model_validate(summary)


@router.put("/{summary_id}", response_model=SummaryResponse)
async def update_summary(
    summary_id: UUID,
    summary_data: SummaryUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> SummaryResponse:
    """Update a summary."""
    summary_service = SummaryService(db)
    
    summary = await summary_service.update_summary(summary_id, summary_data)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    
    return SummaryResponse.model_validate(summary)


@router.delete("/{summary_id}")
async def delete_summary(
    summary_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Delete a summary."""
    summary_service = SummaryService(db)
    
    success = await summary_service.delete_summary(summary_id)
    if not success:
        raise HTTPException(status_code=404, detail="Summary not found")
    
    return {"message": "Summary deleted successfully"}


@router.post("/{summary_id}/approve")
async def approve_summary(
    summary_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Approve a summary."""
    summary_service = SummaryService(db)
    
    summary = await summary_service.get_summary(summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    
    summary.approve()
    await summary_service.update_summary(summary_id, {})
    
    return {"message": "Summary approved successfully"}


@router.post("/{summary_id}/archive")
async def archive_summary(
    summary_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Archive a summary."""
    summary_service = SummaryService(db)
    
    summary = await summary_service.get_summary(summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    
    summary.archive()
    await summary_service.update_summary(summary_id, {})
    
    return {"message": "Summary archived successfully"}


@router.get("/{summary_id}/quality")
async def get_summary_quality(
    summary_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get quality metrics for a summary."""
    summary_service = SummaryService(db)
    
    summary = await summary_service.get_summary(summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    
    return {
        "summary_id": str(summary_id),
        "quality_score": summary.quality_score,
        "relevance_score": summary.relevance_score,
        "coherence_score": summary.coherence_score,
        "is_high_quality": summary.is_high_quality,
        "content_length": summary.content_length,
        "word_count": summary.word_count,
    }


@router.put("/{summary_id}/quality")
async def update_summary_quality(
    summary_id: UUID,
    quality_score: Optional[float] = Query(None, ge=0.0, le=1.0),
    relevance_score: Optional[float] = Query(None, ge=0.0, le=1.0),
    coherence_score: Optional[float] = Query(None, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Update quality scores for a summary."""
    summary_service = SummaryService(db)
    
    summary = await summary_service.get_summary(summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    
    summary.update_quality_scores(
        quality_score=quality_score,
        relevance_score=relevance_score,
        coherence_score=coherence_score,
    )
    await summary_service.update_summary(summary_id, {})
    
    return {
        "message": "Quality scores updated",
        "quality_score": summary.quality_score,
        "relevance_score": summary.relevance_score,
        "coherence_score": summary.coherence_score,
    }


@router.get("/{summary_id}/compression")
async def get_summary_compression(
    summary_id: UUID,
    original_length: int = Query(..., gt=0, description="Original content length"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Calculate compression ratio for a summary."""
    summary_service = SummaryService(db)
    
    summary = await summary_service.get_summary(summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    
    compression_ratio = summary.calculate_compression_ratio(original_length)
    
    return {
        "summary_id": str(summary_id),
        "original_length": original_length,
        "summary_length": summary.content_length,
        "compression_ratio": compression_ratio,
        "compression_percentage": f"{(1 - compression_ratio) * 100:.1f}%",
    }


@router.put("/{summary_id}/token-usage")
async def update_summary_token_usage(
    summary_id: UUID,
    input_tokens: int,
    output_tokens: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Update token usage for a summary."""
    summary_service = SummaryService(db)
    
    summary = await summary_service.get_summary(summary_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    
    summary.update_token_usage(input_tokens, output_tokens)
    await summary_service.update_summary(summary_id, {})
    
    return {
        "message": "Token usage updated",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


@router.get("/task/{task_id}", response_model=SummaryListResponse)
async def get_task_summaries(
    task_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    summary_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
) -> SummaryListResponse:
    """Get all summaries for a specific task."""
    summary_service = SummaryService(db)
    
    summaries, total = await summary_service.list_summaries(
        skip=skip,
        limit=limit,
        task_id=task_id,
        summary_type=summary_type,
    )
    
    return SummaryListResponse(
        summaries=[SummaryResponse.model_validate(summary) for summary in summaries],
        total=total,
        skip=skip,
        limit=limit,
    )