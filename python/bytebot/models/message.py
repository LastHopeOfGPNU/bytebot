"""Message model for database operations."""

from typing import List, Optional

from sqlalchemy import JSON, String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..shared.task_types import Role
from ..shared.message_content import MessageContentBlock
from .base import Base, TimestampMixin, UUIDMixin


class Message(Base, UUIDMixin, TimestampMixin):
    """Message model representing a message in a conversation."""
    
    # Message role (user, assistant, system, tool)
    role: Mapped[Role] = mapped_column(
        SQLEnum(Role),
        nullable=False,
        doc="Role of the message sender"
    )
    
    # Message content as JSON array of content blocks
    content: Mapped[List[dict]] = mapped_column(
        JSON,
        nullable=False,
        doc="Message content blocks as JSON array"
    )
    
    # Optional message metadata
    message_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        doc="Additional message metadata"
    )
    
    # Token usage information
    input_tokens: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        doc="Number of input tokens used"
    )
    
    output_tokens: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        doc="Number of output tokens generated"
    )
    
    # Model information
    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="AI model used to generate this message"
    )
    
    provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="AI provider (openai, anthropic, google, etc.)"
    )
    
    # Message processing status
    is_processed: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        doc="Whether the message has been processed"
    )
    
    processing_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Error message if processing failed"
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
        back_populates="messages",
        doc="Associated task"
    )
    
    # Parent message for threading
    parent_message_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("message.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID of the parent message for threading"
    )
    
    parent_message: Mapped[Optional["Message"]] = relationship(
        "Message",
        remote_side="Message.id",
        back_populates="child_messages",
        doc="Parent message"
    )
    
    child_messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="parent_message",
        cascade="all, delete-orphan",
        doc="Child messages"
    )
    
    def __init__(self, **kwargs):
        """Initialize message."""
        super().__init__(**kwargs)
    
    @property
    def total_tokens(self) -> Optional[int]:
        """Get total token count (input + output)."""
        if self.input_tokens is not None and self.output_tokens is not None:
            return self.input_tokens + self.output_tokens
        return None
    
    @property
    def text_content(self) -> str:
        """Extract plain text content from message content blocks."""
        text_parts = []
        
        for block in self.content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        
        return "\n".join(text_parts)
    
    @property
    def has_tool_use(self) -> bool:
        """Check if message contains tool use content."""
        for block in self.content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                return True
        return False
    
    @property
    def has_images(self) -> bool:
        """Check if message contains image content."""
        for block in self.content:
            if isinstance(block, dict) and block.get("type") == "image":
                return True
        return False
    
    def get_tool_uses(self) -> List[dict]:
        """Get all tool use content blocks."""
        tool_uses = []
        
        for block in self.content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool_uses.append(block)
        
        return tool_uses
    
    def get_images(self) -> List[dict]:
        """Get all image content blocks."""
        images = []
        
        for block in self.content:
            if isinstance(block, dict) and block.get("type") == "image":
                images.append(block)
        
        return images
    
    def add_content_block(self, content_block: dict) -> None:
        """Add a content block to the message.
        
        Args:
            content_block: Content block to add
        """
        if not isinstance(self.content, list):
            self.content = []
        
        self.content.append(content_block)
    
    def mark_processed(self) -> None:
        """Mark message as processed."""
        self.is_processed = True
        self.processing_error = None
    
    def mark_processing_failed(self, error_message: str) -> None:
        """Mark message processing as failed.
        
        Args:
            error_message: Error message describing the failure
        """
        self.is_processed = False
        self.processing_error = error_message
    
    def update_token_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Update token usage information.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
    
    def to_dict(self, exclude: Optional[set] = None) -> dict:
        """Convert message to dictionary with additional computed fields."""
        result = super().to_dict(exclude=exclude)
        
        # Add computed fields
        result.update({
            "total_tokens": self.total_tokens,
            "text_content": self.text_content,
            "has_tool_use": self.has_tool_use,
            "has_images": self.has_images,
        })
        
        return result
    
    @classmethod
    def create_text_message(
        cls,
        task_id: str,
        role: Role,
        text: str,
        **kwargs
    ) -> "Message":
        """Create a simple text message.
        
        Args:
            task_id: ID of the associated task
            role: Message role
            text: Text content
            **kwargs: Additional message fields
        
        Returns:
            New message instance
        """
        content = [{"type": "text", "text": text}]
        
        return cls(
            task_id=task_id,
            role=role,
            content=content,
            **kwargs
        )
    
    @classmethod
    def create_tool_use_message(
        cls,
        task_id: str,
        tool_id: str,
        tool_name: str,
        tool_input: dict,
        **kwargs
    ) -> "Message":
        """Create a tool use message.
        
        Args:
            task_id: ID of the associated task
            tool_id: Tool use ID
            tool_name: Name of the tool
            tool_input: Tool input parameters
            **kwargs: Additional message fields
        
        Returns:
            New message instance
        """
        content = [{
            "type": "tool_use",
            "id": tool_id,
            "name": tool_name,
            "input": tool_input
        }]
        
        return cls(
            task_id=task_id,
            role=Role.ASSISTANT,
            content=content,
            **kwargs
        )
    
    @classmethod
    def create_tool_result_message(
        cls,
        task_id: str,
        tool_use_id: str,
        result_content: str,
        is_error: bool = False,
        **kwargs
    ) -> "Message":
        """Create a tool result message.
        
        Args:
            task_id: ID of the associated task
            tool_use_id: ID of the tool use this result corresponds to
            result_content: Tool result content
            is_error: Whether this is an error result
            **kwargs: Additional message fields
        
        Returns:
            New message instance
        """
        content = [{
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": result_content,
            "is_error": is_error
        }]
        
        return cls(
            task_id=task_id,
            role=Role.TOOL,
            content=content,
            **kwargs
        )
    
    def __repr__(self) -> str:
        """String representation of the message."""
        text_preview = self.text_content[:50] + "..." if len(self.text_content) > 50 else self.text_content
        return f"<Message({self.id}): {self.role.value} - {text_preview}>"