"""Integration tests for ByteBot services."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from bytebot.main import app
from bytebot.models.task import Task, TaskStatus, TaskPriority
from bytebot.models.conversation import Conversation, Message, MessageRole
from bytebot.schemas.task import TaskCreate, TaskUpdate
from bytebot.schemas.ai import AIMessage, AIRole
from bytebot.schemas.desktop import DesktopAction, ActionType


class TestFullWorkflow:
    """Test complete workflows from API to database."""

    def test_task_creation_workflow(self, test_client, db_session):
        """Test complete task creation workflow."""
        # Create task via API
        task_data = {
            "description": "Test integration task",
            "priority": "high",
            "metadata": {"source": "integration_test"}
        }
        
        response = test_client.post("/api/tasks", json=task_data)
        assert response.status_code == 201
        
        task_response = response.json()
        assert task_response["description"] == "Test integration task"
        assert task_response["priority"] == "high"
        assert task_response["status"] == "pending"
        
        # Verify task exists in database
        task_id = task_response["id"]
        db_task = db_session.get(Task, task_id)
        assert db_task is not None
        assert db_task.description == "Test integration task"
        assert db_task.priority == TaskPriority.HIGH
        assert db_task.status == TaskStatus.PENDING

    def test_conversation_workflow(self, test_client, db_session):
        """Test complete conversation workflow."""
        # Create conversation
        conv_data = {
            "title": "Integration Test Conversation",
            "metadata": {"test": True}
        }
        
        response = test_client.post("/api/conversations", json=conv_data)
        assert response.status_code == 201
        
        conv_response = response.json()
        conv_id = conv_response["id"]
        
        # Add message to conversation
        message_data = {
            "content": "Hello, this is a test message",
            "role": "user",
            "metadata": {"test_message": True}
        }
        
        response = test_client.post(
            f"/api/conversations/{conv_id}/messages",
            json=message_data
        )
        assert response.status_code == 201
        
        message_response = response.json()
        assert message_response["content"] == "Hello, this is a test message"
        assert message_response["role"] == "user"
        
        # Verify in database
        db_conv = db_session.get(Conversation, conv_id)
        assert db_conv is not None
        assert len(db_conv.messages) == 1
        assert db_conv.messages[0].content == "Hello, this is a test message"
        assert db_conv.messages[0].role == MessageRole.USER

    @patch('bytebot.services.ai.AIService.send_message')
    def test_ai_integration_workflow(self, mock_ai_service, test_client):
        """Test AI service integration workflow."""
        # Mock AI response
        mock_ai_service.return_value = {
            "content": "This is a test AI response",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 8,
                "total_tokens": 18
            }
        }
        
        # Send AI request
        ai_request = {
            "messages": [
                {
                    "role": "user",
                    "content": "Hello AI, this is a test"
                }
            ],
            "provider": "claude",
            "model": "claude-3-sonnet-20240229"
        }
        
        response = test_client.post("/api/ai/chat", json=ai_request)
        assert response.status_code == 200
        
        ai_response = response.json()
        assert ai_response["content"] == "This is a test AI response"
        assert "usage" in ai_response
        
        # Verify AI service was called
        mock_ai_service.assert_called_once()

    @patch('bytebot.services.desktop.DesktopService.take_screenshot')
    def test_desktop_integration_workflow(self, mock_screenshot, test_client):
        """Test desktop service integration workflow."""
        # Mock screenshot response
        mock_screenshot.return_value = {
            "screenshot": "base64_encoded_image_data",
            "timestamp": "2024-01-01T00:00:00Z",
            "resolution": {"width": 1920, "height": 1080}
        }
        
        # Request screenshot
        response = test_client.post("/api/desktop/screenshot")
        assert response.status_code == 200
        
        screenshot_response = response.json()
        assert "screenshot" in screenshot_response
        assert "timestamp" in screenshot_response
        assert "resolution" in screenshot_response
        
        # Verify desktop service was called
        mock_screenshot.assert_called_once()

    @patch('bytebot.services.desktop.DesktopService.perform_action')
    def test_desktop_action_workflow(self, mock_action, test_client):
        """Test desktop action workflow."""
        # Mock action response
        mock_action.return_value = {
            "success": True,
            "action_id": "test_action_123",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        # Perform desktop action
        action_data = {
            "type": "click",
            "coordinates": {"x": 100, "y": 200},
            "metadata": {"button": "left"}
        }
        
        response = test_client.post("/api/desktop/action", json=action_data)
        assert response.status_code == 200
        
        action_response = response.json()
        assert action_response["success"] is True
        assert "action_id" in action_response
        
        # Verify desktop service was called
        mock_action.assert_called_once()


class TestServiceIntegration:
    """Test integration between different services."""

    @patch('bytebot.services.ai.AIService.send_message')
    @patch('bytebot.services.desktop.DesktopService.take_screenshot')
    def test_ai_desktop_integration(self, mock_screenshot, mock_ai, test_client):
        """Test AI and desktop service integration."""
        # Mock responses
        mock_screenshot.return_value = {
            "screenshot": "base64_image",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        mock_ai.return_value = {
            "content": "I can see the desktop. Let me click on the button.",
            "usage": {"total_tokens": 50}
        }
        
        # Simulate AI analyzing screenshot
        # First get screenshot
        screenshot_response = test_client.post("/api/desktop/screenshot")
        assert screenshot_response.status_code == 200
        
        # Then send to AI for analysis
        ai_request = {
            "messages": [
                {
                    "role": "user",
                    "content": "Analyze this screenshot and suggest an action"
                }
            ],
            "provider": "claude"
        }
        
        ai_response = test_client.post("/api/ai/chat", json=ai_request)
        assert ai_response.status_code == 200
        
        # Verify both services were called
        mock_screenshot.assert_called_once()
        mock_ai.assert_called_once()

    def test_task_conversation_integration(self, test_client, db_session):
        """Test task and conversation integration."""
        # Create a task
        task_data = {
            "description": "Analyze user conversation",
            "priority": "medium"
        }
        
        task_response = test_client.post("/api/tasks", json=task_data)
        task_id = task_response.json()["id"]
        
        # Create a conversation related to the task
        conv_data = {
            "title": "Task Discussion",
            "metadata": {"related_task_id": task_id}
        }
        
        conv_response = test_client.post("/api/conversations", json=conv_data)
        conv_id = conv_response.json()["id"]
        
        # Add messages to conversation
        messages = [
            {"content": "Let's discuss this task", "role": "user"},
            {"content": "Sure, what would you like to know?", "role": "assistant"}
        ]
        
        for message in messages:
            test_client.post(
                f"/api/conversations/{conv_id}/messages",
                json=message
            )
        
        # Update task status
        task_update = {"status": "in_progress"}
        test_client.put(f"/api/tasks/{task_id}", json=task_update)
        
        # Verify integration
        db_task = db_session.get(Task, task_id)
        db_conv = db_session.get(Conversation, conv_id)
        
        assert db_task.status == TaskStatus.IN_PROGRESS
        assert db_conv.metadata["related_task_id"] == task_id
        assert len(db_conv.messages) == 2


class TestWebSocketIntegration:
    """Test WebSocket integration."""

    @pytest.mark.asyncio
    async def test_websocket_connection(self, test_client):
        """Test WebSocket connection and basic messaging."""
        with test_client.websocket_connect("/ws") as websocket:
            # Send test message
            test_message = {
                "type": "ping",
                "data": {"timestamp": "2024-01-01T00:00:00Z"}
            }
            
            websocket.send_json(test_message)
            
            # Receive response
            response = websocket.receive_json()
            assert response["type"] == "pong"

    @pytest.mark.asyncio
    @patch('bytebot.services.ai.AIService.send_message')
    async def test_websocket_ai_integration(self, mock_ai, test_client):
        """Test WebSocket AI message integration."""
        mock_ai.return_value = {
            "content": "WebSocket AI response",
            "usage": {"total_tokens": 25}
        }
        
        with test_client.websocket_connect("/ws") as websocket:
            # Send AI message via WebSocket
            ai_message = {
                "type": "ai_message",
                "data": {
                    "content": "Hello via WebSocket",
                    "provider": "claude"
                }
            }
            
            websocket.send_json(ai_message)
            
            # Receive AI response
            response = websocket.receive_json()
            assert response["type"] == "ai_response"
            assert response["data"]["content"] == "WebSocket AI response"

    @pytest.mark.asyncio
    @patch('bytebot.services.desktop.DesktopService.take_screenshot')
    async def test_websocket_desktop_integration(self, mock_screenshot, test_client):
        """Test WebSocket desktop integration."""
        mock_screenshot.return_value = {
            "screenshot": "websocket_screenshot_data",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        with test_client.websocket_connect("/ws") as websocket:
            # Request screenshot via WebSocket
            screenshot_request = {
                "type": "screenshot_request",
                "data": {}
            }
            
            websocket.send_json(screenshot_request)
            
            # Receive screenshot response
            response = websocket.receive_json()
            assert response["type"] == "screenshot_response"
            assert "screenshot" in response["data"]


class TestErrorHandlingIntegration:
    """Test error handling across services."""

    def test_database_error_handling(self, test_client):
        """Test database error handling in API."""
        # Try to create task with invalid data
        invalid_task = {
            "description": "",  # Empty description
            "priority": "invalid_priority"
        }
        
        response = test_client.post("/api/tasks", json=invalid_task)
        assert response.status_code == 422  # Validation error
        
        error_response = response.json()
        assert "detail" in error_response

    @patch('bytebot.services.ai.AIService.send_message')
    def test_ai_service_error_handling(self, mock_ai, test_client):
        """Test AI service error handling."""
        # Mock AI service to raise an exception
        mock_ai.side_effect = Exception("AI service unavailable")
        
        ai_request = {
            "messages": [{"role": "user", "content": "Test"}],
            "provider": "claude"
        }
        
        response = test_client.post("/api/ai/chat", json=ai_request)
        assert response.status_code == 500
        
        error_response = response.json()
        assert "error" in error_response

    @patch('bytebot.services.desktop.DesktopService.take_screenshot')
    def test_desktop_service_error_handling(self, mock_screenshot, test_client):
        """Test desktop service error handling."""
        # Mock desktop service to raise an exception
        mock_screenshot.side_effect = Exception("Desktop service unavailable")
        
        response = test_client.post("/api/desktop/screenshot")
        assert response.status_code == 500
        
        error_response = response.json()
        assert "error" in error_response


class TestPerformanceIntegration:
    """Test performance aspects of integration."""

    def test_concurrent_requests(self, test_client):
        """Test handling concurrent requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = test_client.get("/health")
            results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # Verify all requests succeeded
        assert len(results) == 10
        assert all(status == 200 for status in results)
        
        # Verify reasonable response time
        total_time = end_time - start_time
        assert total_time < 5.0  # Should complete within 5 seconds

    def test_large_data_handling(self, test_client, db_session):
        """Test handling large data sets."""
        # Create multiple tasks
        tasks = []
        for i in range(100):
            task_data = {
                "description": f"Large dataset task {i}",
                "priority": "low",
                "metadata": {"batch_id": "large_test", "index": i}
            }
            
            response = test_client.post("/api/tasks", json=task_data)
            assert response.status_code == 201
            tasks.append(response.json())
        
        # Verify all tasks were created
        assert len(tasks) == 100
        
        # Test pagination
        response = test_client.get("/api/tasks?limit=20&offset=0")
        assert response.status_code == 200
        
        paginated_tasks = response.json()
        assert len(paginated_tasks) <= 20

    def test_memory_usage(self, test_client):
        """Test memory usage during operations."""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform memory-intensive operations
        for _ in range(50):
            # Create and delete tasks
            task_data = {
                "description": "Memory test task",
                "priority": "low"
            }
            
            response = test_client.post("/api/tasks", json=task_data)
            task_id = response.json()["id"]
            
            # Delete the task
            test_client.delete(f"/api/tasks/{task_id}")
        
        # Get final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024


class TestSecurityIntegration:
    """Test security aspects of integration."""

    def test_api_rate_limiting(self, test_client):
        """Test API rate limiting (if implemented)."""
        # Make many requests quickly
        responses = []
        for _ in range(100):
            response = test_client.get("/health")
            responses.append(response.status_code)
        
        # Most should succeed, but rate limiting might kick in
        success_count = sum(1 for status in responses if status == 200)
        assert success_count > 50  # At least half should succeed

    def test_input_validation_integration(self, test_client):
        """Test input validation across all endpoints."""
        # Test various malicious inputs
        malicious_inputs = [
            {"description": "<script>alert('xss')</script>"},
            {"description": "'; DROP TABLE tasks; --"},
            {"description": "\x00\x01\x02"},  # Binary data
            {"description": "A" * 10000},  # Very long string
        ]
        
        for malicious_input in malicious_inputs:
            response = test_client.post("/api/tasks", json=malicious_input)
            # Should either succeed with sanitized input or fail with validation error
            assert response.status_code in [201, 422]

    def test_cors_integration(self, test_client):
        """Test CORS headers in integration."""
        # Test preflight request
        response = test_client.options(
            "/api/tasks",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers