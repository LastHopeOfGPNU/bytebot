"""Message-related Pydantic schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from ..shared.task_types import Role
from ..shared.message_content import MessageContentBlock


class MessageBase(BaseModel):
    """Base message schema with common fields."""
    role: Role = Field(..., description="Message role (user, assistant, system, tool)")
    content: List[MessageContentBlock] = Field(..., description="Message content blocks")
    message_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    task_id: UUID = Field(..., description="Associated task ID")
    parent_message_id: Optional[UUID] = Field(None, description="Parent message ID for threaded conversations")
    model_name: Optional[str] = Field(None, max_length=100, description="AI model used")
    model_provider: Optional[str] = Field(None, max_length=50, description="AI model provider")
    model_version: Optional[str] = Field(None, max_length=50, description="AI model version")


class MessageUpdate(BaseModel):
    """Schema for updating an existing message."""
    content: Optional[List[MessageContentBlock]] = None
    message_metadata: Optional[Dict[str, Any]] = None
    model_name: Optional[str] = Field(None, max_length=100)
    model_provider: Optional[str] = Field(None, max_length=50)
    model_version: Optional[str] = Field(None, max_length=50)
    input_tokens: Optional[int] = Field(None, ge=0)
    output_tokens: Optional[int] = Field(None, ge=0)
    processing_time_ms: Optional[int] = Field(None, ge=0)
    is_processed: Optional[bool] = None
    processing_error: Optional[str] = None


class MessageResponse(MessageBase):
    """Schema for message responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    task_id: UUID
    parent_message_id: Optional[UUID] = None
    
    # AI model information
    model_name: Optional[str] = None
    model_provider: Optional[str] = None
    model_version: Optional[str] = None
    
    # Token usage
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    
    # Processing information
    processing_time_ms: Optional[int] = None
    is_processed: bool = False
    processing_error: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    
    # Computed properties
    @property
    def total_tokens(self) -> int:
        """Calculate total tokens used."""
        input_tokens = self.input_tokens or 0
        output_tokens = self.output_tokens or 0
        return input_tokens + output_tokens
    
    @property
    def text_content(self) -> str:
        """Extract plain text content from message blocks."""
        text_parts = []
        for block in self.content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        return "\n".join(text_parts)
    
    @property
    def has_tool_use(self) -> bool:
        """Check if message contains tool use blocks."""
        return any(
            isinstance(block, dict) and block.get("type") == "tool_use"
            for block in self.content
        )
    
    @property
    def has_images(self) -> bool:
        """Check if message contains image blocks."""
        return any(
            isinstance(block, dict) and block.get("type") == "image"
            for block in self.content
        )
    
    @property
    def word_count(self) -> int:
        """Calculate word count of text content."""
        return len(self.text_content.split()) if self.text_content else 0


class MessageListResponse(BaseModel):
    """Schema for paginated message list responses."""
    messages: List[MessageResponse]
    total: int = Field(..., ge=0, description="Total number of messages")
    skip: int = Field(..., ge=0, description="Number of messages skipped")
    limit: int = Field(..., ge=1, description="Number of messages returned")
    has_more: bool = Field(..., description="Whether there are more messages available")
    
    @property
    def page(self) -> int:
        """Calculate current page number (1-based)."""
        return (self.skip // self.limit) + 1 if self.limit > 0 else 1
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return (self.total + self.limit - 1) // self.limit if self.limit > 0 else 1


class MessageStats(BaseModel):
    """Schema for message statistics."""
    total_messages: int = 0
    messages_by_role: Dict[str, int] = Field(default_factory=dict)
    messages_by_task: Dict[str, int] = Field(default_factory=dict)
    
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    
    average_processing_time_ms: Optional[float] = None
    average_tokens_per_message: float = 0.0
    
    processed_messages: int = 0
    failed_messages: int = 0
    
    @property
    def processing_success_rate(self) -> float:
        """Calculate processing success rate."""
        return self.processed_messages / self.total_messages if self.total_messages > 0 else 0.0
    
    @property
    def processing_failure_rate(self) -> float:
        """Calculate processing failure rate."""
        return self.failed_messages / self.total_messages if self.total_messages > 0 else 0.0


class MessageContentFilter(BaseModel):
    """Schema for filtering message content."""
    content_type: Optional[str] = Field(None, description="Filter by content type")
    has_images: Optional[bool] = Field(None, description="Filter messages with images")
    has_tool_use: Optional[bool] = Field(None, description="Filter messages with tool use")
    min_word_count: Optional[int] = Field(None, ge=0, description="Minimum word count")
    max_word_count: Optional[int] = Field(None, ge=0, description="Maximum word count")
    search_text: Optional[str] = Field(None, max_length=500, description="Search in text content")


class MessageTokenUsage(BaseModel):
    """Schema for message token usage updates."""
    input_tokens: int = Field(..., ge=0, description="Number of input tokens")
    output_tokens: int = Field(..., ge=0, description="Number of output tokens")
    processing_time_ms: Optional[int] = Field(None, ge=0, description="Processing time in milliseconds")
    model_name: Optional[str] = Field(None, max_length=100, description="AI model used")
    model_provider: Optional[str] = Field(None, max_length=50, description="AI model provider")
    
    @property
    def total_tokens(self) -> int:
        """Calculate total tokens."""
        return self.input_tokens + self.output_tokens


class MessageProcessingStatus(BaseModel):
    """Schema for message processing status updates."""
    is_processed: bool = Field(..., description="Whether message is processed")
    processing_error: Optional[str] = Field(None, max_length=1000, description="Processing error message")
    processing_time_ms: Optional[int] = Field(None, ge=0, description="Processing time in milliseconds")
    processed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")