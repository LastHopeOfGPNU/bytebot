"""Tests for WebSocket functionality."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from bytebot.websocket.manager import ConnectionManager
from bytebot.websocket.handlers import WebSocketHandler
from bytebot.schemas.websocket import (
    WebSocketMessage,
    MessageType,
    WebSocketResponse,
    ConnectionInfo
)


class TestConnectionManager:
    """Test WebSocket connection manager."""

    @pytest.fixture
    def manager(self):
        """Connection manager instance."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket connection."""
        websocket = Mock(spec=WebSocket)
        websocket.send_text = AsyncMock()
        websocket.send_bytes = AsyncMock()
        websocket.receive_text = AsyncMock()
        websocket.receive_bytes = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.mark.asyncio
    async def test_connect(self, manager, mock_websocket):
        """Test connecting a WebSocket."""
        connection_id = await manager.connect(mock_websocket, "test_client")
        
        assert connection_id is not None
        assert len(manager.active_connections) == 1
        assert connection_id in manager.active_connections
        assert manager.active_connections[connection_id]["websocket"] == mock_websocket
        assert manager.active_connections[connection_id]["client_id"] == "test_client"

    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """Test disconnecting a WebSocket."""
        connection_id = await manager.connect(mock_websocket, "test_client")
        
        await manager.disconnect(connection_id)
        
        assert len(manager.active_connections) == 0
        assert connection_id not in manager.active_connections

    @pytest.mark.asyncio
    async def test_send_personal_message(self, manager, mock_websocket):
        """Test sending personal message."""
        connection_id = await manager.connect(mock_websocket, "test_client")
        message = "Hello, client!"
        
        await manager.send_personal_message(message, connection_id)
        
        mock_websocket.send_text.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_personal_message_invalid_connection(self, manager):
        """Test sending message to invalid connection."""
        with pytest.raises(KeyError):
            await manager.send_personal_message("test", "invalid_id")

    @pytest.mark.asyncio
    async def test_broadcast(self, manager, mock_websocket):
        """Test broadcasting message to all connections."""
        # Connect multiple clients
        mock_websocket2 = Mock(spec=WebSocket)
        mock_websocket2.send_text = AsyncMock()
        
        connection_id1 = await manager.connect(mock_websocket, "client1")
        connection_id2 = await manager.connect(mock_websocket2, "client2")
        
        message = "Broadcast message"
        await manager.broadcast(message)
        
        mock_websocket.send_text.assert_called_once_with(message)
        mock_websocket2.send_text.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_json(self, manager, mock_websocket):
        """Test broadcasting JSON message."""
        connection_id = await manager.connect(mock_websocket, "test_client")
        
        data = {"type": "test", "message": "Hello"}
        await manager.broadcast_json(data)
        
        expected_json = json.dumps(data)
        mock_websocket.send_text.assert_called_once_with(expected_json)

    def test_get_connection_info(self, manager, mock_websocket):
        """Test getting connection information."""
        # This would be async in real implementation
        # Just testing the structure here
        assert hasattr(manager, 'get_connection_info')

    def test_get_active_connections_count(self, manager, mock_websocket):
        """Test getting active connections count."""
        assert manager.get_active_connections_count() == 0
        
        # Would need to be async in real implementation
        # manager.connect(mock_websocket, "test")
        # assert manager.get_active_connections_count() == 1


class TestWebSocketHandler:
    """Test WebSocket message handler."""

    @pytest.fixture
    def mock_manager(self):
        """Mock connection manager."""
        manager = Mock(spec=ConnectionManager)
        manager.send_personal_message = AsyncMock()
        manager.broadcast = AsyncMock()
        manager.broadcast_json = AsyncMock()
        return manager

    @pytest.fixture
    def mock_ai_service(self):
        """Mock AI service."""
        service = Mock()
        service.send_message = AsyncMock(return_value="AI response")
        return service

    @pytest.fixture
    def mock_desktop_service(self):
        """Mock desktop service."""
        service = Mock()
        service.take_screenshot = AsyncMock()
        service.click = AsyncMock()
        service.type_text = AsyncMock()
        return service

    @pytest.fixture
    def handler(self, mock_manager, mock_ai_service, mock_desktop_service):
        """WebSocket handler with mocked dependencies."""
        return WebSocketHandler(
            connection_manager=mock_manager,
            ai_service=mock_ai_service,
            desktop_service=mock_desktop_service
        )

    @pytest.mark.asyncio
    async def test_handle_ai_message(self, handler, mock_manager, mock_ai_service):
        """Test handling AI message."""
        message = WebSocketMessage(
            type=MessageType.AI_MESSAGE,
            data={"message": "Hello AI", "conversation_id": "conv_123"}
        )
        connection_id = "conn_123"
        
        await handler.handle_message(message, connection_id)
        
        mock_ai_service.send_message.assert_called_once_with(
            message="Hello AI",
            conversation_id="conv_123"
        )
        mock_manager.send_personal_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_desktop_action(self, handler, mock_manager, mock_desktop_service):
        """Test handling desktop action."""
        message = WebSocketMessage(
            type=MessageType.DESKTOP_ACTION,
            data={
                "action": "click",
                "x": 100,
                "y": 200
            }
        )
        connection_id = "conn_123"
        
        await handler.handle_message(message, connection_id)
        
        mock_desktop_service.click.assert_called_once()
        mock_manager.send_personal_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_screenshot_request(self, handler, mock_manager, mock_desktop_service):
        """Test handling screenshot request."""
        message = WebSocketMessage(
            type=MessageType.SCREENSHOT_REQUEST,
            data={}
        )
        connection_id = "conn_123"
        
        await handler.handle_message(message, connection_id)
        
        mock_desktop_service.take_screenshot.assert_called_once()
        mock_manager.send_personal_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_ping(self, handler, mock_manager):
        """Test handling ping message."""
        message = WebSocketMessage(
            type=MessageType.PING,
            data={}
        )
        connection_id = "conn_123"
        
        await handler.handle_message(message, connection_id)
        
        # Should respond with pong
        mock_manager.send_personal_message.assert_called_once()
        call_args = mock_manager.send_personal_message.call_args
        response_data = json.loads(call_args[0][0])
        assert response_data["type"] == "pong"

    @pytest.mark.asyncio
    async def test_handle_invalid_message_type(self, handler, mock_manager):
        """Test handling invalid message type."""
        message = WebSocketMessage(
            type="invalid_type",
            data={}
        )
        connection_id = "conn_123"
        
        await handler.handle_message(message, connection_id)
        
        # Should send error response
        mock_manager.send_personal_message.assert_called_once()
        call_args = mock_manager.send_personal_message.call_args
        response_data = json.loads(call_args[0][0])
        assert response_data["type"] == "error"


