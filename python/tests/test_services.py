"""Tests for service layer functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from bytebot.services.agent import AgentService
from bytebot.services.task import TaskService
from bytebot.services.conversation import ConversationService
from bytebot.models.task import Task, TaskStatus, TaskPriority
from bytebot.models.conversation import Conversation, Message, MessageRole
from bytebot.schemas.agent import TaskRequest, ConversationRequest


class TestAgentService:
    """Test agent service functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = Mock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.query = Mock()
        session.get = AsyncMock()
        session.delete = AsyncMock()
        return session

    @pytest.fixture
    def mock_ai_service(self):
        """Mock AI service."""
        service = Mock()
        service.send_message = AsyncMock(return_value="AI response")
        service.get_usage_stats = AsyncMock(return_value={
            "total_tokens": 100,
            "prompt_tokens": 50,
            "completion_tokens": 50
        })
        return service

    @pytest.fixture
    def mock_desktop_service(self):
        """Mock desktop service."""
        service = Mock()
        service.execute_action = AsyncMock()
        service.take_screenshot = AsyncMock()
        return service

    @pytest.fixture
    def agent_service(self, mock_db_session, mock_ai_service, mock_desktop_service):
        """Agent service with mocked dependencies."""
        return AgentService(
            db_session=mock_db_session,
            ai_service=mock_ai_service,
            desktop_service=mock_desktop_service
        )

    @pytest.mark.asyncio
    async def test_process_task_request(self, agent_service, mock_ai_service):
        """Test processing task request."""
        request = TaskRequest(
            description="Test task",
            priority=TaskPriority.MEDIUM
        )
        
        result = await agent_service.process_task_request(request)
        
        assert result is not None
        mock_ai_service.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_task_with_desktop_actions(self, agent_service, mock_desktop_service):
        """Test executing task with desktop actions."""
        task = Task(
            id=1,
            description="Click button",
            status=TaskStatus.PENDING,
            priority=TaskPriority.HIGH
        )
        
        await agent_service.execute_task(task)
        
        # Should interact with desktop service
        mock_desktop_service.execute_action.assert_called()

    @pytest.mark.asyncio
    async def test_get_task_status(self, agent_service, mock_db_session):
        """Test getting task status."""
        mock_task = Task(
            id=1,
            description="Test task",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM
        )
        mock_db_session.get.return_value = mock_task
        
        result = await agent_service.get_task_status(1)
        
        assert result.status == TaskStatus.IN_PROGRESS
        mock_db_session.get.assert_called_once_with(Task, 1)

    @pytest.mark.asyncio
    async def test_cancel_task(self, agent_service, mock_db_session):
        """Test canceling a task."""
        mock_task = Task(
            id=1,
            description="Test task",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM
        )
        mock_db_session.get.return_value = mock_task
        
        await agent_service.cancel_task(1)
        
        assert mock_task.status == TaskStatus.CANCELLED
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_agent_metrics(self, agent_service):
        """Test getting agent performance metrics."""
        metrics = await agent_service.get_metrics()
        
        assert "tasks_completed" in metrics
        assert "tasks_failed" in metrics
        assert "average_execution_time" in metrics
        assert "success_rate" in metrics


