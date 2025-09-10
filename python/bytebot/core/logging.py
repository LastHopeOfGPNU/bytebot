"""Logging configuration for the application."""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger

from .config import settings


class CustomJSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # Add service information
        log_record["service"] = "bytebot"
        log_record["version"] = "0.1.0"
        
        # Add level name
        log_record["level"] = record.levelname
        
        # Add module information
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno


class CustomTextFormatter(logging.Formatter):
    """Custom text formatter with colors and structured output."""

    # Color codes
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Add timestamp
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        # Add color if terminal supports it
        level_color = self.COLORS.get(record.levelname, "")
        reset_color = self.RESET if level_color else ""
        
        # Format message
        formatted = (
            f"{timestamp} | "
            f"{level_color}{record.levelname:8}{reset_color} | "
            f"{record.name:20} | "
            f"{record.module}:{record.lineno:4} | "
            f"{record.getMessage()}"
        )
        
        # Add exception info if present
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)
        
        return formatted


def setup_logging() -> None:
    """Setup application logging configuration."""
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level))
    
    # Set formatter based on configuration
    if settings.log_format == "json":
        formatter = CustomJSONFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s"
        )
    else:
        formatter = CustomTextFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    configure_third_party_loggers()


def configure_third_party_loggers() -> None:
    """Configure third-party library loggers."""
    # SQLAlchemy
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    
    # Alembic
    logging.getLogger("alembic").setLevel(logging.INFO)
    
    # FastAPI/Uvicorn
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # HTTP clients
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Celery
    logging.getLogger("celery").setLevel(logging.INFO)
    
    # WebSocket
    logging.getLogger("websockets").setLevel(logging.INFO)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name. If None, uses the caller's module name.
    
    Returns:
        Logger instance.
    """
    if name is None:
        # Get caller's module name
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            name = frame.f_back.f_globals.get("__name__", "bytebot")
        else:
            name = "bytebot"
    
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capability to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")


# Context manager for structured logging
class LogContext:
    """Context manager for adding structured context to logs."""
    
    def __init__(self, **context: Any):
        """Initialize log context.
        
        Args:
            **context: Key-value pairs to add to log context.
        """
        self.context = context
        self.old_factory = logging.getLogRecordFactory()
    
    def __enter__(self) -> "LogContext":
        """Enter context manager."""
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        logging.setLogRecordFactory(self.old_factory)


# Initialize logging on module import
setup_logging()