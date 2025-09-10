"""Model service for AI model management and operations."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..core.exceptions import (
    BytebotNotFoundException,
    BytebotValidationException,
    BytebotConflictException,
)
from ..core.logging import get_logger
from ..models.message import Message
from ..models.summary import Summary
from ..models.task import Task
from ..shared.ai_models import AIModel, ModelProvider, ModelCapability
from ..shared.task_types import TaskType, TaskPriority

logger = get_logger(__name__)


class ModelService:
    """Service for AI model-related operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._available_models = self._initialize_models()
    
    def _initialize_models(self) -> Dict[str, AIModel]:
        """Initialize available AI models."""
        models = {
            # Claude models
            "claude-3-5-sonnet-20241022": AIModel(
                name="claude-3-5-sonnet-20241022",
                provider=ModelProvider.ANTHROPIC,
                version="20241022",
                display_name="Claude 3.5 Sonnet",
                description="Most intelligent model with excellent reasoning and coding capabilities",
                max_tokens=200000,
                context_window=200000,
                input_cost_per_token=0.000003,
                output_cost_per_token=0.000015,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.TOOL_USE,
                    ModelCapability.IMAGE_ANALYSIS,
                ],
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                rate_limit_rpm=4000,
                rate_limit_tpm=400000,
            ),
            "claude-3-haiku-20240307": AIModel(
                name="claude-3-haiku-20240307",
                provider=ModelProvider.ANTHROPIC,
                version="20240307",
                display_name="Claude 3 Haiku",
                description="Fastest model for simple tasks and quick responses",
                max_tokens=200000,
                context_window=200000,
                input_cost_per_token=0.00000025,
                output_cost_per_token=0.00000125,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.TOOL_USE,
                    ModelCapability.IMAGE_ANALYSIS,
                ],
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                rate_limit_rpm=4000,
                rate_limit_tpm=400000,
            ),
            # OpenAI models
            "gpt-4o": AIModel(
                name="gpt-4o",
                provider=ModelProvider.OPENAI,
                version="2024-08-06",
                display_name="GPT-4o",
                description="High-intelligence flagship model for complex, multi-step tasks",
                max_tokens=128000,
                context_window=128000,
                input_cost_per_token=0.0000025,
                output_cost_per_token=0.00001,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.TOOL_USE,
                    ModelCapability.IMAGE_ANALYSIS,
                ],
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                rate_limit_rpm=10000,
                rate_limit_tpm=2000000,
            ),
            "gpt-4o-mini": AIModel(
                name="gpt-4o-mini",
                provider=ModelProvider.OPENAI,
                version="2024-07-18",
                display_name="GPT-4o Mini",
                description="Affordable and intelligent small model for fast, lightweight tasks",
                max_tokens=128000,
                context_window=128000,
                input_cost_per_token=0.00000015,
                output_cost_per_token=0.0000006,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.TOOL_USE,
                    ModelCapability.IMAGE_ANALYSIS,
                ],
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                rate_limit_rpm=30000,
                rate_limit_tpm=10000000,
            ),
            # Google models
            "gemini-1.5-pro": AIModel(
                name="gemini-1.5-pro",
                provider=ModelProvider.GOOGLE,
                version="001",
                display_name="Gemini 1.5 Pro",
                description="Mid-size multimodal model that supports up to 1 million tokens",
                max_tokens=1000000,
                context_window=1000000,
                input_cost_per_token=0.00000125,
                output_cost_per_token=0.000005,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.TOOL_USE,
                    ModelCapability.IMAGE_ANALYSIS,
                ],
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                rate_limit_rpm=2000,
                rate_limit_tpm=32000,
            ),
            "gemini-1.5-flash": AIModel(
                name="gemini-1.5-flash",
                provider=ModelProvider.GOOGLE,
                version="001",
                display_name="Gemini 1.5 Flash",
                description="Fast and versatile multimodal model for scaling across diverse tasks",
                max_tokens=1000000,
                context_window=1000000,
                input_cost_per_token=0.000000075,
                output_cost_per_token=0.0000003,
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.TOOL_USE,
                    ModelCapability.IMAGE_ANALYSIS,
                ],
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                rate_limit_rpm=15000,
                rate_limit_tpm=1000000,
            ),
        }
        return models
    
    async def get_available_models(self) -> List[AIModel]:
        """Get all available AI models."""
        return list(self._available_models.values())
    
    async def get_model(self, model_name: str) -> Optional[AIModel]:
        """Get a specific model by name."""
        return self._available_models.get(model_name)
    
    async def get_models_by_provider(self, provider: ModelProvider) -> List[AIModel]:
        """Get models by provider."""
        return [
            model for model in self._available_models.values()
            if model.provider == provider
        ]
    
    async def get_models_by_capability(self, capability: ModelCapability) -> List[AIModel]:
        """Get models that support a specific capability."""
        return [
            model for model in self._available_models.values()
            if capability in model.capabilities
        ]
    
    async def validate_model_config(
        self,
        model_name: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Validate model configuration."""
        model = await self.get_model(model_name)
        if not model:
            return {
                "valid": False,
                "errors": [f"Model '{model_name}' not found"],
            }
        
        errors = []
        warnings = []
        
        # Validate max_tokens
        if max_tokens is not None:
            if max_tokens > model.max_tokens:
                errors.append(
                    f"max_tokens ({max_tokens}) exceeds model limit ({model.max_tokens})"
                )
            elif max_tokens < 1:
                errors.append("max_tokens must be at least 1")
        
        # Validate temperature
        if temperature is not None:
            if temperature < 0 or temperature > 2:
                errors.append("temperature must be between 0 and 2")
            elif temperature > 1:
                warnings.append("temperature > 1 may produce less coherent outputs")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "model": model.model_dump() if model else None,
        }
    
    async def test_model(
        self,
        model_name: str,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Test a model with a simple prompt."""
        model = await self.get_model(model_name)
        if not model:
            return {
                "success": False,
                "error": f"Model '{model_name}' not found",
            }
        
        # Validate configuration
        config_validation = await self.validate_model_config(
            model_name, max_tokens, temperature
        )
        if not config_validation["valid"]:
            return {
                "success": False,
                "error": "Invalid configuration",
                "details": config_validation["errors"],
            }
        
        # In a real implementation, you would make an actual API call here
        # For now, we'll return a mock response
        return {
            "success": True,
            "model_name": model_name,
            "prompt": prompt,
            "response": f"Test response from {model.display_name}",
            "tokens_used": {
                "input": len(prompt.split()),
                "output": 10,
                "total": len(prompt.split()) + 10,
            },
            "cost_estimate": {
                "input_cost": len(prompt.split()) * model.input_cost_per_token,
                "output_cost": 10 * model.output_cost_per_token,
                "total_cost": (len(prompt.split()) * model.input_cost_per_token) + (10 * model.output_cost_per_token),
            },
        }
    
    async def get_model_recommendations(
        self,
        task_type: TaskType,
        budget: Optional[float] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        required_capabilities: Optional[List[ModelCapability]] = None,
    ) -> List[Dict[str, Any]]:
        """Get model recommendations based on task requirements."""
        models = await self.get_available_models()
        recommendations = []
        
        for model in models:
            # Check required capabilities
            if required_capabilities:
                if not all(cap in model.capabilities for cap in required_capabilities):
                    continue
            
            # Calculate suitability score
            score = 0.0
            reasons = []
            
            # Task type scoring
            if task_type == TaskType.CODE_GENERATION:
                if ModelCapability.CODE_GENERATION in model.capabilities:
                    score += 30
                    reasons.append("Supports code generation")
                if "claude" in model.name.lower():
                    score += 20
                    reasons.append("Excellent for coding tasks")
            elif task_type == TaskType.DATA_ANALYSIS:
                if ModelCapability.REASONING in model.capabilities:
                    score += 25
                    reasons.append("Strong reasoning capabilities")
                if model.context_window > 100000:
                    score += 15
                    reasons.append("Large context window for data analysis")
            elif task_type == TaskType.CONTENT_CREATION:
                if ModelCapability.TEXT_GENERATION in model.capabilities:
                    score += 25
                    reasons.append("Excellent text generation")
            
            # Priority scoring
            if priority == TaskPriority.HIGH:
                if "sonnet" in model.name.lower() or "gpt-4o" in model.name.lower():
                    score += 20
                    reasons.append("High-performance model")
            elif priority == TaskPriority.LOW:
                if "haiku" in model.name.lower() or "mini" in model.name.lower() or "flash" in model.name.lower():
                    score += 15
                    reasons.append("Cost-effective option")
            
            # Budget scoring
            if budget is not None:
                estimated_cost = (1000 * model.input_cost_per_token) + (500 * model.output_cost_per_token)
                if estimated_cost <= budget:
                    score += 10
                    reasons.append("Within budget")
                elif estimated_cost <= budget * 1.5:
                    score += 5
                    reasons.append("Slightly over budget")
                else:
                    score -= 10
                    reasons.append("Over budget")
            
            # Context window bonus
            if model.context_window > 100000:
                score += 10
                reasons.append("Large context window")
            
            # Rate limit considerations
            if model.rate_limit_rpm > 10000:
                score += 5
                reasons.append("High rate limits")
            
            recommendations.append({
                "model": model.model_dump(),
                "score": score,
                "reasons": reasons,
                "estimated_cost_per_1k_tokens": {
                    "input": model.input_cost_per_token * 1000,
                    "output": model.output_cost_per_token * 1000,
                },
            })
        
        # Sort by score (descending)
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        return recommendations[:5]  # Return top 5 recommendations
    
    async def get_usage_statistics(
        self,
        days: int = 30,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get model usage statistics."""
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Base queries for messages and summaries
        message_query = select(Message).where(Message.created_at >= since_date)
        summary_query = select(Summary).where(Summary.created_at >= since_date)
        
        if model_name:
            message_query = message_query.where(Message.model_name == model_name)
            summary_query = summary_query.where(Summary.model_name == model_name)
        
        # Message statistics
        message_stats_query = (
            select(
                Message.model_name,
                Message.model_provider,
                func.count(Message.id).label('count'),
                func.sum(Message.input_tokens).label('total_input_tokens'),
                func.sum(Message.output_tokens).label('total_output_tokens'),
                func.avg(Message.processing_time_ms).label('avg_processing_time'),
            )
            .where(Message.created_at >= since_date)
            .group_by(Message.model_name, Message.model_provider)
        )
        
        if model_name:
            message_stats_query = message_stats_query.where(Message.model_name == model_name)
        
        message_result = await self.db.execute(message_stats_query)
        message_stats = message_result.fetchall()
        
        # Summary statistics
        summary_stats_query = (
            select(
                Summary.model_name,
                Summary.model_provider,
                func.count(Summary.id).label('count'),
                func.sum(Summary.input_tokens).label('total_input_tokens'),
                func.sum(Summary.output_tokens).label('total_output_tokens'),
                func.avg(Summary.processing_time_ms).label('avg_processing_time'),
            )
            .where(Summary.created_at >= since_date)
            .group_by(Summary.model_name, Summary.model_provider)
        )
        
        if model_name:
            summary_stats_query = summary_stats_query.where(Summary.model_name == model_name)
        
        summary_result = await self.db.execute(summary_stats_query)
        summary_stats = summary_result.fetchall()
        
        # Combine and calculate costs
        usage_by_model = {}
        
        for stat in message_stats:
            model_key = stat.model_name or "unknown"
            if model_key not in usage_by_model:
                usage_by_model[model_key] = {
                    "model_name": stat.model_name,
                    "model_provider": stat.model_provider,
                    "message_count": 0,
                    "summary_count": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "avg_processing_time_ms": 0,
                    "estimated_cost": 0,
                }
            
            usage_by_model[model_key]["message_count"] = stat.count or 0
            usage_by_model[model_key]["total_input_tokens"] += stat.total_input_tokens or 0
            usage_by_model[model_key]["total_output_tokens"] += stat.total_output_tokens or 0
            usage_by_model[model_key]["avg_processing_time_ms"] = stat.avg_processing_time or 0
        
        for stat in summary_stats:
            model_key = stat.model_name or "unknown"
            if model_key not in usage_by_model:
                usage_by_model[model_key] = {
                    "model_name": stat.model_name,
                    "model_provider": stat.model_provider,
                    "message_count": 0,
                    "summary_count": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "avg_processing_time_ms": 0,
                    "estimated_cost": 0,
                }
            
            usage_by_model[model_key]["summary_count"] = stat.count or 0
            usage_by_model[model_key]["total_input_tokens"] += stat.total_input_tokens or 0
            usage_by_model[model_key]["total_output_tokens"] += stat.total_output_tokens or 0
            # Average processing time across messages and summaries
            if usage_by_model[model_key]["avg_processing_time_ms"] == 0:
                usage_by_model[model_key]["avg_processing_time_ms"] = stat.avg_processing_time or 0
        
        # Calculate estimated costs
        for model_key, usage in usage_by_model.items():
            model = await self.get_model(model_key)
            if model:
                input_cost = usage["total_input_tokens"] * model.input_cost_per_token
                output_cost = usage["total_output_tokens"] * model.output_cost_per_token
                usage["estimated_cost"] = input_cost + output_cost
        
        # Calculate totals
        total_messages = sum(usage["message_count"] for usage in usage_by_model.values())
        total_summaries = sum(usage["summary_count"] for usage in usage_by_model.values())
        total_input_tokens = sum(usage["total_input_tokens"] for usage in usage_by_model.values())
        total_output_tokens = sum(usage["total_output_tokens"] for usage in usage_by_model.values())
        total_cost = sum(usage["estimated_cost"] for usage in usage_by_model.values())
        
        return {
            "period_days": days,
            "model_name": model_name,
            "totals": {
                "messages": total_messages,
                "summaries": total_summaries,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
                "estimated_cost": total_cost,
            },
            "by_model": list(usage_by_model.values()),
        }
    
    async def get_token_costs(
        self,
        input_tokens: int,
        output_tokens: int,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculate token costs for given usage."""
        if model_name:
            models = [await self.get_model(model_name)]
            if not models[0]:
                raise BytebotNotFoundException(f"Model '{model_name}' not found")
        else:
            models = await self.get_available_models()
        
        costs = []
        for model in models:
            if not model:
                continue
                
            input_cost = input_tokens * model.input_cost_per_token
            output_cost = output_tokens * model.output_cost_per_token
            total_cost = input_cost + output_cost
            
            costs.append({
                "model_name": model.name,
                "model_provider": model.provider.value,
                "input_cost": input_cost,
                "output_cost": output_cost,
                "total_cost": total_cost,
                "cost_per_1k_tokens": {
                    "input": model.input_cost_per_token * 1000,
                    "output": model.output_cost_per_token * 1000,
                },
            })
        
        # Sort by total cost
        costs.sort(key=lambda x: x["total_cost"])
        
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "costs": costs,
        }
    
    async def get_performance_metrics(
        self,
        model_name: str,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Get performance metrics for a specific model."""
        model = await self.get_model(model_name)
        if not model:
            raise BytebotNotFoundException(f"Model '{model_name}' not found")
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Message performance metrics
        message_metrics_query = (
            select(
                func.count(Message.id).label('total_requests'),
                func.count(Message.id).filter(Message.processing_error.is_(None)).label('successful_requests'),
                func.avg(Message.processing_time_ms).label('avg_processing_time'),
                func.min(Message.processing_time_ms).label('min_processing_time'),
                func.max(Message.processing_time_ms).label('max_processing_time'),
                func.avg(Message.input_tokens).label('avg_input_tokens'),
                func.avg(Message.output_tokens).label('avg_output_tokens'),
            )
            .where(
                and_(
                    Message.model_name == model_name,
                    Message.created_at >= since_date,
                )
            )
        )
        
        message_result = await self.db.execute(message_metrics_query)
        message_metrics = message_result.fetchone()
        
        # Summary performance metrics
        summary_metrics_query = (
            select(
                func.count(Summary.id).label('total_requests'),
                func.count(Summary.id).filter(Summary.status != 'failed').label('successful_requests'),
                func.avg(Summary.processing_time_ms).label('avg_processing_time'),
                func.avg(Summary.input_tokens).label('avg_input_tokens'),
                func.avg(Summary.output_tokens).label('avg_output_tokens'),
            )
            .where(
                and_(
                    Summary.model_name == model_name,
                    Summary.created_at >= since_date,
                )
            )
        )
        
        summary_result = await self.db.execute(summary_metrics_query)
        summary_metrics = summary_result.fetchone()
        
        # Calculate success rates and combined metrics
        total_requests = (message_metrics.total_requests or 0) + (summary_metrics.total_requests or 0)
        successful_requests = (message_metrics.successful_requests or 0) + (summary_metrics.successful_requests or 0)
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "model_name": model_name,
            "period_days": days,
            "model_info": model.model_dump(),
            "performance": {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "success_rate_percent": success_rate,
                "avg_processing_time_ms": {
                    "messages": float(message_metrics.avg_processing_time or 0),
                    "summaries": float(summary_metrics.avg_processing_time or 0),
                },
                "processing_time_range_ms": {
                    "min": float(message_metrics.min_processing_time or 0),
                    "max": float(message_metrics.max_processing_time or 0),
                },
                "avg_token_usage": {
                    "input_tokens": {
                        "messages": float(message_metrics.avg_input_tokens or 0),
                        "summaries": float(summary_metrics.avg_input_tokens or 0),
                    },
                    "output_tokens": {
                        "messages": float(message_metrics.avg_output_tokens or 0),
                        "summaries": float(summary_metrics.avg_output_tokens or 0),
                    },
                },
            },
        }
    
    async def get_model_limits(self, model_name: str) -> Dict[str, Any]:
        """Get model limits and constraints."""
        model = await self.get_model(model_name)
        if not model:
            raise BytebotNotFoundException(f"Model '{model_name}' not found")
        
        return {
            "model_name": model_name,
            "limits": {
                "max_tokens": model.max_tokens,
                "context_window": model.context_window,
                "rate_limits": {
                    "requests_per_minute": model.rate_limit_rpm,
                    "tokens_per_minute": model.rate_limit_tpm,
                },
            },
            "capabilities": [cap.value for cap in model.capabilities],
            "features": {
                "supports_streaming": model.supports_streaming,
                "supports_function_calling": model.supports_function_calling,
                "supports_vision": model.supports_vision,
            },
            "pricing": {
                "input_cost_per_token": model.input_cost_per_token,
                "output_cost_per_token": model.output_cost_per_token,
                "cost_per_1k_tokens": {
                    "input": model.input_cost_per_token * 1000,
                    "output": model.output_cost_per_token * 1000,
                },
            },
        }
    
    async def get_model_capabilities(self, capability: ModelCapability) -> List[AIModel]:
        """Get models that support a specific capability."""
        return await self.get_models_by_capability(capability)