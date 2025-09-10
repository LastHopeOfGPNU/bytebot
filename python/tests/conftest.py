"""Pytest configuration and fixtures for ByteBot tests."""

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from bytebot.core.config import Settings, get_settings
from bytebot.core.database import Base, get_db
from bytebot.main import create_app

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_DATABASE_URL_SYNC = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        database_url=TEST_DATABASE_URL,
        environment="testing",
        log_level="DEBUG",
        # AI API keys for testing (use mock keys)
        anthropic_api_key="test-anthropic-key",
        openai_api_key="test-openai-key",
        gemini_api_key="test-gemini-key",
    )


@pytest.fixture(scope="session")
async def async_engine():
    """Create async database engine for testing."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for testing."""
    async_session_maker = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sync_engine():
    """Create sync database engine for testing."""
    engine = create_engine(
        TEST_DATABASE_URL_SYNC,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Clean up
    engine.dispose()


@pytest.fixture
def sync_session(sync_engine):
    """Create sync database session for testing."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
    session = SessionLocal()
    
    yield session
    
    session.rollback()
    session.close()


@pytest.fixture
def app(test_settings, async_session):
    """Create FastAPI app for testing."""
    # Override settings
    def get_test_settings():
        return test_settings
    
    # Override database dependency
    async def get_test_db():
        yield async_session
    
    app = create_app()
    app.dependency_overrides[get_settings] = get_test_settings
    app.dependency_overrides[get_db] = get_test_db
    
    return app


@pytest.fixture
def client(app) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_ai_responses():
    """Mock AI API responses for testing."""
    return {
        "claude": {
            "content": [{"type": "text", "text": "Test response from Claude"}],
            "model": "claude-3-sonnet-20240229",
            "role": "assistant",
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 5},
        },
        "openai": {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Test response from OpenAI",
                    },
                    "finish_reason": "stop",
                }
            ],
            "model": "gpt-4",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
        "gemini": {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Test response from Gemini"}],
                        "role": "model",
                    },
                    "finish_reason": "STOP",
                }
            ],
            "usage_metadata": {
                "prompt_token_count": 10,
                "candidates_token_count": 5,
                "total_token_count": 15,
            },
        },
    }


@pytest.fixture
def mock_desktop_response():
    """Mock desktop service response for testing."""
    return {
        "success": True,
        "message": "Action executed successfully",
        "action_id": "test-action-123",
        "timestamp": "2024-01-01T00:00:00Z",
        "screenshot": None,
        "windows": [],
        "files": [],
        "clipboard_content": None,
        "system_info": {},
    }


# Pytest configuration
pytest_plugins = ["pytest_asyncio"]