"""AI client for interacting with different AI providers."""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import uuid4

import aiohttp
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from ..core.config import get_settings
from ..core.logging import get_logger
from .models import (
    AIMessage,
    AIMessageContent,
    AIMessageRole,
    AIModel,
    AIProvider,
    AIProviderConfig,
    AIResponse,
    AIStreamChunk,
    AIToolUse,
    AIUsage,
)

logger = get_logger(__name__)
settings = get_settings()


class BaseAIClient(ABC):
    """Base class for AI clients."""
    
    def __init__(self, config: AIProviderConfig):
        self.config = config
        self.provider = config.provider
    
    @abstractmethod
    async def chat(
        self,
        messages: List[AIMessage],
        model: AIModel,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
    ) -> AIResponse:
        """Send a chat completion request."""
        pass
    
    @abstractmethod
    async def stream_chat(
        self,
        messages: List[AIMessage],
        model: AIModel,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[AIStreamChunk, None]:
        """Stream a chat completion request."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test the connection to the AI provider."""
        pass
    
    def _calculate_usage_cost(self, usage: AIUsage, model: AIModel) -> AIUsage:
        """Calculate the cost of API usage."""
        input_cost = usage.input_tokens * model.input_cost_per_token
        output_cost = usage.output_tokens * model.output_cost_per_token
        total_cost = input_cost + output_cost
        
        return AIUsage(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
        )
    
    def _convert_messages_to_provider_format(self, messages: List[AIMessage]) -> List[Dict[str, Any]]:
        """Convert AIMessage objects to provider-specific format."""
        # This is a base implementation, override in subclasses
        provider_messages = []
        
        for message in messages:
            provider_message = {
                "role": message.role.value,
                "content": [],
            }
            
            for content in message.content:
                if content.type == "text" and content.text:
                    provider_message["content"].append({
                        "type": "text",
                        "text": content.text,
                    })
                elif content.type == "image":
                    if content.image_url:
                        provider_message["content"].append({
                            "type": "image_url",
                            "image_url": {"url": content.image_url},
                        })
                    elif content.image_data:
                        provider_message["content"].append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{content.image_data}"},
                        })
            
            # If only one text content, simplify to string
            if len(provider_message["content"]) == 1 and provider_message["content"][0]["type"] == "text":
                provider_message["content"] = provider_message["content"][0]["text"]
            
            provider_messages.append(provider_message)
        
        return provider_messages