class TestTaskService:
    """Test task service functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = Mock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.query = Mock()
        session.get = AsyncMock()
        session.delete = AsyncMock()
        return session

    @pytest.fixture
    def task_service(self, mock_db_session):
        """Task service with mocked dependencies."""
        return TaskService(db_session=mock_db_session)

    @pytest.mark.asyncio
    async def test_create_task(self, task_service, mock_db_session):
        """Test creating a new task."""
        request = TaskRequest(
            description="New task",
            priority=TaskPriority.HIGH,
            metadata={"key": "value"}
        )
        
        result = await task_service.create_task(request)
        
        assert result.description == "New task"
        assert result.priority == TaskPriority.HIGH
        assert result.status == TaskStatus.PENDING
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_by_id(self, task_service, mock_db_session):
        """Test getting task by ID."""
        mock_task = Task(
            id=1,
            description="Test task",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM
        )
        mock_db_session.get.return_value = mock_task
        
        result = await task_service.get_task(1)
        
        assert result == mock_task
        mock_db_session.get.assert_called_once_with(Task, 1)

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, task_service, mock_db_session):
        """Test getting non-existent task."""
        mock_db_session.get.return_value = None
        
        result = await task_service.get_task(999)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_update_task(self, task_service, mock_db_session):
        """Test updating a task."""
        mock_task = Task(
            id=1,
            description="Original task",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM
        )
        mock_db_session.get.return_value = mock_task
        
        update_data = {
            "description": "Updated task",
            "status": TaskStatus.IN_PROGRESS
        }
        
        result = await task_service.update_task(1, update_data)
        
        assert result.description == "Updated task"
        assert result.status == TaskStatus.IN_PROGRESS
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_task(self, task_service, mock_db_session):
        """Test deleting a task."""
        mock_task = Task(
            id=1,
            description="Task to delete",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM
        )
        mock_db_session.get.return_value = mock_task
        
        await task_service.delete_task(1)
        
        mock_db_session.delete.assert_called_once_with(mock_task)
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self, task_service, mock_db_session):
        """Test listing tasks with filters."""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query
        
        filters = {
            "status": TaskStatus.PENDING,
            "priority": TaskPriority.HIGH
        }
        
        result = await task_service.list_tasks(filters=filters, limit=10, offset=0)
        
        assert isinstance(result, list)
        mock_db_session.query.assert_called_once_with(Task)

    @pytest.mark.asyncio
    async def test_get_task_statistics(self, task_service, mock_db_session):
        """Test getting task statistics."""
        # Mock query results for statistics
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 5
        mock_db_session.query.return_value = mock_query
        
        stats = await task_service.get_statistics()
        
        assert "total_tasks" in stats
        assert "pending_tasks" in stats
        assert "completed_tasks" in stats
        assert "failed_tasks" in stats


class TestConversationService:
    """Test conversation service functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = Mock()
        session.add = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.query = Mock()
        session.get = AsyncMock()
        session.delete = AsyncMock()
        return session

    @pytest.fixture
    def mock_ai_service(self):
        """Mock AI service."""
        service = Mock()
        service.send_message = AsyncMock(return_value="AI response")
        return service

    @pytest.fixture
    def conversation_service(self, mock_db_session, mock_ai_service):
        """Conversation service with mocked dependencies."""
        return ConversationService(
            db_session=mock_db_session,
            ai_service=mock_ai_service
        )

    @pytest.mark.asyncio
    async def test_create_conversation(self, conversation_service, mock_db_session):
        """Test creating a new conversation."""
        request = ConversationRequest(
            title="Test conversation",
            metadata={"key": "value"}
        )
        
        result = await conversation_service.create_conversation(request)
        
        assert result.title == "Test conversation"
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message(self, conversation_service, mock_db_session, mock_ai_service):
        """Test sending a message in conversation."""
        mock_conversation = Conversation(
            id=1,
            title="Test conversation"
        )
        mock_db_session.get.return_value = mock_conversation
        
        result = await conversation_service.send_message(
            conversation_id=1,
            message="Hello AI",
            role=MessageRole.USER
        )
        
        assert result is not None
        mock_ai_service.send_message.assert_called_once()
        # Should add both user message and AI response
        assert mock_db_session.add.call_count >= 2

    @pytest.mark.asyncio
    async def test_get_conversation_history(self, conversation_service, mock_db_session):
        """Test getting conversation message history."""
        mock_messages = [
            Message(
                id=1,
                conversation_id=1,
                content="Hello",
                role=MessageRole.USER
            ),
            Message(
                id=2,
                conversation_id=1,
                content="Hi there!",
                role=MessageRole.ASSISTANT
            )
        ]
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_messages
        mock_db_session.query.return_value = mock_query
        
        result = await conversation_service.get_conversation_history(1)
        
        assert len(result) == 2
        assert result[0].role == MessageRole.USER
        assert result[1].role == MessageRole.ASSISTANT

    @pytest.mark.asyncio
    async def test_delete_conversation(self, conversation_service, mock_db_session):
        """Test deleting a conversation."""
        mock_conversation = Conversation(
            id=1,
            title="Test conversation"
        )
        mock_db_session.get.return_value = mock_conversation
        
        await conversation_service.delete_conversation(1)
        
        mock_db_session.delete.assert_called_once_with(mock_conversation)
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_conversations(self, conversation_service, mock_db_session):
        """Test listing conversations."""
        mock_conversations = [
            Conversation(id=1, title="Conv 1"),
            Conversation(id=2, title="Conv 2")
        ]
        
        mock_query = Mock()
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = mock_conversations
        mock_db_session.query.return_value = mock_query
        
        result = await conversation_service.list_conversations(limit=10, offset=0)
        
        assert len(result) == 2
        assert result[0].title == "Conv 1"
        assert result[1].title == "Conv 2"

    @pytest.mark.asyncio
    async def test_search_conversations(self, conversation_service, mock_db_session):
        """Test searching conversations by title or content."""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query
        
        result = await conversation_service.search_conversations("test query")
        
        assert isinstance(result, list)
        mock_db_session.query.assert_called()


