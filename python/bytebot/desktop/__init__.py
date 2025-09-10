"""Desktop control module for ByteBot."""

from .client import DesktopClient
from .models import (
    DesktopAction,
    DesktopActionType,
    DesktopEvent,
    DesktopEventType,
    DesktopResponse,
    DesktopScreenshot,
    DesktopWindow,
    KeyboardEvent,
    MouseButton,
    MouseEvent,
    WindowInfo,
)
from .service import DesktopService, desktop_service

__all__ = [
    "DesktopClient",
    "DesktopAction",
    "DesktopActionType",
    "DesktopEvent",
    "DesktopEventType",
    "DesktopResponse",
    "DesktopScreenshot",
    "DesktopWindow",
    "KeyboardEvent",
    "MouseButton",
    "MouseEvent",
    "WindowInfo",
    "DesktopService",
    "desktop_service",
]