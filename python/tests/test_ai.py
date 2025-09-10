"""Tests for AI functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from bytebot.ai import AIClient, AIService, ClaudeClient, OpenAIClient
from bytebot.ai.models import AIMessage, AIProvider, AIRole, AIUsage
from bytebot.models import Task, TaskExecution, User


class TestAIModels:
    """Test AI data models."""
    
    def test_ai_message_creation(self):
        """Test AI message model creation."""
        message = AIMessage(
            role=AIRole.USER,
            content="Test message",
            provider=AIProvider.CLAUDE,
        )
        
        assert message.role == AIRole.USER
        assert message.content == "Test message"
        assert message.provider == AIProvider.CLAUDE
        assert message.timestamp is not None
    
    def test_ai_usage_creation(self):
        """Test AI usage model creation."""
        usage = AIUsage(
            provider=AIProvider.OPENAI,
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )
        
        assert usage.provider == AIProvider.OPENAI
        assert usage.model == "gpt-4"
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.total_tokens == 150
    
    def test_ai_message_validation(self):
        """Test AI message validation."""
        # Test empty content validation
        with pytest.raises(ValueError):
            AIMessage(
                role=AIRole.USER,
                content="",  # Empty content should be invalid
                provider=AIProvider.CLAUDE,
            )
    
    def test_ai_usage_calculation(self):
        """Test AI usage token calculation."""
        usage = AIUsage(
            provider=AIProvider.CLAUDE,
            model="claude-3-sonnet-20240229",
            input_tokens=100,
            output_tokens=50,
        )
        
        # Total tokens should be calculated automatically
        assert usage.total_tokens == 150


class TestClaudeClient:
    """Test Claude AI client."""
    
    @pytest.fixture
    def claude_client(self):
        """Create Claude client for testing."""
        return ClaudeClient(api_key="test-key")
    
    @patch("anthropic.AsyncAnthropic")
    def test_claude_client_initialization(self, mock_anthropic, claude_client):
        """Test Claude client initialization."""
        assert claude_client.provider == AIProvider.CLAUDE
        assert claude_client.api_key == "test-key"
        mock_anthropic.assert_called_once_with(api_key="test-key")
    
    @pytest.mark.asyncio
    @patch("anthropic.AsyncAnthropic")
    async def test_claude_chat_completion(self, mock_anthropic, claude_client, mock_ai_responses):
        """Test Claude chat completion."""
        # Mock the Anthropic client response
        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value = Mock(**mock_ai_responses["claude"])
        
        messages = [
            AIMessage(role=AIRole.USER, content="Hello", provider=AIProvider.CLAUDE)
        ]
        
        response = await claude_client.chat_completion(messages)
        
        assert response.role == AIRole.ASSISTANT
        assert response.content == "Test response from Claude"
        assert response.provider == AIProvider.CLAUDE
        assert response.usage.input_tokens == 10
        assert response.usage.output_tokens == 5
    
    @pytest.mark.asyncio
    @patch("anthropic.AsyncAnthropic")
    async def test_claude_streaming_chat(self, mock_anthropic, claude_client):
        """Test Claude streaming chat."""
        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client
        
        # Mock streaming response
        async def mock_stream():
            yield Mock(type="content_block_delta", delta=Mock(text="Hello"))
            yield Mock(type="content_block_delta", delta=Mock(text=" world"))
            yield Mock(type="message_stop")
        
        mock_client.messages.stream.return_value.__aenter__.return_value = mock_stream()
        
        messages = [
            AIMessage(role=AIRole.USER, content="Hello", provider=AIProvider.CLAUDE)
        ]
        
        chunks = []
        async for chunk in claude_client.stream_chat(messages):
            chunks.append(chunk)
        
        assert len(chunks) > 0
    
    @pytest.mark.asyncio
    @patch("anthropic.AsyncAnthropic")
    async def test_claude_connection_test(self, mock_anthropic, claude_client):
        """Test Claude connection test."""
        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.return_value = Mock(
            content=[{"type": "text", "text": "Test"}]
        )
        
        is_connected = await claude_client.test_connection()
        assert is_connected is True


class TestOpenAIClient:
    """Test OpenAI client."""
    
    @pytest.fixture
    def openai_client(self):
        """Create OpenAI client for testing."""
        return OpenAIClient(api_key="test-key")
    
    @patch("openai.AsyncOpenAI")
    def test_openai_client_initialization(self, mock_openai, openai_client):
        """Test OpenAI client initialization."""
        assert openai_client.provider == AIProvider.OPENAI
        assert openai_client.api_key == "test-key"
        mock_openai.assert_called_once_with(api_key="test-key")
    
    @pytest.mark.asyncio
    @patch("openai.AsyncOpenAI")
    async def test_openai_chat_completion(self, mock_openai, openai_client, mock_ai_responses):
        """Test OpenAI chat completion."""
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = Mock(**mock_ai_responses["openai"])
        
        messages = [
            AIMessage(role=AIRole.USER, content="Hello", provider=AIProvider.OPENAI)
        ]
        
        response = await openai_client.chat_completion(messages)
        
        assert response.role == AIRole.ASSISTANT
        assert response.content == "Test response from OpenAI"
        assert response.provider == AIProvider.OPENAI
        assert response.usage.input_tokens == 10
        assert response.usage.output_tokens == 5


class TestAIClient:
    """Test unified AI client."""
    
    @pytest.fixture
    def ai_client(self):
        """Create AI client for testing."""
        return AIClient(
            anthropic_api_key="test-anthropic-key",
            openai_api_key="test-openai-key",
            gemini_api_key="test-gemini-key",
        )
    
    def test_ai_client_initialization(self, ai_client):
        """Test AI client initialization."""
        assert AIProvider.CLAUDE in ai_client.clients
        assert AIProvider.OPENAI in ai_client.clients
        assert AIProvider.GEMINI in ai_client.clients
    
    @pytest.mark.asyncio
    async def test_ai_client_chat_completion(self, ai_client):
        """Test AI client chat completion routing."""
        with patch.object(ai_client.clients[AIProvider.CLAUDE], 'chat_completion') as mock_chat:
            mock_response = AIMessage(
                role=AIRole.ASSISTANT,
                content="Test response",
                provider=AIProvider.CLAUDE,
            )
            mock_chat.return_value = mock_response
            
            messages = [
                AIMessage(role=AIRole.USER, content="Hello", provider=AIProvider.CLAUDE)
            ]
            
            response = await ai_client.chat_completion(messages, AIProvider.CLAUDE)
            
            assert response == mock_response
            mock_chat.assert_called_once_with(messages, model=None)
    
    @pytest.mark.asyncio
    async def test_ai_client_provider_fallback(self, ai_client):
        """Test AI client provider fallback."""
        with patch.object(ai_client.clients[AIProvider.CLAUDE], 'chat_completion') as mock_claude:
            with patch.object(ai_client.clients[AIProvider.OPENAI], 'chat_completion') as mock_openai:
                # Make Claude fail
                mock_claude.side_effect = Exception("Claude API error")
                
                # Make OpenAI succeed
                mock_response = AIMessage(
                    role=AIRole.ASSISTANT,
                    content="Fallback response",
                    provider=AIProvider.OPENAI,
                )
                mock_openai.return_value = mock_response
                
                messages = [
                    AIMessage(role=AIRole.USER, content="Hello", provider=AIProvider.CLAUDE)
                ]
                
                response = await ai_client.chat_completion_with_fallback(messages)
                
                assert response.provider == AIProvider.OPENAI
                mock_claude.assert_called_once()
                mock_openai.assert_called_once()


class TestAIService:
    """Test AI service."""
    
    @pytest.fixture
    def ai_service(self, async_session):
        """Create AI service for testing."""
        return AIService(db=async_session)
    
    @pytest.mark.asyncio
    async def test_send_message(self, ai_service, async_session):
        """Test sending message through AI service."""
        # Create test user and task
        user = User(email="test@example.com", name="Test User")
        async_session.add(user)
        await async_session.commit()
        
        task = Task(
            title="Test Task",
            description="Test task description",
            user_id=user.id,
        )
        async_session.add(task)
        await async_session.commit()
        
        execution = TaskExecution(
            task_id=task.id,
            status="running",
        )
        async_session.add(execution)
        await async_session.commit()
        
        with patch.object(ai_service.ai_client, 'chat_completion') as mock_chat:
            mock_response = AIMessage(
                role=AIRole.ASSISTANT,
                content="Test AI response",
                provider=AIProvider.CLAUDE,
            )
            mock_chat.return_value = mock_response
            
            response = await ai_service.send_message(
                execution_id=execution.id,
                content="Test message",
                provider=AIProvider.CLAUDE,
            )
            
            assert response.content == "Test AI response"
            assert response.role == AIRole.ASSISTANT
    
    @pytest.mark.asyncio
    async def test_get_conversation_history(self, ai_service, async_session):
        """Test getting conversation history."""
        # Create test execution
        execution = TaskExecution(
            task_id=1,  # Assuming task exists
            status="running",
        )
        async_session.add(execution)
        await async_session.commit()
        
        # Add some messages
        messages = [
            AIMessage(
                execution_id=execution.id,
                role=AIRole.USER,
                content="Hello",
                provider=AIProvider.CLAUDE,
            ),
            AIMessage(
                execution_id=execution.id,
                role=AIRole.ASSISTANT,
                content="Hi there!",
                provider=AIProvider.CLAUDE,
            ),
        ]
        
        for message in messages:
            async_session.add(message)
        await async_session.commit()
        
        history = await ai_service.get_conversation_history(execution.id)
        
        assert len(history) == 2
        assert history[0].role == AIRole.USER
        assert history[1].role == AIRole.ASSISTANT
    
    @pytest.mark.asyncio
    async def test_get_usage_stats(self, ai_service, async_session):
        """Test getting AI usage statistics."""
        # Create test usage records
        usage_records = [
            AIUsage(
                provider=AIProvider.CLAUDE,
                model="claude-3-sonnet-20240229",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
            ),
            AIUsage(
                provider=AIProvider.OPENAI,
                model="gpt-4",
                input_tokens=200,
                output_tokens=100,
                total_tokens=300,
            ),
        ]
        
        for usage in usage_records:
            async_session.add(usage)
        await async_session.commit()
        
        stats = await ai_service.get_usage_stats()
        
        assert "total_tokens" in stats
        assert "by_provider" in stats
        assert stats["total_tokens"] == 450
        assert AIProvider.CLAUDE.value in stats["by_provider"]
        assert AIProvider.OPENAI.value in stats["by_provider"]