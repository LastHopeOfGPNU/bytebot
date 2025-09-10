"""AI service for high-level AI operations and business logic."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.logging import get_logger
from ..models import Message, Task
from ..websocket.router import notify_ai_response, notify_ai_thinking
from .client import AIClient
from .models import (
    AIConversation,
    AIMessage,
    AIMessageRole,
    AIModel,
    AIProvider,
    AIResponse,
    AIStreamChunk,
    AIToolResult,
    AIToolUse,
    AIUsage,
)

logger = get_logger(__name__)


class AIService:
    """High-level AI service for task execution and conversation management."""
    
    def __init__(self):
        self.client = AIClient()
        self.conversations: Dict[UUID, AIConversation] = {}
        self.default_models = self._get_default_models()
    
    def _get_default_models(self) -> Dict[AIProvider, AIModel]:
        """Get default models for each provider."""
        return {
            AIProvider.CLAUDE: AIModel(
                id="claude-3-5-sonnet-20241022",
                name="Claude 3.5 Sonnet",
                provider=AIProvider.CLAUDE,
                max_tokens=8192,
                context_window=200000,
                input_cost_per_token=0.000003,
                output_cost_per_token=0.000015,
                supports_vision=True,
                supports_function_calling=True,
                supports_streaming=True,
            ),
            AIProvider.OPENAI: AIModel(
                id="gpt-4o",
                name="GPT-4o",
                provider=AIProvider.OPENAI,
                max_tokens=4096,
                context_window=128000,
                input_cost_per_token=0.000005,
                output_cost_per_token=0.000015,
                supports_vision=True,
                supports_function_calling=True,
                supports_streaming=True,
            ),
        }
    
    async def create_conversation(
        self,
        task_id: Optional[UUID] = None,
        system_prompt: Optional[str] = None,
        model_provider: AIProvider = AIProvider.CLAUDE,
        model_id: Optional[str] = None,
    ) -> AIConversation:
        """Create a new AI conversation."""
        conversation_id = uuid4()
        
        # Get model configuration
        if model_id:
            # TODO: Load model from database
            model_config = self.default_models.get(model_provider)
            if model_config:
                model_config.id = model_id
        else:
            model_config = self.default_models.get(model_provider)
        
        if not model_config:
            raise ValueError(f"No model available for provider: {model_provider}")
        
        conversation = AIConversation(
            id=conversation_id,
            task_id=task_id,
            system_prompt=system_prompt,
            model_config=model_config,
        )
        
        # Add system message if provided
        if system_prompt:
            system_message = AIMessage.create_system_message(system_prompt)
            conversation.add_message(system_message)
        
        self.conversations[conversation_id] = conversation
        logger.info(f"Created AI conversation {conversation_id} for task {task_id}")
        
        return conversation
    
    async def get_conversation(self, conversation_id: UUID) -> Optional[AIConversation]:
        """Get an existing conversation."""
        return self.conversations.get(conversation_id)
    
    async def send_message(
        self,
        conversation_id: UUID,
        message: str,
        role: AIMessageRole = AIMessageRole.USER,
        images: Optional[List[str]] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        db: Optional[AsyncSession] = None,
    ) -> AIResponse:
        """Send a message to an AI conversation."""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Create user message
        if images:
            user_message = AIMessage.create_image_message(
                role=role,
                text=message,
                image_data=images[0] if images else None,  # For now, support single image
            )
        else:
            user_message = AIMessage.create_text_message(role, message)
        
        conversation.add_message(user_message)
        
        # Get context messages
        context_messages = conversation.get_context_messages(
            max_tokens=conversation.model_config.context_window - (max_tokens or 4096)
        )
        
        # Send to AI
        if stream:
            return await self._stream_ai_response(
                conversation=conversation,
                messages=context_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                tools=tools,
                db=db,
            )
        else:
            return await self._send_ai_request(
                conversation=conversation,
                messages=context_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                tools=tools,
                db=db,
            )
    
    async def _send_ai_request(
        self,
        conversation: AIConversation,
        messages: List[AIMessage],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
        db: Optional[AsyncSession] = None,
    ) -> AIResponse:
        """Send a request to AI and handle the response."""
        try:
            # Notify thinking started
            if conversation.task_id:
                await notify_ai_thinking(
                    task_id=str(conversation.task_id),
                    thinking_data={
                        "status": "thinking",
                        "model": conversation.model_config.id,
                        "message_count": len(messages),
                    },
                )
            
            # Send request to AI
            response = await self.client.chat(
                messages=messages,
                model=conversation.model_config,
                max_tokens=max_tokens,
                temperature=temperature,
                tools=tools,
            )
            
            # Add response to conversation
            conversation.add_message(response.message)
            conversation.add_usage(response.usage)
            
            # Save to database if available
            if db and conversation.task_id:
                await self._save_message_to_db(
                    db=db,
                    task_id=conversation.task_id,
                    message=response.message,
                    usage=response.usage,
                    ai_response=response,
                )
            
            # Notify response received
            if conversation.task_id:
                await notify_ai_response(
                    task_id=str(conversation.task_id),
                    response_data={
                        "message": response.message.get_text_content(),
                        "model": response.model,
                        "usage": {
                            "input_tokens": response.usage.input_tokens,
                            "output_tokens": response.usage.output_tokens,
                            "total_cost": response.usage.total_cost,
                        },
                        "tool_uses": len(response.tool_uses),
                        "response_time": response.response_time,
                    },
                )
            
            logger.info(
                f"AI response received for conversation {conversation.id}: "
                f"{response.usage.total_tokens} tokens, ${response.usage.total_cost:.6f}"
            )
            
            return response
        
        except Exception as e:
            logger.error(f"AI request failed for conversation {conversation.id}: {e}")
            
            # Notify error
            if conversation.task_id:
                await notify_ai_response(
                    task_id=str(conversation.task_id),
                    response_data={
                        "error": str(e),
                        "model": conversation.model_config.id,
                    },
                )
            
            raise
    
    async def _stream_ai_response(
        self,
        conversation: AIConversation,
        messages: List[AIMessage],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
        db: Optional[AsyncSession] = None,
    ) -> AIResponse:
        """Stream AI response and handle chunks."""
        try:
            # Notify thinking started
            if conversation.task_id:
                await notify_ai_thinking(
                    task_id=str(conversation.task_id),
                    thinking_data={
                        "status": "thinking",
                        "model": conversation.model_config.id,
                        "message_count": len(messages),
                        "streaming": True,
                    },
                )
            
            # Collect response parts
            response_parts = []
            tool_uses = []
            final_usage = None
            finish_reason = None
            response_id = None
            
            # Stream response
            async for chunk in self.client.stream_chat(
                messages=messages,
                model=conversation.model_config,
                max_tokens=max_tokens,
                temperature=temperature,
                tools=tools,
            ):
                if chunk.delta:
                    response_parts.append(chunk.delta)
                    
                    # Notify streaming chunk
                    if conversation.task_id:
                        await notify_ai_response(
                            task_id=str(conversation.task_id),
                            response_data={
                                "delta": chunk.delta,
                                "streaming": True,
                                "model": chunk.model,
                            },
                        )
                
                if chunk.tool_use:
                    tool_uses.append(chunk.tool_use)
                
                if chunk.usage:
                    final_usage = chunk.usage
                
                if chunk.finish_reason:
                    finish_reason = chunk.finish_reason
                
                if chunk.id and not response_id:
                    response_id = chunk.id
            
            # Construct final response
            response_text = "".join(response_parts)
            response_message = AIMessage.create_assistant_message(response_text)
            
            # Add tool uses to message if any
            if tool_uses:
                for tool_use in tool_uses:
                    response_message.content.append(
                        AIMessageContent(
                            type="tool_use",
                            tool_use_id=tool_use.id,
                            tool_name=tool_use.name,
                            tool_input=tool_use.input,
                        )
                    )
            
            # Create final response object
            final_response = AIResponse(
                id=response_id or str(uuid4()),
                model=conversation.model_config.id,
                provider=conversation.model_config.provider,
                message=response_message,
                usage=final_usage or AIUsage(),
                tool_uses=tool_uses,
                finish_reason=finish_reason,
            )
            
            # Add to conversation
            conversation.add_message(response_message)
            if final_usage:
                conversation.add_usage(final_usage)
            
            # Save to database if available
            if db and conversation.task_id:
                await self._save_message_to_db(
                    db=db,
                    task_id=conversation.task_id,
                    message=response_message,
                    usage=final_usage or AIUsage(),
                    ai_response=final_response,
                )
            
            # Notify streaming complete
            if conversation.task_id:
                await notify_ai_response(
                    task_id=str(conversation.task_id),
                    response_data={
                        "message": response_text,
                        "model": final_response.model,
                        "usage": {
                            "input_tokens": final_usage.input_tokens if final_usage else 0,
                            "output_tokens": final_usage.output_tokens if final_usage else 0,
                            "total_cost": final_usage.total_cost if final_usage else 0,
                        },
                        "tool_uses": len(tool_uses),
                        "streaming": False,
                        "complete": True,
                    },
                )
            
            logger.info(
                f"AI streaming response completed for conversation {conversation.id}: "
                f"{len(response_text)} characters"
            )
            
            return final_response
        
        except Exception as e:
            logger.error(f"AI streaming failed for conversation {conversation.id}: {e}")
            
            # Notify error
            if conversation.task_id:
                await notify_ai_response(
                    task_id=str(conversation.task_id),
                    response_data={
                        "error": str(e),
                        "model": conversation.model_config.id,
                        "streaming": False,
                    },
                )
            
            raise
    
    async def execute_tool_use(
        self,
        conversation_id: UUID,
        tool_use: AIToolUse,
        db: Optional[AsyncSession] = None,
    ) -> AIToolResult:
        """Execute a tool use request."""
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        try:
            # TODO: Implement actual tool execution
            # For now, return a mock result
            result = {
                "status": "success",
                "message": f"Tool {tool_use.name} executed successfully",
                "data": tool_use.input,
            }
            
            tool_result = AIToolResult(
                tool_use_id=tool_use.id,
                result=result,
                is_error=False,
            )
            
            # Add tool result to conversation
            tool_result_message = AIMessage.create_tool_result_message(
                tool_use_id=tool_use.id,
                tool_result=result,
                is_error=False,
            )
            conversation.add_message(tool_result_message)
            
            # Save to database if available
            if db and conversation.task_id:
                await self._save_message_to_db(
                    db=db,
                    task_id=conversation.task_id,
                    message=tool_result_message,
                    usage=AIUsage(),
                )
            
            logger.info(f"Tool {tool_use.name} executed successfully for conversation {conversation_id}")
            
            return tool_result
        
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_use.name}: {e}")
            
            # Create error result
            tool_result = AIToolResult(
                tool_use_id=tool_use.id,
                result=None,
                is_error=True,
                error_message=str(e),
            )
            
            # Add error result to conversation
            tool_result_message = AIMessage.create_tool_result_message(
                tool_use_id=tool_use.id,
                tool_result={"error": str(e)},
                is_error=True,
            )
            conversation.add_message(tool_result_message)
            
            return tool_result
    
    async def _save_message_to_db(
        self,
        db: AsyncSession,
        task_id: UUID,
        message: AIMessage,
        usage: AIUsage,
        ai_response: Optional[AIResponse] = None,
    ):
        """Save AI message to database."""
        try:
            # Create message record
            db_message = Message(
                task_id=task_id,
                role=message.role.value,
                content_blocks=[
                    {
                        "type": content.type,
                        "text": content.text,
                        "tool_use_id": content.tool_use_id,
                        "tool_name": content.tool_name,
                        "tool_input": content.tool_input,
                        "tool_result": content.tool_result,
                        "is_error": content.is_error,
                    }
                    for content in message.content
                ],
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
                input_cost=usage.input_cost,
                output_cost=usage.output_cost,
                total_cost=usage.total_cost,
            )
            
            if ai_response:
                db_message.model_id = ai_response.model
                db_message.provider = ai_response.provider.value
                db_message.response_time = ai_response.response_time
                db_message.finish_reason = ai_response.finish_reason
            
            db.add(db_message)
            await db.commit()
            
            logger.debug(f"Saved AI message to database: {db_message.id}")
        
        except Exception as e:
            logger.error(f"Failed to save AI message to database: {e}")
            await db.rollback()
    
    async def get_conversation_history(
        self,
        task_id: UUID,
        db: AsyncSession,
        limit: int = 50,
    ) -> List[AIMessage]:
        """Get conversation history from database."""
        try:
            # Query messages from database
            query = (
                select(Message)
                .where(Message.task_id == task_id)
                .order_by(desc(Message.created_at))
                .limit(limit)
            )
            
            result = await db.execute(query)
            db_messages = result.scalars().all()
            
            # Convert to AI messages
            ai_messages = []
            for db_message in reversed(db_messages):  # Reverse to get chronological order
                content_blocks = []
                
                for block in db_message.content_blocks or []:
                    content_blocks.append(
                        AIMessageContent(
                            type=block.get("type", "text"),
                            text=block.get("text"),
                            tool_use_id=block.get("tool_use_id"),
                            tool_name=block.get("tool_name"),
                            tool_input=block.get("tool_input"),
                            tool_result=block.get("tool_result"),
                            is_error=block.get("is_error"),
                        )
                    )
                
                ai_message = AIMessage(
                    role=AIMessageRole(db_message.role),
                    content=content_blocks,
                    timestamp=db_message.created_at,
                    token_count=db_message.total_tokens,
                )
                
                ai_messages.append(ai_message)
            
            return ai_messages
        
        except Exception as e:
            logger.error(f"Failed to get conversation history for task {task_id}: {e}")
            return []
    
    async def get_usage_statistics(
        self,
        task_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Get AI usage statistics."""
        if not db:
            async with get_db() as db:
                return await self._get_usage_stats_from_db(
                    db=db,
                    task_id=task_id,
                    start_date=start_date,
                    end_date=end_date,
                )
        else:
            return await self._get_usage_stats_from_db(
                db=db,
                task_id=task_id,
                start_date=start_date,
                end_date=end_date,
            )
    
    async def _get_usage_stats_from_db(
        self,
        db: AsyncSession,
        task_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get usage statistics from database."""
        try:
            # Build query conditions
            conditions = []
            
            if task_id:
                conditions.append(Message.task_id == task_id)
            
            if start_date:
                conditions.append(Message.created_at >= start_date)
            
            if end_date:
                conditions.append(Message.created_at <= end_date)
            
            # Query usage statistics
            query = select(
                func.count(Message.id).label("total_messages"),
                func.sum(Message.input_tokens).label("total_input_tokens"),
                func.sum(Message.output_tokens).label("total_output_tokens"),
                func.sum(Message.total_tokens).label("total_tokens"),
                func.sum(Message.total_cost).label("total_cost"),
                func.avg(Message.response_time).label("avg_response_time"),
            )
            
            if conditions:
                query = query.where(and_(*conditions))
            
            result = await db.execute(query)
            stats = result.first()
            
            # Query by provider
            provider_query = (
                select(
                    Message.provider,
                    func.count(Message.id).label("message_count"),
                    func.sum(Message.total_tokens).label("total_tokens"),
                    func.sum(Message.total_cost).label("total_cost"),
                )
                .group_by(Message.provider)
            )
            
            if conditions:
                provider_query = provider_query.where(and_(*conditions))
            
            provider_result = await db.execute(provider_query)
            provider_stats = provider_result.all()
            
            # Query by model
            model_query = (
                select(
                    Message.model_id,
                    func.count(Message.id).label("message_count"),
                    func.sum(Message.total_tokens).label("total_tokens"),
                    func.sum(Message.total_cost).label("total_cost"),
                )
                .group_by(Message.model_id)
            )
            
            if conditions:
                model_query = model_query.where(and_(*conditions))
            
            model_result = await db.execute(model_query)
            model_stats = model_result.all()
            
            return {
                "total_messages": stats.total_messages or 0,
                "total_input_tokens": stats.total_input_tokens or 0,
                "total_output_tokens": stats.total_output_tokens or 0,
                "total_tokens": stats.total_tokens or 0,
                "total_cost": float(stats.total_cost or 0),
                "average_response_time": float(stats.avg_response_time or 0),
                "by_provider": {
                    stat.provider: {
                        "message_count": stat.message_count,
                        "total_tokens": stat.total_tokens,
                        "total_cost": float(stat.total_cost),
                    }
                    for stat in provider_stats
                    if stat.provider
                },
                "by_model": {
                    stat.model_id: {
                        "message_count": stat.message_count,
                        "total_tokens": stat.total_tokens,
                        "total_cost": float(stat.total_cost),
                    }
                    for stat in model_stats
                    if stat.model_id
                },
            }
        
        except Exception as e:
            logger.error(f"Failed to get usage statistics: {e}")
            return {
                "total_messages": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "average_response_time": 0.0,
                "by_provider": {},
                "by_model": {},
            }
    
    async def cleanup_old_conversations(self, max_age_hours: int = 24):
        """Clean up old conversations from memory."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        conversations_to_remove = []
        for conversation_id, conversation in self.conversations.items():
            if conversation.updated_at < cutoff_time:
                conversations_to_remove.append(conversation_id)
        
        for conversation_id in conversations_to_remove:
            del self.conversations[conversation_id]
            logger.info(f"Cleaned up old conversation: {conversation_id}")
        
        logger.info(f"Cleaned up {len(conversations_to_remove)} old conversations")
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get current conversation statistics."""
        total_conversations = len(self.conversations)
        conversations_by_provider = {}
        total_usage = AIUsage()
        
        for conversation in self.conversations.values():
            provider = conversation.model_config.provider.value
            conversations_by_provider[provider] = conversations_by_provider.get(provider, 0) + 1
            total_usage = total_usage.add_usage(conversation.total_usage)
        
        return {
            "total_conversations": total_conversations,
            "conversations_by_provider": conversations_by_provider,
            "total_usage": {
                "input_tokens": total_usage.input_tokens,
                "output_tokens": total_usage.output_tokens,
                "total_tokens": total_usage.total_tokens,
                "total_cost": total_usage.total_cost,
            },
            "available_providers": [provider.value for provider in self.client.get_available_providers()],
        }


# Global AI service instance
ai_service = AIService()