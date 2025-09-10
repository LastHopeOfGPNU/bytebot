"""Summary model for database operations."""

from typing import Optional

from sqlalchemy import JSON, String, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class Summary(Base, UUIDMixin, TimestampMixin):
    """Summary model representing a task execution summary."""
    
    # Summary title
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Summary title"
    )
    
    # Summary content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Summary content"
    )
    
    # Summary type (execution, error, completion, etc.)
    summary_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="execution",
        doc="Type of summary"
    )
    
    # Summary metadata
    summary_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        doc="Additional summary metadata"
    )
    
    # Token usage for summary generation
    input_tokens: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        doc="Number of input tokens used for summary generation"
    )
    
    output_tokens: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        doc="Number of output tokens generated for summary"
    )
    
    # Model information
    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="AI model used to generate this summary"
    )
    
    provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="AI provider (openai, anthropic, google, etc.)"
    )
    
    # Summary quality metrics
    confidence_score: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        doc="Confidence score for the summary quality (0.0-1.0)"
    )
    
    relevance_score: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        doc="Relevance score for the summary content (0.0-1.0)"
    )
    
    # Summary statistics
    original_message_count: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        doc="Number of messages summarized"
    )
    
    compression_ratio: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        doc="Compression ratio (original_length / summary_length)"
    )
    
    # Summary status
    is_approved: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        doc="Whether the summary has been approved"
    )
    
    is_archived: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        doc="Whether the summary has been archived"
    )
    
    # Relationships
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("task.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID of the associated task"
    )
    
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="summaries",
        doc="Associated task"
    )
    
    # Parent summary for hierarchical summaries
    parent_summary_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("summary.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID of the parent summary for hierarchical summaries"
    )
    
    parent_summary: Mapped[Optional["Summary"]] = relationship(
        "Summary",
        remote_side="Summary.id",
        back_populates="child_summaries",
        doc="Parent summary"
    )
    
    child_summaries: Mapped[list["Summary"]] = relationship(
        "Summary",
        back_populates="parent_summary",
        cascade="all, delete-orphan",
        doc="Child summaries"
    )
    
    def __init__(self, **kwargs):
        """Initialize summary."""
        super().__init__(**kwargs)
    
    @property
    def total_tokens(self) -> Optional[int]:
        """Get total token count (input + output)."""
        if self.input_tokens is not None and self.output_tokens is not None:
            return self.input_tokens + self.output_tokens
        return None
    
    @property
    def content_length(self) -> int:
        """Get the length of the summary content."""
        return len(self.content) if self.content else 0
    
    @property
    def word_count(self) -> int:
        """Get the word count of the summary content."""
        if not self.content:
            return 0
        return len(self.content.split())
    
    @property
    def is_high_quality(self) -> bool:
        """Check if summary is considered high quality based on scores."""
        if self.confidence_score is None or self.relevance_score is None:
            return False
        
        return (self.confidence_score >= 0.7 and 
                self.relevance_score >= 0.7)
    
    def approve(self) -> None:
        """Approve the summary."""
        self.is_approved = True
    
    def archive(self) -> None:
        """Archive the summary."""
        self.is_archived = True
    
    def unarchive(self) -> None:
        """Unarchive the summary."""
        self.is_archived = False
    
    def update_quality_scores(
        self, 
        confidence_score: Optional[float] = None,
        relevance_score: Optional[float] = None
    ) -> None:
        """Update quality scores.
        
        Args:
            confidence_score: Confidence score (0.0-1.0)
            relevance_score: Relevance score (0.0-1.0)
        """
        if confidence_score is not None:
            if not 0.0 <= confidence_score <= 1.0:
                raise ValueError("Confidence score must be between 0.0 and 1.0")
            self.confidence_score = confidence_score
        
        if relevance_score is not None:
            if not 0.0 <= relevance_score <= 1.0:
                raise ValueError("Relevance score must be between 0.0 and 1.0")
            self.relevance_score = relevance_score
    
    def update_token_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Update token usage information.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
    
    def calculate_compression_ratio(self, original_length: int) -> None:
        """Calculate and set compression ratio.
        
        Args:
            original_length: Length of the original content
        """
        if original_length > 0 and self.content_length > 0:
            self.compression_ratio = original_length / self.content_length
        else:
            self.compression_ratio = None
    
    def to_dict(self, exclude: Optional[set] = None) -> dict:
        """Convert summary to dictionary with additional computed fields."""
        result = super().to_dict(exclude=exclude)
        
        # Add computed fields
        result.update({
            "total_tokens": self.total_tokens,
            "content_length": self.content_length,
            "word_count": self.word_count,
            "is_high_quality": self.is_high_quality,
        })
        
        return result
    
    @classmethod
    def create_execution_summary(
        cls,
        task_id: str,
        title: str,
        content: str,
        message_count: Optional[int] = None,
        **kwargs
    ) -> "Summary":
        """Create an execution summary.
        
        Args:
            task_id: ID of the associated task
            title: Summary title
            content: Summary content
            message_count: Number of messages summarized
            **kwargs: Additional summary fields
        
        Returns:
            New summary instance
        """
        return cls(
            task_id=task_id,
            title=title,
            content=content,
            summary_type="execution",
            original_message_count=message_count,
            **kwargs
        )
    
    @classmethod
    def create_error_summary(
        cls,
        task_id: str,
        title: str,
        content: str,
        error_metadata: Optional[dict] = None,
        **kwargs
    ) -> "Summary":
        """Create an error summary.
        
        Args:
            task_id: ID of the associated task
            title: Summary title
            content: Summary content
            error_metadata: Error-specific metadata
            **kwargs: Additional summary fields
        
        Returns:
            New summary instance
        """
        metadata = error_metadata or {}
        
        return cls(
            task_id=task_id,
            title=title,
            content=content,
            summary_type="error",
            metadata=metadata,
            **kwargs
        )
    
    @classmethod
    def create_completion_summary(
        cls,
        task_id: str,
        title: str,
        content: str,
        **kwargs
    ) -> "Summary":
        """Create a completion summary.
        
        Args:
            task_id: ID of the associated task
            title: Summary title
            content: Summary content
            **kwargs: Additional summary fields
        
        Returns:
            New summary instance
        """
        return cls(
            task_id=task_id,
            title=title,
            content=content,
            summary_type="completion",
            **kwargs
        )
    
    def __repr__(self) -> str:
        """String representation of the summary."""
        title_preview = self.title[:30] + "..." if len(self.title) > 30 else self.title
        return f"<Summary({self.id}): {self.summary_type} - {title_preview}>"