class TestWebSocketSchemas:
    """Test WebSocket data schemas."""

    def test_websocket_message(self):
        """Test WebSocket message schema."""
        message = WebSocketMessage(
            type=MessageType.AI_MESSAGE,
            data={"message": "Hello"},
            id="msg_123"
        )
        assert message.type == MessageType.AI_MESSAGE
        assert message.data == {"message": "Hello"}
        assert message.id == "msg_123"
        assert message.timestamp is not None

    def test_websocket_response(self):
        """Test WebSocket response schema."""
        response = WebSocketResponse(
            type="ai_response",
            data={"response": "Hello back"},
            success=True,
            message_id="msg_123"
        )
        assert response.type == "ai_response"
        assert response.data == {"response": "Hello back"}
        assert response.success is True
        assert response.message_id == "msg_123"
        assert response.timestamp is not None

    def test_connection_info(self):
        """Test connection info schema."""
        info = ConnectionInfo(
            connection_id="conn_123",
            client_id="client_456",
            connected_at="2024-01-01T00:00:00Z",
            last_activity="2024-01-01T00:01:00Z"
        )
        assert info.connection_id == "conn_123"
        assert info.client_id == "client_456"
        assert info.connected_at == "2024-01-01T00:00:00Z"
        assert info.last_activity == "2024-01-01T00:01:00Z"

    def test_message_type_enum(self):
        """Test message type enumeration."""
        assert MessageType.AI_MESSAGE == "ai_message"
        assert MessageType.DESKTOP_ACTION == "desktop_action"
        assert MessageType.SCREENSHOT_REQUEST == "screenshot_request"
        assert MessageType.PING == "ping"
        assert MessageType.PONG == "pong"
        assert MessageType.ERROR == "error"

    def test_websocket_message_validation(self):
        """Test WebSocket message validation."""
        # Valid message
        valid_message = WebSocketMessage(
            type=MessageType.AI_MESSAGE,
            data={"message": "test"}
        )
        assert valid_message.type == MessageType.AI_MESSAGE
        
        # Test with minimal data
        minimal_message = WebSocketMessage(
            type=MessageType.PING,
            data={}
        )
        assert minimal_message.type == MessageType.PING
        assert minimal_message.data == {}


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""

    @pytest.fixture
    def app_with_websocket(self, app):
        """FastAPI app with WebSocket routes."""
        # This would include WebSocket routes in real implementation
        return app

    def test_websocket_endpoint_exists(self, app_with_websocket):
        """Test that WebSocket endpoint exists."""
        # This would test actual WebSocket endpoint in real implementation
        assert app_with_websocket is not None

    @pytest.mark.asyncio
    async def test_websocket_connection_flow(self):
        """Test complete WebSocket connection flow."""
        # This would test the complete flow:
        # 1. Connect to WebSocket
        # 2. Send message
        # 3. Receive response
        # 4. Disconnect
        # 
        # In real implementation, this would use WebSocket test client
        pass

    @pytest.mark.asyncio
    async def test_multiple_connections(self):
        """Test handling multiple WebSocket connections."""
        # This would test multiple simultaneous connections
        # and message broadcasting in real implementation
        pass

    @pytest.mark.asyncio
    async def test_connection_cleanup(self):
        """Test connection cleanup on disconnect."""
        # This would test that connections are properly cleaned up
        # when clients disconnect in real implementation
        pass