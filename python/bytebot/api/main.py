"""Main FastAPI application router."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import time
import uuid
from contextlib import asynccontextmanager

from ..core.config import settings
from ..core.database import init_database, close_database
from ..core.logging import get_logger
from ..core.exceptions import BytebotException, HTTP_EXCEPTION_MAP
from ..websocket import websocket_manager, websocket_router
from .v1 import api_router
from .desktop import router as desktop_router
from .ui import ui_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Bytebot Agent service...")
    await init_database()
    logger.info("Database initialized")
    
    # Start WebSocket manager
    await websocket_manager.start()
    logger.info("WebSocket manager started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Bytebot Agent service...")
    
    # Stop WebSocket manager
    await websocket_manager.stop()
    logger.info("WebSocket manager stopped")
    
    # Close database connections
    await close_database()
    logger.info("Database connections closed")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Bytebot Agent API",
        description="AI Desktop Agent Service",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )
    
    # Add middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # CORS middleware
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    # Exception handlers
    @app.exception_handler(BytebotException)
    async def bytebot_exception_handler(request: Request, exc: BytebotException):
        """Handle custom Bytebot exceptions."""
        logger.error(
            f"Bytebot exception: {exc.__class__.__name__}: {exc.message}",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "path": request.url.path,
                "method": request.method,
                "error_code": exc.error_code,
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": exc.__class__.__name__,
                    "message": exc.message,
                    "code": exc.error_code,
                    "request_id": getattr(request.state, "request_id", None),
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.exception(
            f"Unhandled exception: {exc.__class__.__name__}: {str(exc)}",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "path": request.url.path,
                "method": request.method,
            }
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "InternalServerError",
                    "message": "An internal server error occurred",
                    "code": "INTERNAL_ERROR",
                    "request_id": getattr(request.state, "request_id", None),
                }
            }
        )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "bytebot-agent",
            "version": "0.1.0",
            "timestamp": time.time(),
        }
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    # Include desktop control routes
    app.include_router(desktop_router, prefix="/api")
    
    # Include UI routes
    app.include_router(ui_router, prefix="/api")
    
    # Include WebSocket routes
    app.include_router(websocket_router, prefix="/api", tags=["websocket"])
    
    return app


# Create the app instance
app = create_app()