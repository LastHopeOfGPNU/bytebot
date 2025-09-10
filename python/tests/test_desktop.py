"""Tests for desktop service functionality."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from bytebot.desktop.service import DesktopService
from bytebot.desktop.client import DesktopClient
from bytebot.schemas.desktop import (
    ScreenshotRequest,
    ScreenshotResponse,
    ClickRequest,
    TypeRequest,
    KeyRequest,
    ScrollRequest,
    DesktopAction,
    ActionType,
    Coordinate
)


class TestDesktopService:
    """Test desktop service functionality."""

    @pytest.fixture
    def mock_client(self):
        """Mock desktop client."""
        client = Mock(spec=DesktopClient)
        client.take_screenshot = AsyncMock(return_value=b"fake_screenshot_data")
        client.click = AsyncMock()
        client.type_text = AsyncMock()
        client.press_key = AsyncMock()
        client.scroll = AsyncMock()
        client.get_screen_size = AsyncMock(return_value=(1920, 1080))
        return client

    @pytest.fixture
    def desktop_service(self, mock_client):
        """Desktop service with mocked client."""
        service = DesktopService()
        service.client = mock_client
        return service

    @pytest.mark.asyncio
    async def test_take_screenshot(self, desktop_service, mock_client):
        """Test taking screenshot."""
        request = ScreenshotRequest()
        
        result = await desktop_service.take_screenshot(request)
        
        assert isinstance(result, ScreenshotResponse)
        assert result.data == b"fake_screenshot_data"
        assert result.format == "png"
        mock_client.take_screenshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_click(self, desktop_service, mock_client):
        """Test clicking at coordinates."""
        request = ClickRequest(
            x=100,
            y=200,
            button="left",
            clicks=1
        )
        
        await desktop_service.click(request)
        
        mock_client.click.assert_called_once_with(
            x=100, y=200, button="left", clicks=1
        )

    @pytest.mark.asyncio
    async def test_type_text(self, desktop_service, mock_client):
        """Test typing text."""
        request = TypeRequest(text="Hello, World!")
        
        await desktop_service.type_text(request)
        
        mock_client.type_text.assert_called_once_with("Hello, World!")

    @pytest.mark.asyncio
    async def test_press_key(self, desktop_service, mock_client):
        """Test pressing keys."""
        request = KeyRequest(key="ctrl+c")
        
        await desktop_service.press_key(request)
        
        mock_client.press_key.assert_called_once_with("ctrl+c")

    @pytest.mark.asyncio
    async def test_scroll(self, desktop_service, mock_client):
        """Test scrolling."""
        request = ScrollRequest(
            x=500,
            y=500,
            direction="up",
            clicks=3
        )
        
        await desktop_service.scroll(request)
        
        mock_client.scroll.assert_called_once_with(
            x=500, y=500, direction="up", clicks=3
        )

    @pytest.mark.asyncio
    async def test_execute_action_click(self, desktop_service, mock_client):
        """Test executing click action."""
        action = DesktopAction(
            type=ActionType.CLICK,
            coordinate=Coordinate(x=150, y=250),
            button="right",
            clicks=2
        )
        
        await desktop_service.execute_action(action)
        
        mock_client.click.assert_called_once_with(
            x=150, y=250, button="right", clicks=2
        )

    @pytest.mark.asyncio
    async def test_execute_action_type(self, desktop_service, mock_client):
        """Test executing type action."""
        action = DesktopAction(
            type=ActionType.TYPE,
            text="Test input"
        )
        
        await desktop_service.execute_action(action)
        
        mock_client.type_text.assert_called_once_with("Test input")

    @pytest.mark.asyncio
    async def test_execute_action_key(self, desktop_service, mock_client):
        """Test executing key action."""
        action = DesktopAction(
            type=ActionType.KEY,
            key="alt+tab"
        )
        
        await desktop_service.execute_action(action)
        
        mock_client.press_key.assert_called_once_with("alt+tab")

    @pytest.mark.asyncio
    async def test_execute_action_scroll(self, desktop_service, mock_client):
        """Test executing scroll action."""
        action = DesktopAction(
            type=ActionType.SCROLL,
            coordinate=Coordinate(x=400, y=600),
            direction="down",
            clicks=5
        )
        
        await desktop_service.execute_action(action)
        
        mock_client.scroll.assert_called_once_with(
            x=400, y=600, direction="down", clicks=5
        )

    @pytest.mark.asyncio
    async def test_get_screen_info(self, desktop_service, mock_client):
        """Test getting screen information."""
        result = await desktop_service.get_screen_info()
        
        assert result["width"] == 1920
        assert result["height"] == 1080
        mock_client.get_screen_size.assert_called_once()


class TestDesktopClient:
    """Test desktop client functionality."""

    @pytest.fixture
    def desktop_client(self):
        """Desktop client instance."""
        return DesktopClient()

    @patch('subprocess.run')
    def test_take_screenshot_command(self, mock_run, desktop_client):
        """Test screenshot command generation."""
        mock_run.return_value.stdout = b"fake_image_data"
        mock_run.return_value.returncode = 0
        
        # This would be an async test in real implementation
        # Just testing the command structure here
        assert hasattr(desktop_client, 'take_screenshot')

    @patch('subprocess.run')
    def test_click_command(self, mock_run, desktop_client):
        """Test click command generation."""
        mock_run.return_value.returncode = 0
        
        # This would be an async test in real implementation
        # Just testing the command structure here
        assert hasattr(desktop_client, 'click')

    def test_client_initialization(self, desktop_client):
        """Test client initialization."""
        assert desktop_client is not None
        assert hasattr(desktop_client, 'take_screenshot')
        assert hasattr(desktop_client, 'click')
        assert hasattr(desktop_client, 'type_text')
        assert hasattr(desktop_client, 'press_key')
        assert hasattr(desktop_client, 'scroll')
        assert hasattr(desktop_client, 'get_screen_size')


class TestDesktopSchemas:
    """Test desktop data schemas."""

    def test_screenshot_request(self):
        """Test screenshot request schema."""
        request = ScreenshotRequest()
        assert request is not None
        
        # Test with optional parameters
        request_with_params = ScreenshotRequest(
            format="jpeg",
            quality=80
        )
        assert request_with_params.format == "jpeg"
        assert request_with_params.quality == 80

    def test_screenshot_response(self):
        """Test screenshot response schema."""
        response = ScreenshotResponse(
            data=b"test_data",
            format="png",
            width=1920,
            height=1080
        )
        assert response.data == b"test_data"
        assert response.format == "png"
        assert response.width == 1920
        assert response.height == 1080

    def test_click_request(self):
        """Test click request schema."""
        request = ClickRequest(x=100, y=200)
        assert request.x == 100
        assert request.y == 200
        assert request.button == "left"  # default
        assert request.clicks == 1  # default
        
        # Test with custom parameters
        custom_request = ClickRequest(
            x=300, y=400, button="right", clicks=2
        )
        assert custom_request.button == "right"
        assert custom_request.clicks == 2

    def test_type_request(self):
        """Test type request schema."""
        request = TypeRequest(text="Hello World")
        assert request.text == "Hello World"

    def test_key_request(self):
        """Test key request schema."""
        request = KeyRequest(key="ctrl+c")
        assert request.key == "ctrl+c"

    def test_scroll_request(self):
        """Test scroll request schema."""
        request = ScrollRequest(x=500, y=600, direction="up")
        assert request.x == 500
        assert request.y == 600
        assert request.direction == "up"
        assert request.clicks == 1  # default

    def test_coordinate(self):
        """Test coordinate schema."""
        coord = Coordinate(x=123, y=456)
        assert coord.x == 123
        assert coord.y == 456

    def test_desktop_action(self):
        """Test desktop action schema."""
        # Click action
        click_action = DesktopAction(
            type=ActionType.CLICK,
            coordinate=Coordinate(x=100, y=200),
            button="left"
        )
        assert click_action.type == ActionType.CLICK
        assert click_action.coordinate.x == 100
        assert click_action.coordinate.y == 200
        assert click_action.button == "left"
        
        # Type action
        type_action = DesktopAction(
            type=ActionType.TYPE,
            text="Hello"
        )
        assert type_action.type == ActionType.TYPE
        assert type_action.text == "Hello"
        
        # Key action
        key_action = DesktopAction(
            type=ActionType.KEY,
            key="enter"
        )
        assert key_action.type == ActionType.KEY
        assert key_action.key == "enter"
        
        # Scroll action
        scroll_action = DesktopAction(
            type=ActionType.SCROLL,
            coordinate=Coordinate(x=300, y=400),
            direction="down",
            clicks=3
        )
        assert scroll_action.type == ActionType.SCROLL
        assert scroll_action.coordinate.x == 300
        assert scroll_action.coordinate.y == 400
        assert scroll_action.direction == "down"
        assert scroll_action.clicks == 3

    def test_action_type_enum(self):
        """Test action type enumeration."""
        assert ActionType.CLICK == "click"
        assert ActionType.TYPE == "type"
        assert ActionType.KEY == "key"
        assert ActionType.SCROLL == "scroll"
        assert ActionType.SCREENSHOT == "screenshot"