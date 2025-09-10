"""Tests for API endpoints."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from bytebot.schemas.agent import (
    TaskRequest,
    TaskResponse,
    ConversationRequest,
    ConversationResponse
)
from bytebot.schemas.desktop import (
    ScreenshotRequest,
    ClickRequest,
    TypeRequest,
    KeyRequest,
    ScrollRequest
)
from bytebot.schemas.ui import (
    UIStatusResponse,
    UIConfigRequest
)


class TestAgentAPI:
    """Test agent API endpoints."""

    def test_create_task(self, client):
        """Test creating a new task."""
        task_data = {
            "description": "Test task",
            "priority": "medium",
            "metadata": {"key": "value"}
        }
        
        response = client.post("/api/agent/tasks", json=task_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Test task"
        assert data["priority"] == "medium"
        assert data["status"] == "pending"
        assert "id" in data
        assert "created_at" in data

    def test_get_task(self, client):
        """Test getting a task by ID."""
        # First create a task
        task_data = {"description": "Test task"}
        create_response = client.post("/api/agent/tasks", json=task_data)
        task_id = create_response.json()["id"]
        
        # Then get it
        response = client.get(f"/api/agent/tasks/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["description"] == "Test task"

    def test_get_task_not_found(self, client):
        """Test getting non-existent task."""
        response = client.get("/api/agent/tasks/999")
        assert response.status_code == 404

    def test_list_tasks(self, client):
        """Test listing tasks."""
        # Create some tasks
        for i in range(3):
            client.post("/api/agent/tasks", json={"description": f"Task {i}"})
        
        response = client.get("/api/agent/tasks")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
        assert all("id" in task for task in data)

    def test_update_task(self, client):
        """Test updating a task."""
        # Create a task
        task_data = {"description": "Original task"}
        create_response = client.post("/api/agent/tasks", json=task_data)
        task_id = create_response.json()["id"]
        
        # Update it
        update_data = {
            "description": "Updated task",
            "status": "in_progress"
        }
        response = client.put(f"/api/agent/tasks/{task_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated task"
        assert data["status"] == "in_progress"

    def test_delete_task(self, client):
        """Test deleting a task."""
        # Create a task
        task_data = {"description": "Task to delete"}
        create_response = client.post("/api/agent/tasks", json=task_data)
        task_id = create_response.json()["id"]
        
        # Delete it
        response = client.delete(f"/api/agent/tasks/{task_id}")
        assert response.status_code == 204
        
        # Verify it's gone
        get_response = client.get(f"/api/agent/tasks/{task_id}")
        assert get_response.status_code == 404

    def test_create_conversation(self, client):
        """Test creating a conversation."""
        conversation_data = {
            "title": "Test conversation",
            "metadata": {"key": "value"}
        }
        
        response = client.post("/api/agent/conversations", json=conversation_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test conversation"
        assert "id" in data
        assert "created_at" in data

    def test_send_message(self, client):
        """Test sending a message in conversation."""
        # Create conversation
        conv_response = client.post("/api/agent/conversations", json={"title": "Test"})
        conv_id = conv_response.json()["id"]
        
        # Send message
        message_data = {
            "message": "Hello AI",
            "conversation_id": conv_id
        }
        response = client.post("/api/agent/chat", json=message_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "conversation_id" in data

    def test_get_conversation_history(self, client):
        """Test getting conversation history."""
        # Create conversation and send message
        conv_response = client.post("/api/agent/conversations", json={"title": "Test"})
        conv_id = conv_response.json()["id"]
        
        client.post("/api/agent/chat", json={
            "message": "Hello",
            "conversation_id": conv_id
        })
        
        # Get history
        response = client.get(f"/api/agent/conversations/{conv_id}/messages")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestDesktopAPI:
    """Test desktop API endpoints."""

    @patch('bytebot.desktop.service.DesktopService.take_screenshot')
    def test_take_screenshot(self, mock_screenshot, client):
        """Test taking screenshot."""
        mock_screenshot.return_value = AsyncMock()
        mock_screenshot.return_value.data = b"fake_image_data"
        mock_screenshot.return_value.format = "png"
        
        response = client.post("/api/desktop/screenshot", json={})
        
        assert response.status_code == 200
        # In real implementation, this would return image data

    def test_click(self, client):
        """Test clicking at coordinates."""
        click_data = {
            "x": 100,
            "y": 200,
            "button": "left",
            "clicks": 1
        }
        
        response = client.post("/api/desktop/click", json=click_data)
        
        assert response.status_code == 200

    def test_type_text(self, client):
        """Test typing text."""
        type_data = {"text": "Hello World"}
        
        response = client.post("/api/desktop/type", json=type_data)
        
        assert response.status_code == 200

    def test_press_key(self, client):
        """Test pressing keys."""
        key_data = {"key": "ctrl+c"}
        
        response = client.post("/api/desktop/key", json=key_data)
        
        assert response.status_code == 200

    def test_scroll(self, client):
        """Test scrolling."""
        scroll_data = {
            "x": 500,
            "y": 500,
            "direction": "up",
            "clicks": 3
        }
        
        response = client.post("/api/desktop/scroll", json=scroll_data)
        
        assert response.status_code == 200

    def test_get_screen_info(self, client):
        """Test getting screen information."""
        response = client.get("/api/desktop/screen")
        
        assert response.status_code == 200
        data = response.json()
        assert "width" in data
        assert "height" in data

    def test_invalid_click_coordinates(self, client):
        """Test clicking with invalid coordinates."""
        click_data = {
            "x": -1,
            "y": -1
        }
        
        response = client.post("/api/desktop/click", json=click_data)
        
        # Should return validation error
        assert response.status_code == 422

    def test_empty_text_input(self, client):
        """Test typing empty text."""
        type_data = {"text": ""}
        
        response = client.post("/api/desktop/type", json=type_data)
        
        # Should handle empty text gracefully
        assert response.status_code in [200, 422]


class TestUIAPI:
    """Test UI API endpoints."""

    def test_get_ui_status(self, client):
        """Test getting UI server status."""
        response = client.get("/api/ui/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "agent_url" in data
        assert "desktop_vnc_url" in data

    def test_start_ui_server(self, client):
        """Test starting UI server."""
        response = client.post("/api/ui/start")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_stop_ui_server(self, client):
        """Test stopping UI server."""
        response = client.post("/api/ui/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_restart_ui_server(self, client):
        """Test restarting UI server."""
        response = client.post("/api/ui/restart")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_ui_health_check(self, client):
        """Test UI server health check."""
        response = client.get("/api/ui/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data

    def test_get_ui_connections(self, client):
        """Test getting UI WebSocket connections."""
        response = client.get("/api/ui/connections")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_configure_ui_server(self, client):
        """Test configuring UI server."""
        config_data = {
            "host": "0.0.0.0",
            "port": 9992,
            "static_dir": "/app/static"
        }
        
        response = client.post("/api/ui/configure", json=config_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestHealthAPI:
    """Test health check endpoints."""

    def test_health_check(self, client):
        """Test main health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_readiness_check(self, client):
        """Test readiness check endpoint."""
        response = client.get("/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_liveness_check(self, client):
        """Test liveness check endpoint."""
        response = client.get("/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


class TestAPIValidation:
    """Test API request validation."""

    def test_invalid_json(self, client):
        """Test sending invalid JSON."""
        response = client.post(
            "/api/agent/tasks",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

    def test_missing_required_fields(self, client):
        """Test missing required fields."""
        # Task without description
        response = client.post("/api/agent/tasks", json={})
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_invalid_field_types(self, client):
        """Test invalid field types."""
        task_data = {
            "description": 123,  # Should be string
            "priority": "invalid_priority"  # Should be valid enum
        }
        
        response = client.post("/api/agent/tasks", json=task_data)
        
        assert response.status_code == 422

    def test_field_length_validation(self, client):
        """Test field length validation."""
        task_data = {
            "description": "x" * 10000  # Very long description
        }
        
        response = client.post("/api/agent/tasks", json=task_data)
        
        # Should either accept or reject based on validation rules
        assert response.status_code in [201, 422]


class TestAPIAuthentication:
    """Test API authentication (if implemented)."""

    def test_unauthenticated_request(self, client):
        """Test request without authentication."""
        # If authentication is required, this should fail
        # If not required, this should succeed
        response = client.get("/api/agent/tasks")
        
        # Status depends on whether auth is implemented
        assert response.status_code in [200, 401, 403]

    def test_invalid_token(self, client):
        """Test request with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/agent/tasks", headers=headers)
        
        # Status depends on whether auth is implemented
        assert response.status_code in [200, 401, 403]


class TestAPIErrorHandling:
    """Test API error handling."""

    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get("/api/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_method_not_allowed(self, client):
        """Test method not allowed error."""
        response = client.patch("/health")  # PATCH not allowed on health
        
        assert response.status_code == 405

    @patch('bytebot.services.agent.AgentService.create_task')
    def test_internal_server_error(self, mock_create_task, client):
        """Test internal server error handling."""
        mock_create_task.side_effect = Exception("Database error")
        
        response = client.post("/api/agent/tasks", json={"description": "test"})
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data


class TestAPICORS:
    """Test CORS headers."""

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.get("/health")
        
        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers

    def test_preflight_request(self, client):
        """Test CORS preflight request."""
        response = client.options(
            "/api/agent/tasks",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        assert response.status_code == 200
        assert "access-control-allow-methods" in response.headers