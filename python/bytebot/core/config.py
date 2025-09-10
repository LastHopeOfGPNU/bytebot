"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Any, Dict, List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://bytebot:password@localhost:5432/bytebot",
        description="Database connection URL",
    )
    
    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for Celery",
    )

    # AI Provider API Keys
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")

    # Service Configuration
    agent_host: str = Field(default="0.0.0.0", description="Agent service host")
    agent_port: int = Field(default=9991, description="Agent service port")
    desktop_host: str = Field(default="0.0.0.0", description="Desktop service host")
    desktop_port: int = Field(default=9990, description="Desktop service port")
    ui_host: str = Field(default="0.0.0.0", description="UI service host")
    ui_port: int = Field(default=9992, description="UI service port")

    # External Service URLs
    bytebot_agent_base_url: str = Field(
        default="http://localhost:9991",
        description="Base URL for agent service",
    )
    bytebot_desktop_base_url: str = Field(
        default="http://localhost:9990",
        description="Base URL for desktop service",
    )
    bytebot_desktop_vnc_url: str = Field(
        default="http://localhost:6080",
        description="VNC URL for desktop access",
    )

    # Security
    secret_key: str = Field(
        default="your-secret-key-here",
        description="Secret key for JWT tokens",
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Logging format (json or text)")

    # Development
    debug: bool = Field(default=False, description="Enable debug mode")
    reload: bool = Field(default=False, description="Enable auto-reload")

    # VNC Configuration
    vnc_host: str = Field(default="localhost", description="VNC host")
    vnc_port: int = Field(default=6080, description="VNC port")
    display: str = Field(default=":1", description="X11 display")
    vnc_password: str = Field(default="bytebot", description="VNC password")

    # Task Configuration
    max_concurrent_tasks: int = Field(
        default=5,
        description="Maximum number of concurrent tasks",
    )
    task_timeout_seconds: int = Field(
        default=3600,
        description="Task timeout in seconds",
    )

    # File Upload
    max_file_size_mb: int = Field(
        default=50,
        description="Maximum file size for uploads in MB",
    )
    upload_dir: str = Field(
        default="/tmp/bytebot/uploads",
        description="Directory for file uploads",
    )

    # Computer Use Settings
    screenshot_quality: int = Field(
        default=85,
        description="Screenshot JPEG quality (1-100)",
    )
    mouse_move_duration: float = Field(
        default=0.1,
        description="Duration for mouse movements in seconds",
    )
    keyboard_type_delay: float = Field(
        default=0.05,
        description="Delay between keystrokes in seconds",
    )

    # CORS Settings
    cors_origins: List[str] = Field(
        default=["*"],
        description="Allowed CORS origins",
    )
    cors_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        description="Allowed CORS methods",
    )

    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()

    @validator("log_format")
    def validate_log_format(cls, v: str) -> str:
        """Validate log format."""
        valid_formats = ["json", "text"]
        if v.lower() not in valid_formats:
            raise ValueError(f"Invalid log format. Must be one of: {valid_formats}")
        return v.lower()

    @validator("screenshot_quality")
    def validate_screenshot_quality(cls, v: int) -> int:
        """Validate screenshot quality."""
        if not 1 <= v <= 100:
            raise ValueError("Screenshot quality must be between 1 and 100")
        return v

    def get_available_llm_providers(self) -> List[str]:
        """Get list of available LLM providers based on API keys."""
        providers = []
        if self.anthropic_api_key:
            providers.append("anthropic")
        if self.openai_api_key:
            providers.append("openai")
        if self.gemini_api_key:
            providers.append("google")
        return providers

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic."""
        return self.database_url.replace("+asyncpg", "")

    @property
    def max_file_size_bytes(self) -> int:
        """Get maximum file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()