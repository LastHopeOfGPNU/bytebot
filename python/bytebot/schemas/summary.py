"""Summary-related Pydantic schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class SummaryBase(BaseModel):
    """Base summary schema with common fields."""
    title: str = Field(..., min_length=1, max_length=255, description="Summary title")
    content: str = Field(..., min_length=1, description="Summary content")
    summary_type: str = Field(..., max_length=50, description="Type of summary")
    summary_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class SummaryCreate(SummaryBase):
    """Schema for creating a new summary."""
    task_id: UUID = Field(..., description="Associated task ID")
    parent_summary_id: Optional[UUID] = Field(None, description="Parent summary ID for hierarchical summaries")
    model_name: Optional[str] = Field(None, max_length=100, description="AI model used for generation")
    model_provider: Optional[str] = Field(None, max_length=50, description="AI model provider")
    model_version: Optional[str] = Field(None, max_length=50, description="AI model version")
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Quality score (0-1)")
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Relevance score (0-1)")
    coherence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Coherence score (0-1)")


class SummaryUpdate(BaseModel):
    """Schema for updating an existing summary."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    content: Optional[str] = Field(None, min_length=1)
    summary_type: Optional[str] = Field(None, max_length=50)
    summary_metadata: Optional[Dict[str, Any]] = None
    model_name: Optional[str] = Field(None, max_length=100)
    model_provider: Optional[str] = Field(None, max_length=50)
    model_version: Optional[str] = Field(None, max_length=50)
    input_tokens: Optional[int] = Field(None, ge=0)
    output_tokens: Optional[int] = Field(None, ge=0)
    generation_time_ms: Optional[int] = Field(None, ge=0)
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    coherence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_approved: Optional[bool] = None
    is_archived: Optional[bool] = None


class SummaryResponse(SummaryBase):
    """Schema for summary responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    task_id: UUID
    parent_summary_id: Optional[UUID] = None
    
    # AI model information
    model_name: Optional[str] = None
    model_provider: Optional[str] = None
    model_version: Optional[str] = None
    
    # Token usage
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    
    # Generation information
    generation_time_ms: Optional[int] = None
    
    # Quality metrics
    quality_score: Optional[float] = None
    relevance_score: Optional[float] = None
    coherence_score: Optional[float] = None
    
    # Statistics
    view_count: int = 0
    like_count: int = 0
    share_count: int = 0
    
    # Status
    is_approved: bool = False
    is_archived: bool = False
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    
    # Computed properties
    @property
    def total_tokens(self) -> int:
        """Calculate total tokens used."""
        input_tokens = self.input_tokens or 0
        output_tokens = self.output_tokens or 0
        return input_tokens + output_tokens
    
    @property
    def content_length(self) -> int:
        """Get content length in characters."""
        return len(self.content)
    
    @property
    def word_count(self) -> int:
        """Calculate word count of content."""
        return len(self.content.split()) if self.content else 0
    
    @property
    def is_high_quality(self) -> bool:
        """Check if summary is considered high quality."""
        if self.quality_score is None:
            return False
        return self.quality_score >= 0.8
    
    @property
    def average_score(self) -> Optional[float]:
        """Calculate average of all quality scores."""
        scores = [s for s in [self.quality_score, self.relevance_score, self.coherence_score] if s is not None]
        return sum(scores) / len(scores) if scores else None
    
    @property
    def engagement_score(self) -> float:
        """Calculate engagement score based on interactions."""
        return (self.view_count * 0.1) + (self.like_count * 1.0) + (self.share_count * 2.0)


class SummaryListResponse(BaseModel):
    """Schema for paginated summary list responses."""
    summaries: List[SummaryResponse]
    total: int = Field(..., ge=0, description="Total number of summaries")
    skip: int = Field(..., ge=0, description="Number of summaries skipped")
    limit: int = Field(..., ge=1, description="Number of summaries returned")
    has_more: bool = Field(..., description="Whether there are more summaries available")
    
    @property
    def page(self) -> int:
        """Calculate current page number (1-based)."""
        return (self.skip // self.limit) + 1 if self.limit > 0 else 1
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return (self.total + self.limit - 1) // self.limit if self.limit > 0 else 1


class SummaryStats(BaseModel):
    """Schema for summary statistics."""
    total_summaries: int = 0
    summaries_by_type: Dict[str, int] = Field(default_factory=dict)
    summaries_by_task: Dict[str, int] = Field(default_factory=dict)
    
    approved_summaries: int = 0
    archived_summaries: int = 0
    high_quality_summaries: int = 0
    
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    
    average_generation_time_ms: Optional[float] = None
    average_quality_score: Optional[float] = None
    average_content_length: float = 0.0
    average_word_count: float = 0.0
    
    total_views: int = 0
    total_likes: int = 0
    total_shares: int = 0
    
    @property
    def approval_rate(self) -> float:
        """Calculate approval rate."""
        return self.approved_summaries / self.total_summaries if self.total_summaries > 0 else 0.0
    
    @property
    def quality_rate(self) -> float:
        """Calculate high quality rate."""
        return self.high_quality_summaries / self.total_summaries if self.total_summaries > 0 else 0.0
    
    @property
    def average_engagement(self) -> float:
        """Calculate average engagement per summary."""
        if self.total_summaries == 0:
            return 0.0
        total_engagement = (self.total_views * 0.1) + (self.total_likes * 1.0) + (self.total_shares * 2.0)
        return total_engagement / self.total_summaries


class SummaryQualityUpdate(BaseModel):
    """Schema for updating summary quality scores."""
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Overall quality score")
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Relevance score")
    coherence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Coherence score")
    feedback: Optional[str] = Field(None, max_length=1000, description="Quality feedback")


class SummaryTokenUsage(BaseModel):
    """Schema for summary token usage updates."""
    input_tokens: int = Field(..., ge=0, description="Number of input tokens")
    output_tokens: int = Field(..., ge=0, description="Number of output tokens")
    generation_time_ms: Optional[int] = Field(None, ge=0, description="Generation time in milliseconds")
    model_name: Optional[str] = Field(None, max_length=100, description="AI model used")
    model_provider: Optional[str] = Field(None, max_length=50, description="AI model provider")
    
    @property
    def total_tokens(self) -> int:
        """Calculate total tokens."""
        return self.input_tokens + self.output_tokens


class SummaryCompressionInfo(BaseModel):
    """Schema for summary compression information."""
    original_length: int = Field(..., gt=0, description="Original content length")
    summary_length: int = Field(..., gt=0, description="Summary content length")
    compression_ratio: float = Field(..., gt=0.0, le=1.0, description="Compression ratio")
    compression_percentage: str = Field(..., description="Compression percentage as string")
    
    @property
    def space_saved(self) -> int:
        """Calculate characters saved."""
        return self.original_length - self.summary_length
    
    @property
    def efficiency_score(self) -> float:
        """Calculate efficiency score (higher is better compression)."""
        return 1.0 - self.compression_ratio


class SummaryFilter(BaseModel):
    """Schema for filtering summaries."""
    summary_type: Optional[str] = Field(None, description="Filter by summary type")
    min_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum quality score")
    is_approved: Optional[bool] = Field(None, description="Filter by approval status")
    is_archived: Optional[bool] = Field(None, description="Filter by archive status")
    min_word_count: Optional[int] = Field(None, ge=0, description="Minimum word count")
    max_word_count: Optional[int] = Field(None, ge=0, description="Maximum word count")
    search_text: Optional[str] = Field(None, max_length=500, description="Search in content")
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")