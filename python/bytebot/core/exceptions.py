"""Custom exceptions for the Bytebot application."""

from typing import Any, Dict, Optional


class BytebotException(Exception):
    """Base exception for all Bytebot-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize exception.
        
        Args:
            message: Error message
            error_code: Optional error code for API responses
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


class ValidationError(BytebotException):
    """Raised when input validation fails."""
    pass


class AuthenticationError(BytebotException):
    """Raised when authentication fails."""
    pass


class AuthorizationError(BytebotException):
    """Raised when authorization fails."""
    pass


class NotFoundError(BytebotException):
    """Raised when a requested resource is not found."""
    pass


class ConflictError(BytebotException):
    """Raised when a resource conflict occurs."""
    pass


class DatabaseError(BytebotException):
    """Raised when database operations fail."""
    pass


class ExternalServiceError(BytebotException):
    """Raised when external service calls fail."""
    
    def __init__(
        self,
        message: str,
        service_name: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        **kwargs,
    ):
        """Initialize external service error.
        
        Args:
            message: Error message
            service_name: Name of the external service
            status_code: HTTP status code if applicable
            response_body: Response body from the service
            **kwargs: Additional arguments for base exception
        """
        super().__init__(message, **kwargs)
        self.service_name = service_name
        self.status_code = status_code
        self.response_body = response_body
        
        # Add service details to exception details
        self.details.update({
            "service_name": service_name,
            "status_code": status_code,
            "response_body": response_body,
        })


class LLMProviderError(ExternalServiceError):
    """Raised when LLM provider API calls fail."""
    
    def __init__(
        self,
        message: str,
        provider: str,
        model: Optional[str] = None,
        **kwargs,
    ):
        """Initialize LLM provider error.
        
        Args:
            message: Error message
            provider: LLM provider name (e.g., 'openai', 'anthropic')
            model: Model name if applicable
            **kwargs: Additional arguments for external service error
        """
        super().__init__(message, service_name=provider, **kwargs)
        self.provider = provider
        self.model = model
        
        # Add provider details
        self.details.update({
            "provider": provider,
            "model": model,
        })


class TaskError(BytebotException):
    """Raised when task execution fails."""
    
    def __init__(
        self,
        message: str,
        task_id: Optional[str] = None,
        task_type: Optional[str] = None,
        **kwargs,
    ):
        """Initialize task error.
        
        Args:
            message: Error message
            task_id: Task ID if applicable
            task_type: Task type if applicable
            **kwargs: Additional arguments for base exception
        """
        super().__init__(message, **kwargs)
        self.task_id = task_id
        self.task_type = task_type
        
        # Add task details
        self.details.update({
            "task_id": task_id,
            "task_type": task_type,
        })


class ComputerUseError(BytebotException):
    """Raised when computer use operations fail."""
    
    def __init__(
        self,
        message: str,
        action_type: Optional[str] = None,
        coordinates: Optional[tuple] = None,
        **kwargs,
    ):
        """Initialize computer use error.
        
        Args:
            message: Error message
            action_type: Type of computer action that failed
            coordinates: Screen coordinates if applicable
            **kwargs: Additional arguments for base exception
        """
        super().__init__(message, **kwargs)
        self.action_type = action_type
        self.coordinates = coordinates
        
        # Add computer use details
        self.details.update({
            "action_type": action_type,
            "coordinates": coordinates,
        })


class FileOperationError(BytebotException):
    """Raised when file operations fail."""
    
    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs,
    ):
        """Initialize file operation error.
        
        Args:
            message: Error message
            file_path: File path that caused the error
            operation: File operation that failed (read, write, delete, etc.)
            **kwargs: Additional arguments for base exception
        """
        super().__init__(message, **kwargs)
        self.file_path = file_path
        self.operation = operation
        
        # Add file operation details
        self.details.update({
            "file_path": file_path,
            "operation": operation,
        })


class ConfigurationError(BytebotException):
    """Raised when configuration is invalid or missing."""
    pass


class RateLimitError(ExternalServiceError):
    """Raised when rate limits are exceeded."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs,
    ):
        """Initialize rate limit error.
        
        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            **kwargs: Additional arguments for external service error
        """
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        
        # Add rate limit details
        self.details.update({
            "retry_after": retry_after,
        })


class TimeoutError(BytebotException):
    """Raised when operations timeout."""
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        **kwargs,
    ):
        """Initialize timeout error.
        
        Args:
            message: Error message
            timeout_seconds: Timeout duration in seconds
            **kwargs: Additional arguments for base exception
        """
        super().__init__(message, **kwargs)
        self.timeout_seconds = timeout_seconds
        
        # Add timeout details
        self.details.update({
            "timeout_seconds": timeout_seconds,
        })


class WebSocketError(BytebotException):
    """Raised when WebSocket operations fail."""
    pass


class SerializationError(BytebotException):
    """Raised when serialization/deserialization fails."""
    pass


# Exception mapping for HTTP status codes
HTTP_EXCEPTION_MAP = {
    400: ValidationError,
    401: AuthenticationError,
    403: AuthorizationError,
    404: NotFoundError,
    409: ConflictError,
    429: RateLimitError,
    500: BytebotException,
}


def get_exception_for_status_code(status_code: int) -> type[BytebotException]:
    """Get appropriate exception class for HTTP status code.
    
    Args:
        status_code: HTTP status code
    
    Returns:
        Exception class
    """
    return HTTP_EXCEPTION_MAP.get(status_code, BytebotException)


class BytebotNotFoundException(NotFoundError):
    """Raised when a requested resource is not found.
    
    This is an alias for NotFoundError for backward compatibility.
    """
    pass


class BytebotValidationException(ValidationError):
    """Raised when input validation fails.
    
    This is an alias for ValidationError for backward compatibility.
    """
    pass


class BytebotConflictException(ConflictError):
    """Raised when a resource conflict occurs.
    
    This is an alias for ConflictError for backward compatibility.
    """
    pass