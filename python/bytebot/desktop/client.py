"""Desktop control client for Linux desktop interaction."""

import asyncio
import base64
import json
import subprocess
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import psutil
from PIL import Image, ImageGrab

from ..core.logging import get_logger
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

logger = get_logger(__name__)


class DesktopClient:
    """Client for interacting with Linux desktop environment."""
    
    def __init__(self):
        self.is_connected = False
        self.display = None
        self._init_display()
    
    def _init_display(self):
        """Initialize display connection."""
        try:
            # Try to get display from environment
            import os
            self.display = os.environ.get("DISPLAY", ":0")
            
            # Test X11 connection
            result = subprocess.run(
                ["xdpyinfo", "-display", self.display],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            if result.returncode == 0:
                self.is_connected = True
                logger.info(f"Connected to X11 display: {self.display}")
            else:
                logger.warning(f"Failed to connect to X11 display: {self.display}")
        
        except Exception as e:
            logger.error(f"Failed to initialize display: {e}")
    
    async def execute_action(self, action: DesktopAction) -> DesktopResponse:
        """Execute a desktop action."""
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Executing desktop action: {action.type} (ID: {action.id})")
            
            # Route action to appropriate handler
            if action.type in [
                DesktopActionType.MOUSE_CLICK,
                DesktopActionType.MOUSE_DOUBLE_CLICK,
                DesktopActionType.MOUSE_RIGHT_CLICK,
                DesktopActionType.MOUSE_MOVE,
                DesktopActionType.MOUSE_DRAG,
                DesktopActionType.MOUSE_SCROLL,
            ]:
                response = await self._handle_mouse_action(action)
            
            elif action.type in [
                DesktopActionType.KEY_PRESS,
                DesktopActionType.KEY_RELEASE,
                DesktopActionType.KEY_COMBINATION,
                DesktopActionType.TYPE_TEXT,
            ]:
                response = await self._handle_keyboard_action(action)
            
            elif action.type in [
                DesktopActionType.WINDOW_FOCUS,
                DesktopActionType.WINDOW_CLOSE,
                DesktopActionType.WINDOW_MINIMIZE,
                DesktopActionType.WINDOW_MAXIMIZE,
                DesktopActionType.WINDOW_RESTORE,
                DesktopActionType.WINDOW_MOVE,
                DesktopActionType.WINDOW_RESIZE,
            ]:
                response = await self._handle_window_action(action)
            
            elif action.type == DesktopActionType.SCREENSHOT:
                response = await self._handle_screenshot_action(action)
            
            elif action.type in [
                DesktopActionType.APP_LAUNCH,
                DesktopActionType.APP_CLOSE,
                DesktopActionType.APP_SWITCH,
            ]:
                response = await self._handle_app_action(action)
            
            elif action.type in [
                DesktopActionType.CLIPBOARD_GET,
                DesktopActionType.CLIPBOARD_SET,
            ]:
                response = await self._handle_clipboard_action(action)
            
            elif action.type in [
                DesktopActionType.WAIT,
                DesktopActionType.WAIT_FOR_ELEMENT,
                DesktopActionType.WAIT_FOR_WINDOW,
            ]:
                response = await self._handle_wait_action(action)
            
            else:
                response = DesktopResponse.error_response(
                    action_id=action.id,
                    error=f"Unsupported action type: {action.type}",
                )
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            response.execution_time = execution_time
            
            logger.info(
                f"Desktop action {action.type} completed in {execution_time:.3f}s: "
                f"{'success' if response.success else 'failed'}"
            )
            
            return response
        
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Desktop action {action.type} failed after {execution_time:.3f}s: {e}")
            
            return DesktopResponse.error_response(
                action_id=action.id,
                error=str(e),
                execution_time=execution_time,
            )
    
    async def _handle_mouse_action(self, action: DesktopAction) -> DesktopResponse:
        """Handle mouse actions."""
        try:
            if action.type == DesktopActionType.MOUSE_CLICK:
                await self._mouse_click(action.x or 0, action.y or 0, action.button or MouseButton.LEFT)
            
            elif action.type == DesktopActionType.MOUSE_DOUBLE_CLICK:
                await self._mouse_double_click(action.x or 0, action.y or 0)
            
            elif action.type == DesktopActionType.MOUSE_RIGHT_CLICK:
                await self._mouse_click(action.x or 0, action.y or 0, MouseButton.RIGHT)
            
            elif action.type == DesktopActionType.MOUSE_MOVE:
                await self._mouse_move(action.x or 0, action.y or 0)
            
            elif action.type == DesktopActionType.MOUSE_DRAG:
                # Drag from current position to target
                await self._mouse_drag(
                    action.x or 0,
                    action.y or 0,
                    action.width or 0,
                    action.height or 0,
                )
            
            elif action.type == DesktopActionType.MOUSE_SCROLL:
                await self._mouse_scroll(action.x or 0, action.y or 0, action.scroll_delta or 1)
            
            return DesktopResponse.success_response(
                action_id=action.id,
                message=f"Mouse action {action.type} completed",
            )
        
        except Exception as e:
            return DesktopResponse.error_response(
                action_id=action.id,
                error=f"Mouse action failed: {e}",
            )
    
    async def _handle_keyboard_action(self, action: DesktopAction) -> DesktopResponse:
        """Handle keyboard actions."""
        try:
            if action.type == DesktopActionType.KEY_PRESS:
                await self._key_press(action.key or "")
            
            elif action.type == DesktopActionType.KEY_RELEASE:
                await self._key_release(action.key or "")
            
            elif action.type == DesktopActionType.KEY_COMBINATION:
                await self._key_combination(action.keys or [])
            
            elif action.type == DesktopActionType.TYPE_TEXT:
                await self._type_text(action.text or "")
            
            return DesktopResponse.success_response(
                action_id=action.id,
                message=f"Keyboard action {action.type} completed",
            )
        
        except Exception as e:
            return DesktopResponse.error_response(
                action_id=action.id,
                error=f"Keyboard action failed: {e}",
            )
    
    async def _handle_window_action(self, action: DesktopAction) -> DesktopResponse:
        """Handle window actions."""
        try:
            windows = await self.get_windows()
            target_window = None
            
            # Find target window
            if action.window_id:
                target_window = next(
                    (w for w in windows if w.info.id == action.window_id),
                    None,
                )
            elif action.window_title:
                target_window = next(
                    (w for w in windows if action.window_title.lower() in w.info.title.lower()),
                    None,
                )
            
            if not target_window:
                return DesktopResponse.error_response(
                    action_id=action.id,
                    error="Target window not found",
                )
            
            if action.type == DesktopActionType.WINDOW_FOCUS:
                await self._window_focus(target_window.info.id)
            
            elif action.type == DesktopActionType.WINDOW_CLOSE:
                await self._window_close(target_window.info.id)
            
            elif action.type == DesktopActionType.WINDOW_MINIMIZE:
                await self._window_minimize(target_window.info.id)
            
            elif action.type == DesktopActionType.WINDOW_MAXIMIZE:
                await self._window_maximize(target_window.info.id)
            
            elif action.type == DesktopActionType.WINDOW_RESTORE:
                await self._window_restore(target_window.info.id)
            
            elif action.type == DesktopActionType.WINDOW_MOVE:
                await self._window_move(target_window.info.id, action.x or 0, action.y or 0)
            
            elif action.type == DesktopActionType.WINDOW_RESIZE:
                await self._window_resize(
                    target_window.info.id,
                    action.width or target_window.info.width,
                    action.height or target_window.info.height,
                )
            
            return DesktopResponse.success_response(
                action_id=action.id,
                message=f"Window action {action.type} completed",
                windows=[target_window],
            )
        
        except Exception as e:
            return DesktopResponse.error_response(
                action_id=action.id,
                error=f"Window action failed: {e}",
            )
    
    async def _handle_screenshot_action(self, action: DesktopAction) -> DesktopResponse:
        """Handle screenshot action."""
        try:
            screenshot = await self.take_screenshot()
            
            return DesktopResponse.success_response(
                action_id=action.id,
                message="Screenshot taken successfully",
                screenshot=screenshot,
            )
        
        except Exception as e:
            return DesktopResponse.error_response(
                action_id=action.id,
                error=f"Screenshot failed: {e}",
            )
    
    async def _handle_app_action(self, action: DesktopAction) -> DesktopResponse:
        """Handle application actions."""
        try:
            if action.type == DesktopActionType.APP_LAUNCH:
                await self._app_launch(action.app_name or action.app_path or "", action.app_args or [])
            
            elif action.type == DesktopActionType.APP_CLOSE:
                await self._app_close(action.app_name or "")
            
            elif action.type == DesktopActionType.APP_SWITCH:
                await self._app_switch(action.app_name or "")
            
            return DesktopResponse.success_response(
                action_id=action.id,
                message=f"Application action {action.type} completed",
            )
        
        except Exception as e:
            return DesktopResponse.error_response(
                action_id=action.id,
                error=f"Application action failed: {e}",
            )
    
    async def _handle_clipboard_action(self, action: DesktopAction) -> DesktopResponse:
        """Handle clipboard actions."""
        try:
            if action.type == DesktopActionType.CLIPBOARD_GET:
                content = await self._clipboard_get()
                return DesktopResponse.success_response(
                    action_id=action.id,
                    message="Clipboard content retrieved",
                    clipboard_content=content,
                )
            
            elif action.type == DesktopActionType.CLIPBOARD_SET:
                await self._clipboard_set(action.text or "")
                return DesktopResponse.success_response(
                    action_id=action.id,
                    message="Clipboard content set",
                )
        
        except Exception as e:
            return DesktopResponse.error_response(
                action_id=action.id,
                error=f"Clipboard action failed: {e}",
            )
    
    async def _handle_wait_action(self, action: DesktopAction) -> DesktopResponse:
        """Handle wait actions."""
        try:
            if action.type == DesktopActionType.WAIT:
                await asyncio.sleep(action.wait_time or 1.0)
            
            elif action.type == DesktopActionType.WAIT_FOR_WINDOW:
                await self._wait_for_window(action.window_title or "", action.wait_time or 10.0)
            
            elif action.type == DesktopActionType.WAIT_FOR_ELEMENT:
                # TODO: Implement element waiting
                await asyncio.sleep(action.wait_time or 1.0)
            
            return DesktopResponse.success_response(
                action_id=action.id,
                message=f"Wait action {action.type} completed",
            )
        
        except Exception as e:
            return DesktopResponse.error_response(
                action_id=action.id,
                error=f"Wait action failed: {e}",
            )
    
    # Low-level action implementations
    
    async def _mouse_click(self, x: int, y: int, button: MouseButton):
        """Perform mouse click."""
        button_map = {
            MouseButton.LEFT: "1",
            MouseButton.RIGHT: "3",
            MouseButton.MIDDLE: "2",
        }
        
        button_num = button_map.get(button, "1")
        
        # Use xdotool for mouse click
        await self._run_command(["xdotool", "mousemove", str(x), str(y)])
        await self._run_command(["xdotool", "click", button_num])
    
    async def _mouse_double_click(self, x: int, y: int):
        """Perform mouse double click."""
        await self._run_command(["xdotool", "mousemove", str(x), str(y)])
        await self._run_command(["xdotool", "click", "--repeat", "2", "1"])
    
    async def _mouse_move(self, x: int, y: int):
        """Move mouse to position."""
        await self._run_command(["xdotool", "mousemove", str(x), str(y)])
    
    async def _mouse_drag(self, start_x: int, start_y: int, end_x: int, end_y: int):
        """Perform mouse drag."""
        await self._run_command(["xdotool", "mousemove", str(start_x), str(start_y)])
        await self._run_command(["xdotool", "mousedown", "1"])
        await self._run_command(["xdotool", "mousemove", str(end_x), str(end_y)])
        await self._run_command(["xdotool", "mouseup", "1"])
    
    async def _mouse_scroll(self, x: int, y: int, delta: int):
        """Perform mouse scroll."""
        await self._run_command(["xdotool", "mousemove", str(x), str(y)])
        
        if delta > 0:
            button = "4"  # Scroll up
        else:
            button = "5"  # Scroll down
            delta = abs(delta)
        
        for _ in range(delta):
            await self._run_command(["xdotool", "click", button])
    
    async def _key_press(self, key: str):
        """Press a key."""
        await self._run_command(["xdotool", "keydown", key])
    
    async def _key_release(self, key: str):
        """Release a key."""
        await self._run_command(["xdotool", "keyup", key])
    
    async def _key_combination(self, keys: List[str]):
        """Press key combination."""
        key_combo = "+".join(keys)
        await self._run_command(["xdotool", "key", key_combo])
    
    async def _type_text(self, text: str):
        """Type text."""
        await self._run_command(["xdotool", "type", text])
    
    async def _window_focus(self, window_id: int):
        """Focus window."""
        await self._run_command(["xdotool", "windowfocus", str(window_id)])
    
    async def _window_close(self, window_id: int):
        """Close window."""
        await self._run_command(["xdotool", "windowclose", str(window_id)])
    
    async def _window_minimize(self, window_id: int):
        """Minimize window."""
        await self._run_command(["xdotool", "windowminimize", str(window_id)])
    
    async def _window_maximize(self, window_id: int):
        """Maximize window."""
        await self._run_command(["wmctrl", "-i", "-r", str(window_id), "-b", "add,maximized_vert,maximized_horz"])
    
    async def _window_restore(self, window_id: int):
        """Restore window."""
        await self._run_command(["wmctrl", "-i", "-r", str(window_id), "-b", "remove,maximized_vert,maximized_horz"])
    
    async def _window_move(self, window_id: int, x: int, y: int):
        """Move window."""
        await self._run_command(["xdotool", "windowmove", str(window_id), str(x), str(y)])
    
    async def _window_resize(self, window_id: int, width: int, height: int):
        """Resize window."""
        await self._run_command(["xdotool", "windowsize", str(window_id), str(width), str(height)])
    
    async def _app_launch(self, app: str, args: List[str]):
        """Launch application."""
        cmd = [app] + args
        await self._run_command(cmd, wait=False)
    
    async def _app_close(self, app_name: str):
        """Close application by name."""
        # Find and close processes by name
        for proc in psutil.process_iter(['pid', 'name']):
            if app_name.lower() in proc.info['name'].lower():
                proc.terminate()
    
    async def _app_switch(self, app_name: str):
        """Switch to application."""
        windows = await self.get_windows()
        target_window = next(
            (w for w in windows if app_name.lower() in w.info.title.lower()),
            None,
        )
        
        if target_window:
            await self._window_focus(target_window.info.id)
    
    async def _clipboard_get(self) -> str:
        """Get clipboard content."""
        result = await self._run_command(["xclip", "-selection", "clipboard", "-o"])
        return result.stdout.strip() if result.stdout else ""
    
    async def _clipboard_set(self, content: str):
        """Set clipboard content."""
        process = await asyncio.create_subprocess_exec(
            "xclip", "-selection", "clipboard",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        await process.communicate(input=content.encode())
    
    async def _wait_for_window(self, window_title: str, timeout: float):
        """Wait for window to appear."""
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            windows = await self.get_windows()
            if any(window_title.lower() in w.info.title.lower() for w in windows):
                return
            
            await asyncio.sleep(0.5)
        
        raise TimeoutError(f"Window '{window_title}' not found within {timeout} seconds")
    
    async def _run_command(self, cmd: List[str], wait: bool = True) -> subprocess.CompletedProcess:
        """Run system command."""
        if wait:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=process.returncode,
                stdout=stdout.decode() if stdout else None,
                stderr=stderr.decode() if stderr else None,
            )
        else:
            await asyncio.create_subprocess_exec(*cmd)
            return subprocess.CompletedProcess(args=cmd, returncode=0)
    
    # High-level methods
    
    async def take_screenshot(self) -> DesktopScreenshot:
        """Take a screenshot of the desktop."""
        try:
            # Use scrot for screenshot
            result = await self._run_command(["scrot", "-"])
            
            if result.returncode != 0:
                raise Exception(f"Screenshot failed: {result.stderr}")
            
            # Convert to base64
            image_data = base64.b64encode(result.stdout.encode()).decode()
            
            # Get image dimensions (approximate)
            width, height = 1920, 1080  # Default values
            
            try:
                # Try to get actual screen resolution
                xrandr_result = await self._run_command(["xrandr"])
                if xrandr_result.stdout:
                    for line in xrandr_result.stdout.split("\n"):
                        if "*" in line and "x" in line:
                            resolution = line.split()[0]
                            if "x" in resolution:
                                width, height = map(int, resolution.split("x"))
                                break
            except Exception:
                pass  # Use default values
            
            return DesktopScreenshot(
                width=width,
                height=height,
                data=image_data,
                file_size=len(result.stdout),
            )
        
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            raise
    
    async def get_windows(self) -> List[DesktopWindow]:
        """Get list of desktop windows."""
        try:
            # Use wmctrl to get window list
            result = await self._run_command(["wmctrl", "-l", "-G"])
            
            if result.returncode != 0:
                return []
            
            windows = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                
                parts = line.split(None, 6)
                if len(parts) < 7:
                    continue
                
                window_id = int(parts[0], 16)
                desktop = int(parts[1])
                x = int(parts[2])
                y = int(parts[3])
                width = int(parts[4])
                height = int(parts[5])
                title = parts[6] if len(parts) > 6 else ""
                
                # Get additional window info
                window_info = WindowInfo(
                    id=window_id,
                    title=title,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    is_visible=desktop >= 0,
                )
                
                windows.append(DesktopWindow(info=window_info))
            
            return windows
        
        except Exception as e:
            logger.error(f"Failed to get windows: {e}")
            return []
    
    async def get_active_window(self) -> Optional[DesktopWindow]:
        """Get the currently active window."""
        try:
            result = await self._run_command(["xdotool", "getactivewindow"])
            
            if result.returncode != 0:
                return None
            
            window_id = int(result.stdout.strip())
            windows = await self.get_windows()
            
            return next((w for w in windows if w.info.id == window_id), None)
        
        except Exception as e:
            logger.error(f"Failed to get active window: {e}")
            return None
    
    async def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        try:
            result = await self._run_command(["xdotool", "getmouselocation", "--shell"])
            
            if result.returncode != 0:
                return (0, 0)
            
            x, y = 0, 0
            for line in result.stdout.strip().split("\n"):
                if line.startswith("X="):
                    x = int(line.split("=")[1])
                elif line.startswith("Y="):
                    y = int(line.split("=")[1])
            
            return (x, y)
        
        except Exception as e:
            logger.error(f"Failed to get mouse position: {e}")
            return (0, 0)
    
    async def test_connection(self) -> bool:
        """Test desktop connection."""
        try:
            result = await self._run_command(["xdpyinfo", "-display", self.display or ":0"])
            return result.returncode == 0
        except Exception:
            return False
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get desktop client capabilities."""
        return {
            "platform": "linux",
            "display": self.display,
            "connected": self.is_connected,
            "supported_actions": [action.value for action in DesktopActionType],
            "tools": {
                "xdotool": self._check_tool("xdotool"),
                "wmctrl": self._check_tool("wmctrl"),
                "xclip": self._check_tool("xclip"),
                "scrot": self._check_tool("scrot"),
                "xrandr": self._check_tool("xrandr"),
            },
        }
    
    def _check_tool(self, tool_name: str) -> bool:
        """Check if a tool is available."""
        try:
            result = subprocess.run(
                ["which", tool_name],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False