class ClaudeClient(BaseAIClient):
    """Claude AI client using Anthropic API."""
    
    def __init__(self, config: AIProviderConfig):
        super().__init__(config)
        self.client = AsyncAnthropic(
            api_key=config.api_key,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
    
    async def chat(
        self,
        messages: List[AIMessage],
        model: AIModel,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
    ) -> AIResponse:
        """Send a chat completion request to Claude."""
        start_time = time.time()
        
        try:
            # Convert messages to Claude format
            claude_messages = self._convert_messages_to_claude_format(messages)
            
            # Extract system message if present
            system_message = None
            if claude_messages and claude_messages[0]["role"] == "system":
                system_message = claude_messages.pop(0)["content"]
            
            # Prepare request parameters
            request_params = {
                "model": model.id,
                "messages": claude_messages,
                "max_tokens": max_tokens or model.max_tokens,
                "temperature": temperature,
            }
            
            if system_message:
                request_params["system"] = system_message
            
            if tools:
                request_params["tools"] = tools
            
            # Make API request
            response = await self.client.messages.create(**request_params)
            
            # Convert response to our format
            response_time = time.time() - start_time
            
            # Extract content
            content_blocks = []
            tool_uses = []
            
            for content in response.content:
                if content.type == "text":
                    content_blocks.append(
                        AIMessageContent(type="text", text=content.text)
                    )
                elif content.type == "tool_use":
                    tool_use = AIToolUse(
                        id=content.id,
                        name=content.name,
                        input=content.input,
                    )
                    tool_uses.append(tool_use)
                    content_blocks.append(
                        AIMessageContent(
                            type="tool_use",
                            tool_use_id=content.id,
                            tool_name=content.name,
                            tool_input=content.input,
                        )
                    )
            
            # Create response message
            response_message = AIMessage(
                role=AIMessageRole.ASSISTANT,
                content=content_blocks,
            )
            
            # Calculate usage
            usage = AIUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )
            usage = self._calculate_usage_cost(usage, model)
            
            return AIResponse(
                id=response.id,
                model=model.id,
                provider=AIProvider.CLAUDE,
                message=response_message,
                usage=usage,
                tool_uses=tool_uses,
                finish_reason=response.stop_reason,
                response_time=response_time,
            )
        
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise
    
    async def stream_chat(
        self,
        messages: List[AIMessage],
        model: AIModel,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[AIStreamChunk, None]:
        """Stream a chat completion request to Claude."""
        try:
            # Convert messages to Claude format
            claude_messages = self._convert_messages_to_claude_format(messages)
            
            # Extract system message if present
            system_message = None
            if claude_messages and claude_messages[0]["role"] == "system":
                system_message = claude_messages.pop(0)["content"]
            
            # Prepare request parameters
            request_params = {
                "model": model.id,
                "messages": claude_messages,
                "max_tokens": max_tokens or model.max_tokens,
                "temperature": temperature,
                "stream": True,
            }
            
            if system_message:
                request_params["system"] = system_message
            
            if tools:
                request_params["tools"] = tools
            
            # Make streaming API request
            async with self.client.messages.stream(**request_params) as stream:
                async for chunk in stream:
                    if chunk.type == "content_block_delta":
                        if chunk.delta.type == "text_delta":
                            yield AIStreamChunk(
                                id=str(uuid4()),
                                model=model.id,
                                provider=AIProvider.CLAUDE,
                                delta=chunk.delta.text,
                            )
                    elif chunk.type == "message_stop":
                        # Final chunk with usage information
                        if hasattr(chunk, "usage"):
                            usage = AIUsage(
                                input_tokens=chunk.usage.input_tokens,
                                output_tokens=chunk.usage.output_tokens,
                                total_tokens=chunk.usage.input_tokens + chunk.usage.output_tokens,
                            )
                            usage = self._calculate_usage_cost(usage, model)
                            
                            yield AIStreamChunk(
                                id=str(uuid4()),
                                model=model.id,
                                provider=AIProvider.CLAUDE,
                                finish_reason="stop",
                                usage=usage,
                            )
        
        except Exception as e:
            logger.error(f"Claude streaming API error: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """Test the connection to Claude API."""
        try:
            # Send a simple test message
            test_messages = [
                AIMessage.create_user_message("Hello, can you respond with just 'OK'?")
            ]
            
            # Use a simple model for testing
            test_model = AIModel(
                id="claude-3-haiku-20240307",
                name="Claude 3 Haiku",
                provider=AIProvider.CLAUDE,
                max_tokens=4096,
                context_window=200000,
                input_cost_per_token=0.00000025,
                output_cost_per_token=0.00000125,
            )
            
            response = await self.chat(
                messages=test_messages,
                model=test_model,
                max_tokens=10,
                temperature=0.0,
            )
            
            return response is not None
        
        except Exception as e:
            logger.error(f"Claude connection test failed: {e}")
            return False
    
    def _convert_messages_to_claude_format(self, messages: List[AIMessage]) -> List[Dict[str, Any]]:
        """Convert AIMessage objects to Claude-specific format."""
        claude_messages = []
        
        for message in messages:
            claude_message = {
                "role": message.role.value,
                "content": [],
            }
            
            for content in message.content:
                if content.type == "text" and content.text:
                    claude_message["content"].append({
                        "type": "text",
                        "text": content.text,
                    })
                elif content.type == "image":
                    if content.image_data:
                        claude_message["content"].append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": content.image_data,
                            },
                        })
                elif content.type == "tool_use":
                    claude_message["content"].append({
                        "type": "tool_use",
                        "id": content.tool_use_id,
                        "name": content.tool_name,
                        "input": content.tool_input,
                    })
                elif content.type == "tool_result":
                    claude_message["content"].append({
                        "type": "tool_result",
                        "tool_use_id": content.tool_use_id,
                        "content": content.tool_result,
                        "is_error": content.is_error,
                    })
            
            # If only one text content, simplify to string
            if len(claude_message["content"]) == 1 and claude_message["content"][0]["type"] == "text":
                claude_message["content"] = claude_message["content"][0]["text"]
            
            claude_messages.append(claude_message)
        
        return claude_messages


class OpenAIClient(BaseAIClient):
    """OpenAI client using OpenAI API."""
    
    def __init__(self, config: AIProviderConfig):
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            organization=config.organization,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
    
    async def chat(
        self,
        messages: List[AIMessage],
        model: AIModel,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
    ) -> AIResponse:
        """Send a chat completion request to OpenAI."""
        start_time = time.time()
        
        try:
            # Convert messages to OpenAI format
            openai_messages = self._convert_messages_to_openai_format(messages)
            
            # Prepare request parameters
            request_params = {
                "model": model.id,
                "messages": openai_messages,
                "temperature": temperature,
            }
            
            if max_tokens:
                request_params["max_tokens"] = max_tokens
            
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = "auto"
            
            # Make API request
            response = await self.client.chat.completions.create(**request_params)
            
            # Convert response to our format
            response_time = time.time() - start_time
            choice = response.choices[0]
            
            # Extract content
            content_blocks = []
            tool_uses = []
            
            if choice.message.content:
                content_blocks.append(
                    AIMessageContent(type="text", text=choice.message.content)
                )
            
            if choice.message.tool_calls:
                for tool_call in choice.message.tool_calls:
                    tool_use = AIToolUse(
                        id=tool_call.id,
                        name=tool_call.function.name,
                        input=json.loads(tool_call.function.arguments),
                    )
                    tool_uses.append(tool_use)
                    content_blocks.append(
                        AIMessageContent(
                            type="tool_use",
                            tool_use_id=tool_call.id,
                            tool_name=tool_call.function.name,
                            tool_input=json.loads(tool_call.function.arguments),
                        )
                    )
            
            # Create response message
            response_message = AIMessage(
                role=AIMessageRole.ASSISTANT,
                content=content_blocks,
            )
            
            # Calculate usage
            usage = AIUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
            usage = self._calculate_usage_cost(usage, model)
            
            return AIResponse(
                id=response.id,
                model=model.id,
                provider=AIProvider.OPENAI,
                message=response_message,
                usage=usage,
                tool_uses=tool_uses,
                finish_reason=choice.finish_reason,
                response_time=response_time,
            )
        
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def stream_chat(
        self,
        messages: List[AIMessage],
        model: AIModel,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[AIStreamChunk, None]:
        """Stream a chat completion request to OpenAI."""
        try:
            # Convert messages to OpenAI format
            openai_messages = self._convert_messages_to_openai_format(messages)
            
            # Prepare request parameters
            request_params = {
                "model": model.id,
                "messages": openai_messages,
                "temperature": temperature,
                "stream": True,
            }
            
            if max_tokens:
                request_params["max_tokens"] = max_tokens
            
            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = "auto"
            
            # Make streaming API request
            stream = await self.client.chat.completions.create(**request_params)
            
            async for chunk in stream:
                if chunk.choices:
                    choice = chunk.choices[0]
                    
                    if choice.delta.content:
                        yield AIStreamChunk(
                            id=chunk.id,
                            model=model.id,
                            provider=AIProvider.OPENAI,
                            delta=choice.delta.content,
                        )
                    
                    if choice.delta.tool_calls:
                        for tool_call in choice.delta.tool_calls:
                            if tool_call.function and tool_call.function.name:
                                tool_use = AIToolUse(
                                    id=tool_call.id,
                                    name=tool_call.function.name,
                                    input=json.loads(tool_call.function.arguments or "{}"),
                                )
                                yield AIStreamChunk(
                                    id=chunk.id,
                                    model=model.id,
                                    provider=AIProvider.OPENAI,
                                    tool_use=tool_use,
                                )
                    
                    if choice.finish_reason:
                        yield AIStreamChunk(
                            id=chunk.id,
                            model=model.id,
                            provider=AIProvider.OPENAI,
                            finish_reason=choice.finish_reason,
                        )
        
        except Exception as e:
            logger.error(f"OpenAI streaming API error: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """Test the connection to OpenAI API."""
        try:
            # Send a simple test message
            test_messages = [
                AIMessage.create_user_message("Hello, can you respond with just 'OK'?")
            ]
            
            # Use a simple model for testing
            test_model = AIModel(
                id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                provider=AIProvider.OPENAI,
                max_tokens=4096,
                context_window=16385,
                input_cost_per_token=0.0000005,
                output_cost_per_token=0.0000015,
            )
            
            response = await self.chat(
                messages=test_messages,
                model=test_model,
                max_tokens=10,
                temperature=0.0,
            )
            
            return response is not None
        
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {e}")
            return False
    
    def _convert_messages_to_openai_format(self, messages: List[AIMessage]) -> List[Dict[str, Any]]:
        """Convert AIMessage objects to OpenAI-specific format."""
        openai_messages = []
        
        for message in messages:
            openai_message = {
                "role": message.role.value,
                "content": [],
            }
            
            # Handle tool role mapping
            if message.role == AIMessageRole.TOOL:
                openai_message["role"] = "tool"
                # For tool messages, we need tool_call_id
                for content in message.content:
                    if content.type == "tool_result" and content.tool_use_id:
                        openai_message["tool_call_id"] = content.tool_use_id
                        openai_message["content"] = str(content.tool_result)
                        break
            else:
                for content in message.content:
                    if content.type == "text" and content.text:
                        openai_message["content"].append({
                            "type": "text",
                            "text": content.text,
                        })
                    elif content.type == "image":
                        if content.image_url:
                            openai_message["content"].append({
                                "type": "image_url",
                                "image_url": {"url": content.image_url},
                            })
                        elif content.image_data:
                            openai_message["content"].append({
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{content.image_data}"},
                            })
                
                # If only one text content, simplify to string
                if len(openai_message["content"]) == 1 and openai_message["content"][0]["type"] == "text":
                    openai_message["content"] = openai_message["content"][0]["text"]
                elif not openai_message["content"]:
                    openai_message["content"] = ""
            
            # Handle tool calls for assistant messages
            if message.role == AIMessageRole.ASSISTANT:
                tool_calls = []
                for content in message.content:
                    if content.type == "tool_use":
                        tool_calls.append({
                            "id": content.tool_use_id,
                            "type": "function",
                            "function": {
                                "name": content.tool_name,
                                "arguments": json.dumps(content.tool_input or {}),
                            },
                        })
                
                if tool_calls:
                    openai_message["tool_calls"] = tool_calls
            
            openai_messages.append(openai_message)
        
        return openai_messages


class AIClient:
    """Unified AI client that can work with multiple providers."""
    
    def __init__(self):
        self.clients: Dict[AIProvider, BaseAIClient] = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize clients for available providers."""
        # Claude client
        if settings.CLAUDE_API_KEY:
            claude_config = AIProviderConfig(
                provider=AIProvider.CLAUDE,
                api_key=settings.CLAUDE_API_KEY,
                timeout=30,
                max_retries=3,
            )
            self.clients[AIProvider.CLAUDE] = ClaudeClient(claude_config)
        
        # OpenAI client
        if settings.OPENAI_API_KEY:
            openai_config = AIProviderConfig(
                provider=AIProvider.OPENAI,
                api_key=settings.OPENAI_API_KEY,
                organization=getattr(settings, 'OPENAI_ORGANIZATION', None),
                timeout=30,
                max_retries=3,
            )
            self.clients[AIProvider.OPENAI] = OpenAIClient(openai_config)
    
    def get_client(self, provider: AIProvider) -> Optional[BaseAIClient]:
        """Get a client for a specific provider."""
        return self.clients.get(provider)
    
    async def chat(
        self,
        messages: List[AIMessage],
        model: AIModel,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
    ) -> AIResponse:
        """Send a chat completion request using the appropriate client."""
        client = self.get_client(model.provider)
        if not client:
            raise ValueError(f"No client available for provider: {model.provider}")
        
        return await client.chat(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
            stream=stream,
        )
    
    async def stream_chat(
        self,
        messages: List[AIMessage],
        model: AIModel,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[AIStreamChunk, None]:
        """Stream a chat completion request using the appropriate client."""
        client = self.get_client(model.provider)
        if not client:
            raise ValueError(f"No client available for provider: {model.provider}")
        
        async for chunk in client.stream_chat(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
        ):
            yield chunk
    
    async def test_connection(self, provider: AIProvider) -> bool:
        """Test the connection to a specific provider."""
        client = self.get_client(provider)
        if not client:
            return False
        
        return await client.test_connection()
    
    async def test_all_connections(self) -> Dict[AIProvider, bool]:
        """Test connections to all available providers."""
        results = {}
        
        for provider, client in self.clients.items():
            try:
                results[provider] = await client.test_connection()
            except Exception as e:
                logger.error(f"Connection test failed for {provider}: {e}")
                results[provider] = False
        
        return results
    
    def get_available_providers(self) -> List[AIProvider]:
        """Get list of available providers."""
        return list(self.clients.keys())
    
    def is_provider_available(self, provider: AIProvider) -> bool:
        """Check if a provider is available."""
        return provider in self.clients