"""Main entry point for UI server."""

import asyncio
import os
import signal
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI

from ..core.config import get_settings
from ..core.logging import get_logger
from .server import ui_server

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting ByteBot UI Server...")
    try:
        await ui_server.start()
        logger.info("ByteBot UI Server started successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to start UI server: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down ByteBot UI Server...")
        try:
            await ui_server.stop()
            logger.info("ByteBot UI Server stopped successfully")
        except Exception as e:
            logger.error(f"Error during UI server shutdown: {e}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = ui_server.get_app()
    app.router.lifespan_context = lifespan
    return app


def handle_shutdown(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    # The lifespan context manager will handle the cleanup
    exit(0)


async def main():
    """Main entry point for the UI server."""
    # Setup signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Configuration
    host = os.getenv("BYTEBOT_UI_HOST", "0.0.0.0")
    port = int(os.getenv("BYTEBOT_UI_PORT", "3000"))
    
    logger.info(f"Starting ByteBot UI Server on {host}:{port}")
    
    # Create app
    app = create_app()
    
    # Configure uvicorn
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        server_header=False,
        date_header=False,
    )
    
    # Run server
    server = uvicorn.Server(config)
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        exit(1)