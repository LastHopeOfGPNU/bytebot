"""Models API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db_session
from ...core.logging import get_logger
from ...services.model_service import ModelService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/available")
async def get_available_models(
    provider: Optional[str] = Query(None, description="Filter by provider (openai, anthropic, google)"),
    model_type: Optional[str] = Query(None, description="Filter by model type (chat, completion, embedding)"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get list of available AI models."""
    model_service = ModelService(db)
    
    models = await model_service.get_available_models(
        provider=provider,
        model_type=model_type,
    )
    
    return {
        "models": models,
        "total": len(models),
        "providers": list(set(model.get("provider") for model in models if model.get("provider"))),
    }


@router.get("/usage-stats")
async def get_model_usage_stats(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get model usage statistics."""
    model_service = ModelService(db)
    
    stats = await model_service.get_usage_stats(
        start_date=start_date,
        end_date=end_date,
        model_name=model_name,
    )
    
    return stats


@router.get("/token-costs")
async def get_token_costs(
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get token cost information for models."""
    model_service = ModelService(db)
    
    costs = await model_service.get_token_costs(model_name=model_name)
    
    return {
        "token_costs": costs,
        "currency": "USD",
        "unit": "per 1K tokens",
    }


@router.get("/performance")
async def get_model_performance(
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    metric: Optional[str] = Query(None, description="Filter by metric (latency, throughput, accuracy)"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get model performance metrics."""
    model_service = ModelService(db)
    
    performance = await model_service.get_performance_metrics(
        model_name=model_name,
        metric=metric,
    )
    
    return performance


@router.post("/validate")
async def validate_model_config(
    provider: str,
    model_name: str,
    api_key: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Validate model configuration and connectivity."""
    model_service = ModelService(db)
    
    try:
        is_valid = await model_service.validate_model_config(
            provider=provider,
            model_name=model_name,
            api_key=api_key,
        )
        
        return {
            "valid": is_valid,
            "provider": provider,
            "model_name": model_name,
            "message": "Model configuration is valid" if is_valid else "Model configuration is invalid",
        }
    except Exception as e:
        return {
            "valid": False,
            "provider": provider,
            "model_name": model_name,
            "error": str(e),
            "message": "Failed to validate model configuration",
        }


@router.get("/limits")
async def get_model_limits(
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get model limits and constraints."""
    model_service = ModelService(db)
    
    limits = await model_service.get_model_limits(model_name=model_name)
    
    return {
        "limits": limits,
        "note": "Limits may vary based on your API plan and usage tier",
    }


@router.get("/capabilities")
async def get_model_capabilities(
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    capability: Optional[str] = Query(None, description="Filter by capability (vision, function_calling, streaming)"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get model capabilities and features."""
    model_service = ModelService(db)
    
    capabilities = await model_service.get_model_capabilities(
        model_name=model_name,
        capability=capability,
    )
    
    return {
        "capabilities": capabilities,
        "available_capabilities": [
            "vision",
            "function_calling",
            "streaming",
            "json_mode",
            "system_messages",
            "tool_use",
        ],
    }


@router.post("/test")
async def test_model(
    provider: str,
    model_name: str,
    test_prompt: str = "Hello, how are you?",
    api_key: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Test a model with a simple prompt."""
    model_service = ModelService(db)
    
    try:
        result = await model_service.test_model(
            provider=provider,
            model_name=model_name,
            prompt=test_prompt,
            api_key=api_key,
        )
        
        return {
            "success": True,
            "provider": provider,
            "model_name": model_name,
            "test_prompt": test_prompt,
            "response": result.get("response"),
            "latency_ms": result.get("latency_ms"),
            "input_tokens": result.get("input_tokens"),
            "output_tokens": result.get("output_tokens"),
        }
    except Exception as e:
        return {
            "success": False,
            "provider": provider,
            "model_name": model_name,
            "test_prompt": test_prompt,
            "error": str(e),
        }


@router.get("/recommendations")
async def get_model_recommendations(
    task_type: Optional[str] = Query(None, description="Task type (chat, completion, analysis, coding)"),
    budget: Optional[str] = Query(None, description="Budget tier (low, medium, high)"),
    priority: Optional[str] = Query(None, description="Priority (speed, quality, cost)"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get model recommendations based on requirements."""
    model_service = ModelService(db)
    
    recommendations = await model_service.get_model_recommendations(
        task_type=task_type,
        budget=budget,
        priority=priority,
    )
    
    return {
        "recommendations": recommendations,
        "criteria": {
            "task_type": task_type,
            "budget": budget,
            "priority": priority,
        },
        "note": "Recommendations are based on general performance metrics and may vary for specific use cases",
    }