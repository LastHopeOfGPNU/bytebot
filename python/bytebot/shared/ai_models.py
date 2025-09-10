"""AI model-related types and enumerations."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ModelProvider(str, Enum):
    """AI model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    COHERE = "cohere"
    TOGETHER = "together"
    REPLICATE = "replicate"
    HUGGINGFACE = "huggingface"
    AZURE = "azure"
    BEDROCK = "bedrock"
    VERTEX = "vertex"
    CUSTOM = "custom"


class ModelCapability(str, Enum):
    """AI model capabilities."""
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    TOOL_USE = "tool_use"
    IMAGE_ANALYSIS = "image_analysis"
    AUDIO_PROCESSING = "audio_processing"
    VIDEO_ANALYSIS = "video_analysis"
    EMBEDDINGS = "embeddings"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    NAMED_ENTITY_RECOGNITION = "named_entity_recognition"
    QUESTION_ANSWERING = "question_answering"
    CHAT_COMPLETION = "chat_completion"


class AIModel(BaseModel):
    """AI model configuration."""
    name: str = Field(..., description="Model identifier")
    provider: ModelProvider = Field(..., description="Model provider")
    version: str = Field(..., description="Model version")
    display_name: str = Field(..., description="Human-readable model name")
    description: str = Field(..., description="Model description")
    max_tokens: int = Field(..., ge=1, description="Maximum tokens per request")
    context_window: int = Field(..., ge=1, description="Context window size")
    input_cost_per_token: float = Field(..., ge=0, description="Cost per input token")
    output_cost_per_token: float = Field(..., ge=0, description="Cost per output token")
    capabilities: List[ModelCapability] = Field(..., description="Supported capabilities")
    supports_streaming: bool = Field(False, description="Whether model supports streaming")
    supports_function_calling: bool = Field(False, description="Whether model supports function calling")
    supports_vision: bool = Field(False, description="Whether model supports vision")
    rate_limit_rpm: int = Field(..., ge=1, description="Rate limit in requests per minute")
    rate_limit_tpm: int = Field(..., ge=1, description="Rate limit in tokens per minute")
    
    @property
    def total_cost_per_token(self) -> float:
        """Calculate total cost per token (input + output)."""
        return self.input_cost_per_token + self.output_cost_per_token
    
    @property
    def is_expensive(self) -> bool:
        """Check if model is considered expensive."""
        return self.total_cost_per_token > 0.00001
    
    @property
    def is_high_capacity(self) -> bool:
        """Check if model has high capacity (context window > 100k)."""
        return self.context_window > 100000


class ModelUsage(BaseModel):
    """Model usage statistics."""
    model_name: str = Field(..., description="Model identifier")
    input_tokens: int = Field(0, ge=0, description="Total input tokens used")
    output_tokens: int = Field(0, ge=0, description="Total output tokens generated")
    total_requests: int = Field(0, ge=0, description="Total requests made")
    total_cost: float = Field(0.0, ge=0, description="Total cost incurred")
    last_used: Optional[datetime] = Field(None, description="Last usage timestamp")
    
    @property
    def total_tokens(self) -> int:
        """Calculate total tokens used."""
        return self.input_tokens + self.output_tokens
    
    @property
    def average_tokens_per_request(self) -> float:
        """Calculate average tokens per request."""
        return self.total_tokens / self.total_requests if self.total_requests > 0 else 0.0
    
    @property
    def average_cost_per_request(self) -> float:
        """Calculate average cost per request."""
        return self.total_cost / self.total_requests if self.total_requests > 0 else 0.0


class ModelSelectionCriteria(BaseModel):
    """Criteria for selecting AI models."""
    required_capabilities: List[ModelCapability] = Field(default_factory=list, description="Required capabilities")
    max_cost_per_token: Optional[float] = Field(None, ge=0, description="Maximum cost per token")
    min_context_window: Optional[int] = Field(None, ge=1, description="Minimum context window size")
    max_context_window: Optional[int] = Field(None, ge=1, description="Maximum context window size")
    requires_streaming: bool = Field(False, description="Whether streaming is required")
    requires_function_calling: bool = Field(False, description="Whether function calling is required")
    requires_vision: bool = Field(False, description="Whether vision support is required")
    preferred_providers: List[ModelProvider] = Field(default_factory=list, description="Preferred providers")
    excluded_providers: List[ModelProvider] = Field(default_factory=list, description="Excluded providers")
    max_requests_per_minute: Optional[int] = Field(None, ge=1, description="Maximum requests per minute")
    max_tokens_per_minute: Optional[int] = Field(None, ge=1, description="Maximum tokens per minute")


class ModelPerformanceMetrics(BaseModel):
    """Model performance metrics."""
    model_name: str = Field(..., description="Model identifier")
    latency_ms: float = Field(..., ge=0, description="Average latency in milliseconds")
    success_rate: float = Field(..., ge=0, le=1, description="Request success rate")
    error_rate: float = Field(..., ge=0, le=1, description="Request error rate")
    timeout_rate: float = Field(..., ge=0, le=1, description="Request timeout rate")
    retry_rate: float = Field(..., ge=0, le=1, description="Request retry rate")
    cache_hit_rate: float = Field(..., ge=0, le=1, description="Cache hit rate")
    tokens_per_second: float = Field(..., ge=0, description="Tokens generated per second")
    
    @property
    def reliability_score(self) -> float:
        """Calculate reliability score (1.0 - error_rate - timeout_rate)."""
        return 1.0 - (self.error_rate + self.timeout_rate)
    
    @property
    def efficiency_score(self) -> float:
        """Calculate efficiency score (tokens_per_second / latency_ms)."""
        return self.tokens_per_second / self.latency_ms if self.latency_ms > 0 else 0.0