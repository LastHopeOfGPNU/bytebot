"""UI backend server for serving web interface and handling proxies."""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlparse

import aiofiles
import httpx
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect

from ..core.config import get_settings
from ..core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class UIServer:
    """UI backend server for web interface and API proxying."""
    
    def __init__(self):
        self.app = FastAPI(
            title="ByteBot UI Server",
            description="UI backend server for ByteBot web interface",
            version="1.0.0",
        )
        self.http_client: Optional[httpx.AsyncClient] = None
        self.static_dir: Optional[Path] = None
        self.websocket_connections: Dict[str, WebSocket] = {}
        
        # Configuration
        self.agent_base_url = os.getenv("BYTEBOT_AGENT_BASE_URL", "http://localhost:8000")
        self.desktop_vnc_url = os.getenv("BYTEBOT_DESKTOP_VNC_URL", "http://localhost:6080")
        self.ui_static_dir = os.getenv("BYTEBOT_UI_STATIC_DIR", "./static")
        
        self._setup_middleware()
        self._setup_routes()
    
    def _setup_middleware(self):
        """Setup middleware for the UI server."""
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Setup routes for the UI server."""
        
        # Health check
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "service": "bytebot-ui"}
        
        # API proxy routes
        @self.app.api_route("/api/proxy/tasks/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
        async def proxy_tasks_api(request: Request, path: str):
            """Proxy API requests to the agent service."""
            return await self._proxy_http_request(
                request=request,
                target_url=f"{self.agent_base_url}/api/{path}",
                rewrite_path=True,
            )
        
        @self.app.api_route("/api/proxy/agent/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
        async def proxy_agent_api(request: Request, path: str):
            """Proxy API requests to the agent service."""
            return await self._proxy_http_request(
                request=request,
                target_url=f"{self.agent_base_url}/api/{path}",
                rewrite_path=True,
            )
        
        @self.app.api_route("/api/proxy/websockify/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
        async def proxy_websockify_api(request: Request, path: str):
            """Proxy websockify requests to the desktop VNC service."""
            return await self._proxy_http_request(
                request=request,
                target_url=f"{self.desktop_vnc_url}/{path}",
                rewrite_path=True,
            )
        
        # WebSocket proxy routes
        @self.app.websocket("/api/proxy/tasks/ws")
        async def proxy_tasks_websocket(websocket: WebSocket):
            """Proxy WebSocket connections to the agent service."""
            await self._proxy_websocket(
                websocket=websocket,
                target_url=f"{self.agent_base_url.replace('http', 'ws')}/ws",
                connection_id="tasks",
            )
        
        @self.app.websocket("/api/proxy/websockify/ws")
        async def proxy_websockify_websocket(websocket: WebSocket):
            """Proxy WebSocket connections to the desktop VNC service."""
            await self._proxy_websocket(
                websocket=websocket,
                target_url=f"{self.desktop_vnc_url.replace('http', 'ws')}/websockify",
                connection_id="websockify",
            )
        
        # Static file serving
        @self.app.get("/static/{file_path:path}")
        async def serve_static_files(file_path: str):
            """Serve static files."""
            if not self.static_dir:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Static directory not configured",
                )
            
            file_full_path = self.static_dir / file_path
            
            if not file_full_path.exists() or not file_full_path.is_file():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found",
                )
            
            return FileResponse(file_full_path)
        
        # Default route for SPA
        @self.app.get("/{path:path}")
        async def serve_spa(path: str):
            """Serve the single page application."""
            # For SPA routing, always serve index.html for non-API routes
            if path.startswith("api/"):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="API endpoint not found",
                )
            
            if self.static_dir:
                index_file = self.static_dir / "index.html"
                if index_file.exists():
                    return FileResponse(index_file)
            
            # Fallback HTML response
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>ByteBot UI</title>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                </head>
                <body>
                    <div id="root">
                        <h1>ByteBot UI</h1>
                        <p>UI server is running, but static files are not configured.</p>
                        <p>Please configure BYTEBOT_UI_STATIC_DIR environment variable.</p>
                    </div>
                </body>
                </html>
                """
            )
    
    async def _proxy_http_request(
        self,
        request: Request,
        target_url: str,
        rewrite_path: bool = False,
    ) -> Response:
        """Proxy HTTP request to target URL."""
        try:
            if not self.http_client:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="HTTP client not initialized",
                )
            
            # Prepare headers
            headers = dict(request.headers)
            # Remove host header to avoid conflicts
            headers.pop("host", None)
            
            # Prepare request body
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
            
            # Add query parameters
            url = target_url
            if request.url.query:
                url += f"?{request.url.query}"
            
            logger.debug(f"Proxying {request.method} request to: {url}")
            
            # Make the proxied request
            response = await self.http_client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
                timeout=30.0,
            )
            
            # Prepare response headers
            response_headers = dict(response.headers)
            # Remove headers that might cause issues
            response_headers.pop("content-encoding", None)
            response_headers.pop("transfer-encoding", None)
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
            )
        
        except httpx.RequestError as e:
            logger.error(f"HTTP proxy request failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Proxy request failed: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Unexpected error in HTTP proxy: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Proxy error: {str(e)}",
            )
    
    async def _proxy_websocket(
        self,
        websocket: WebSocket,
        target_url: str,
        connection_id: str,
    ):
        """Proxy WebSocket connection to target URL."""
        await websocket.accept()
        self.websocket_connections[connection_id] = websocket
        
        try:
            # Create WebSocket connection to target
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "GET",
                    target_url,
                    headers={"Upgrade": "websocket", "Connection": "Upgrade"},
                ) as target_ws:
                    
                    # Create tasks for bidirectional communication
                    async def forward_to_target():
                        try:
                            while True:
                                data = await websocket.receive_text()
                                # Forward to target WebSocket
                                # Note: This is a simplified implementation
                                # In practice, you might need a proper WebSocket client
                                logger.debug(f"Forwarding to target: {data}")
                        except WebSocketDisconnect:
                            logger.info(f"Client WebSocket disconnected: {connection_id}")
                    
                    async def forward_to_client():
                        try:
                            # Note: This is a simplified implementation
                            # In practice, you would read from the target WebSocket
                            # and forward messages to the client
                            while True:
                                await asyncio.sleep(1)
                                # Placeholder for target WebSocket messages
                        except Exception as e:
                            logger.error(f"Error forwarding to client: {e}")
                    
                    # Run both forwarding tasks concurrently
                    await asyncio.gather(
                        forward_to_target(),
                        forward_to_client(),
                        return_exceptions=True,
                    )
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket connection closed: {connection_id}")
        except Exception as e:
            logger.error(f"WebSocket proxy error: {e}")
        finally:
            self.websocket_connections.pop(connection_id, None)
    
    async def start(self):
        """Start the UI server."""
        try:
            # Initialize HTTP client
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
            )
            
            # Setup static directory
            static_path = Path(self.ui_static_dir)
            if static_path.exists() and static_path.is_dir():
                self.static_dir = static_path
                logger.info(f"Static files directory: {static_path}")
            else:
                logger.warning(f"Static files directory not found: {static_path}")
            
            logger.info("UI server started successfully")
            logger.info(f"Agent base URL: {self.agent_base_url}")
            logger.info(f"Desktop VNC URL: {self.desktop_vnc_url}")
        
        except Exception as e:
            logger.error(f"Failed to start UI server: {e}")
            raise
    
    async def stop(self):
        """Stop the UI server."""
        try:
            # Close HTTP client
            if self.http_client:
                await self.http_client.aclose()
                self.http_client = None
            
            # Close WebSocket connections
            for connection_id, websocket in list(self.websocket_connections.items()):
                try:
                    await websocket.close()
                except Exception as e:
                    logger.warning(f"Error closing WebSocket {connection_id}: {e}")
            
            self.websocket_connections.clear()
            
            logger.info("UI server stopped successfully")
        
        except Exception as e:
            logger.error(f"Error stopping UI server: {e}")
    
    def get_app(self) -> FastAPI:
        """Get the FastAPI application instance."""
        return self.app
    
    def get_status(self) -> Dict[str, Any]:
        """Get UI server status."""
        return {
            "status": "running",
            "agent_base_url": self.agent_base_url,
            "desktop_vnc_url": self.desktop_vnc_url,
            "static_dir": str(self.static_dir) if self.static_dir else None,
            "websocket_connections": len(self.websocket_connections),
            "http_client_initialized": self.http_client is not None,
        }


# Global UI server instance
ui_server = UIServer()