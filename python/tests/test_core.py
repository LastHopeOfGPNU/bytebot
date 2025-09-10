"""Tests for core functionality."""

import pytest
from unittest.mock import Mock, patch

from bytebot.core.config import Settings, get_settings
from bytebot.core.database import get_db
from bytebot.core.logging import get_logger


class TestSettings:
    """Test settings configuration."""
    
    def test_default_settings(self):
        """Test default settings creation."""
        settings = Settings()
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
    
    def test_settings_from_env(self, monkeypatch):
        """Test settings from environment variables."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LOG_LEVEL", "ERROR")
        monkeypatch.setenv("HOST", "127.0.0.1")
        monkeypatch.setenv("PORT", "9000")
        
        settings = Settings()
        assert settings.environment == "production"
        assert settings.log_level == "ERROR"
        assert settings.host == "127.0.0.1"
        assert settings.port == 9000
    
    def test_database_url_validation(self):
        """Test database URL validation."""
        # Valid PostgreSQL URL
        settings = Settings(database_url="postgresql://user:pass@localhost/db")
        assert settings.database_url == "postgresql://user:pass@localhost/db"
        
        # Valid SQLite URL
        settings = Settings(database_url="sqlite:///./test.db")
        assert settings.database_url == "sqlite:///./test.db"
    
    def test_api_keys_validation(self):
        """Test API keys validation."""
        settings = Settings(
            anthropic_api_key="sk-ant-test",
            openai_api_key="sk-test",
            gemini_api_key="test-key",
        )
        assert settings.anthropic_api_key == "sk-ant-test"
        assert settings.openai_api_key == "sk-test"
        assert settings.gemini_api_key == "test-key"


class TestLogging:
    """Test logging configuration."""
    
    def test_get_logger(self):
        """Test logger creation."""
        logger = get_logger("test_module")
        assert logger.name == "test_module"
    
    def test_logger_hierarchy(self):
        """Test logger hierarchy."""
        parent_logger = get_logger("bytebot")
        child_logger = get_logger("bytebot.core")
        
        assert child_logger.parent == parent_logger
    
    @patch("bytebot.core.logging.logging")
    def test_logging_configuration(self, mock_logging):
        """Test logging configuration setup."""
        from bytebot.core.logging import setup_logging
        
        setup_logging("DEBUG")
        mock_logging.basicConfig.assert_called_once()


class TestDatabase:
    """Test database functionality."""
    
    @pytest.mark.asyncio
    async def test_get_db_dependency(self, async_session):
        """Test database dependency injection."""
        # This test verifies that the database dependency works
        # The actual database session is provided by the fixture
        assert async_session is not None
    
    def test_database_models_import(self):
        """Test that database models can be imported."""
        from bytebot.models import (
            User, Task, TaskExecution, AIMessage, AIUsage,
            DesktopAction, DesktopEvent, DesktopScreenshot
        )
        
        # Verify models are properly defined
        assert hasattr(User, '__tablename__')
        assert hasattr(Task, '__tablename__')
        assert hasattr(TaskExecution, '__tablename__')
        assert hasattr(AIMessage, '__tablename__')
        assert hasattr(AIUsage, '__tablename__')
        assert hasattr(DesktopAction, '__tablename__')
        assert hasattr(DesktopEvent, '__tablename__')
        assert hasattr(DesktopScreenshot, '__tablename__')


class TestHealthCheck:
    """Test application health check."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_health_endpoint_async(self, async_client):
        """Test health check endpoint with async client."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"


class TestErrorHandling:
    """Test error handling."""
    
    def test_404_error(self, client):
        """Test 404 error handling."""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
    
    def test_validation_error(self, client):
        """Test validation error handling."""
        # Try to create a task with invalid data
        response = client.post("/api/tasks", json={"invalid": "data"})
        assert response.status_code == 422  # Validation error
    
    @patch("bytebot.core.database.get_db")
    def test_database_error_handling(self, mock_get_db, client):
        """Test database error handling."""
        # Mock database error
        mock_get_db.side_effect = Exception("Database connection failed")
        
        response = client.get("/api/tasks")
        assert response.status_code == 500


class TestCORS:
    """Test CORS configuration."""
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/api/tasks")
        
        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers
    
    def test_preflight_request(self, client):
        """Test CORS preflight request."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        }
        
        response = client.options("/api/tasks", headers=headers)
        assert response.status_code == 200