class TestServiceIntegration:
    """Integration tests for services working together."""

    @pytest.fixture
    def mock_services(self):
        """Mock all services."""
        return {
            "agent": Mock(),
            "task": Mock(),
            "conversation": Mock(),
            "ai": Mock(),
            "desktop": Mock()
        }

    @pytest.mark.asyncio
    async def test_task_to_conversation_flow(self, mock_services):
        """Test flow from task creation to conversation."""
        # This would test the integration between task and conversation services
        # when a task requires AI interaction
        pass

    @pytest.mark.asyncio
    async def test_agent_desktop_integration(self, mock_services):
        """Test agent service integrating with desktop service."""
        # This would test how agent service coordinates with desktop service
        # for task execution
        pass

    @pytest.mark.asyncio
    async def test_error_propagation(self, mock_services):
        """Test error handling across service boundaries."""
        # This would test how errors are handled when they occur
        # in one service and need to be handled by another
        pass


class TestServiceErrorHandling:
    """Test error handling in services."""

    @pytest.mark.asyncio
    async def test_database_connection_error(self):
        """Test handling database connection errors."""
        # Mock database connection failure
        mock_session = Mock()
        mock_session.commit.side_effect = Exception("Database connection lost")
        
        service = TaskService(db_session=mock_session)
        
        with pytest.raises(Exception):
            await service.create_task(TaskRequest(description="test"))

    @pytest.mark.asyncio
    async def test_ai_service_timeout(self):
        """Test handling AI service timeouts."""
        mock_ai_service = Mock()
        mock_ai_service.send_message.side_effect = TimeoutError("AI service timeout")
        
        service = ConversationService(
            db_session=Mock(),
            ai_service=mock_ai_service
        )
        
        with pytest.raises(TimeoutError):
            await service.send_message(1, "test message", MessageRole.USER)

    @pytest.mark.asyncio
    async def test_desktop_service_unavailable(self):
        """Test handling desktop service unavailability."""
        mock_desktop_service = Mock()
        mock_desktop_service.execute_action.side_effect = ConnectionError("Desktop service unavailable")
        
        service = AgentService(
            db_session=Mock(),
            ai_service=Mock(),
            desktop_service=mock_desktop_service
        )
        
        with pytest.raises(ConnectionError):
            task = Task(id=1, description="test", status=TaskStatus.PENDING, priority=TaskPriority.MEDIUM)
            await service.execute_task(task)


class TestServicePerformance:
    """Test service performance characteristics."""

    @pytest.mark.asyncio
    async def test_concurrent_task_processing(self):
        """Test handling multiple concurrent tasks."""
        # This would test how services handle concurrent requests
        # and ensure thread safety
        pass

    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """Test memory usage under load."""
        # This would test memory usage patterns
        # and ensure no memory leaks
        pass

    @pytest.mark.asyncio
    async def test_response_time(self):
        """Test service response times."""
        # This would test that services respond within acceptable time limits
        pass