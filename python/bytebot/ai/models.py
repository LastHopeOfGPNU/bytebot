"""AI models and data structures."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class AIProvider(str, Enum):
    """AI service providers."""
    CLAUDE = "claude"
    OPENAI = "openai"
    GOOGLE = "google"
    LOCAL = "local"


class AIModel(BaseModel):
    """AI model configuration."""
    id: str
    name: str
    provider: AIProvider
    max_tokens: int
    context_window: int
    input_cost_per_token: float = Field(description="Cost per input token in USD")
    output_cost_per_token: float = Field(description="Cost per output token in USD")
    supports_vision: bool = False
    supports_function_calling: bool = False
    supports_streaming: bool = False
    description: Optional[str] = None
    version: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class AIMessageRole(str, Enum):
    """AI message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class AIMessageContent(BaseModel):
    """AI message content block."""
    type: str  # text, image, tool_use, tool_result
    text: Optional[str] = None
    image_url: Optional[str] = None
    image_data: Optional[str] = None  # base64 encoded
    tool_use_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_result: Optional[Any] = None
    is_error: Optional[bool] = None


class AIMessage(BaseModel):
    """AI conversation message."""
    role: AIMessageRole
    content: List[AIMessageContent]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    token_count: Optional[int] = None
    
    @classmethod
    def create_text_message(cls, role: AIMessageRole, text: str) -> "AIMessage":
        """Create a text message."""
        return cls(
            role=role,
            content=[AIMessageContent(type="text", text=text)],
        )
    
    @classmethod
    def create_system_message(cls, text: str) -> "AIMessage":
        """Create a system message."""
        return cls.create_text_message(AIMessageRole.SYSTEM, text)
    
    @classmethod
    def create_user_message(cls, text: str) -> "AIMessage":
        """Create a user message."""
        return cls.create_text_message(AIMessageRole.USER, text)
    
    @classmethod
    def create_assistant_message(cls, text: str) -> "AIMessage":
        """Create an assistant message."""
        return cls.create_text_message(AIMessageRole.ASSISTANT, text)
    
    @classmethod
    def create_tool_use_message(
        cls,
        tool_use_id: str,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> "AIMessage":
        """Create a tool use message."""
        return cls(
            role=AIMessageRole.ASSISTANT,
            content=[
                AIMessageContent(
                    type="tool_use",
                    tool_use_id=tool_use_id,
                    tool_name=tool_name,
                    tool_input=tool_input,
                )
            ],
        )
    
    @classmethod
    def create_tool_result_message(
        cls,
        tool_use_id: str,
        tool_result: Any,
        is_error: bool = False,
    ) -> "AIMessage":
        """Create a tool result message."""
        return cls(
            role=AIMessageRole.TOOL,
            content=[
                AIMessageContent(
                    type="tool_result",
                    tool_use_id=tool_use_id,
                    tool_result=tool_result,
                    is_error=is_error,
                )
            ],
        )
    
    @classmethod
    def create_image_message(
        cls,
        role: AIMessageRole,
        text: Optional[str] = None,
        image_url: Optional[str] = None,
        image_data: Optional[str] = None,
    ) -> "AIMessage":
        """Create an image message."""
        content = []
        
        if text:
            content.append(AIMessageContent(type="text", text=text))
        
        content.append(
            AIMessageContent(
                type="image",
                image_url=image_url,
                image_data=image_data,
            )
        )
        
        return cls(role=role, content=content)
    
    def get_text_content(self) -> str:
        """Get all text content from the message."""
        text_parts = []
        for content in self.content:
            if content.type == "text" and content.text:
                text_parts.append(content.text)
        return "\n".join(text_parts)
    
    def has_tool_use(self) -> bool:
        """Check if message contains tool use."""
        return any(content.type == "tool_use" for content in self.content)
    
    def has_images(self) -> bool:
        """Check if message contains images."""
        return any(content.type == "image" for content in self.content)
    
    def get_tool_uses(self) -> List[AIMessageContent]:
        """Get all tool use content blocks."""
        return [content for content in self.content if content.type == "tool_use"]
    
    def get_tool_results(self) -> List[AIMessageContent]:
        """Get all tool result content blocks."""
        return [content for content in self.content if content.type == "tool_result"]


class AIToolUse(BaseModel):
    """AI tool use request."""
    id: str
    name: str
    input: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AIToolResult(BaseModel):
    """AI tool execution result."""
    tool_use_id: str
    result: Any
    is_error: bool = False
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AIUsage(BaseModel):
    """AI API usage statistics."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    
    def add_usage(self, other: "AIUsage") -> "AIUsage":
        """Add another usage to this one."""
        return AIUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            input_cost=self.input_cost + other.input_cost,
            output_cost=self.output_cost + other.output_cost,
            total_cost=self.total_cost + other.total_cost,
        )


class AIResponse(BaseModel):
    """AI service response."""
    id: str
    model: str
    provider: AIProvider
    message: AIMessage
    usage: AIUsage
    tool_uses: List[AIToolUse] = Field(default_factory=list)
    finish_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    response_time: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class AIConversation(BaseModel):
    """AI conversation context."""
    id: UUID
    task_id: Optional[UUID] = None
    messages: List[AIMessage] = Field(default_factory=list)
    system_prompt: Optional[str] = None
    model_config: AIModel
    total_usage: AIUsage = Field(default_factory=AIUsage)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def add_message(self, message: AIMessage):
        """Add a message to the conversation."""
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
    
    def add_usage(self, usage: AIUsage):
        """Add usage statistics to the conversation."""
        self.total_usage = self.total_usage.add_usage(usage)
        self.updated_at = datetime.utcnow()
    
    def get_context_messages(self, max_tokens: Optional[int] = None) -> List[AIMessage]:
        """Get messages for AI context, optionally limited by token count."""
        if not max_tokens:
            return self.messages.copy()
        
        # Simple token estimation (rough approximation)
        # In a real implementation, you'd use the actual tokenizer
        messages = []
        total_tokens = 0
        
        # Always include system message if present
        if self.messages and self.messages[0].role == AIMessageRole.SYSTEM:
            messages.append(self.messages[0])
            total_tokens += len(self.messages[0].get_text_content()) // 4  # Rough estimate
        
        # Add messages from most recent, staying within token limit
        for message in reversed(self.messages[1:] if messages else self.messages):
            estimated_tokens = len(message.get_text_content()) // 4  # Rough estimate
            if total_tokens + estimated_tokens > max_tokens:
                break
            messages.insert(-1 if messages and messages[0].role == AIMessageRole.SYSTEM else 0, message)
            total_tokens += estimated_tokens
        
        return messages
    
    def get_last_assistant_message(self) -> Optional[AIMessage]:
        """Get the last assistant message."""
        for message in reversed(self.messages):
            if message.role == AIMessageRole.ASSISTANT:
                return message
        return None
    
    def get_pending_tool_uses(self) -> List[AIToolUse]:
        """Get tool uses that haven't been executed yet."""
        tool_uses = []
        tool_results = set()
        
        # Collect all tool result IDs
        for message in self.messages:
            for content in message.content:
                if content.type == "tool_result" and content.tool_use_id:
                    tool_results.add(content.tool_use_id)
        
        # Find tool uses without results
        for message in self.messages:
            for content in message.content:
                if content.type == "tool_use" and content.tool_use_id not in tool_results:
                    tool_uses.append(
                        AIToolUse(
                            id=content.tool_use_id,
                            name=content.tool_name,
                            input=content.tool_input or {},
                        )
                    )
        
        return tool_uses


class AIStreamChunk(BaseModel):
    """AI streaming response chunk."""
    id: str
    model: str
    provider: AIProvider
    delta: Optional[str] = None
    tool_use: Optional[AIToolUse] = None
    finish_reason: Optional[str] = None
    usage: Optional[AIUsage] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AIModelCapabilities(BaseModel):
    """AI model capabilities and limits."""
    model_id: str
    max_tokens: int
    context_window: int
    supports_vision: bool
    supports_function_calling: bool
    supports_streaming: bool
    supports_system_messages: bool
    max_images_per_request: int = 0
    supported_image_formats: List[str] = Field(default_factory=list)
    max_function_calls_per_request: int = 0
    rate_limits: Dict[str, Any] = Field(default_factory=dict)
    

class AIModelPerformance(BaseModel):
    """AI model performance metrics."""
    model_id: str
    average_response_time: float
    success_rate: float
    error_rate: float
    total_requests: int
    total_tokens_processed: int
    average_tokens_per_request: float
    cost_per_request: float
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class AIProviderConfig(BaseModel):
    """AI provider configuration."""
    provider: AIProvider
    api_key: str
    base_url: Optional[str] = None
    organization: Optional[str] = None
    project: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_requests_per_minute: Optional[int] = None
    rate_limit_tokens_per_minute: Optional[int] = None
    is_active: bool = True
    
    class Config:
        # Don't include sensitive fields in serialization by default
        fields = {
            "api_key": {"write_only": True},
        }