# ByteBot Python Implementation

A Python 3.12 implementation of ByteBot - an AI-powered desktop automation and conversation platform.

## Overview

ByteBot provides intelligent desktop automation capabilities through AI-powered agents that can:

- **Desktop Control**: Take screenshots, perform clicks, keyboard input, and other desktop interactions
- **AI Conversations**: Engage in natural language conversations using multiple AI providers (Claude, OpenAI, Gemini)
- **Task Management**: Create, track, and manage automation tasks
- **WebSocket Communication**: Real-time bidirectional communication for interactive sessions
- **Web UI**: Modern web interface for managing conversations and tasks

## Architecture

### Core Components

- **FastAPI Backend**: High-performance async web framework
- **SQLAlchemy ORM**: Database abstraction and migrations
- **PostgreSQL**: Primary database for persistent storage
- **Pydantic**: Data validation and serialization
- **WebSockets**: Real-time communication
- **Docker**: Containerized deployment

### Services

- **Agent Service**: Core AI and task processing logic
- **Desktop Service**: Linux desktop automation (X11, VNC)
- **AI Service**: Multi-provider AI client (Claude, OpenAI, Gemini)
- **WebSocket Service**: Real-time communication handling
- **UI Service**: Static file serving and web interface

### Project Structure

```
bytebot/
├── bytebot/
│   ├── __init__.py
│   ├── core/                 # Core application logic
│   │   ├── __init__.py
│   │   ├── config.py         # Configuration management
│   │   ├── database.py       # Database connection
│   │   ├── logging.py        # Logging configuration
│   │   └── security.py       # Security utilities
│   ├── models/               # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── base.py           # Base model class
│   │   ├── task.py           # Task model
│   │   ├── message.py        # Message model
│   │   └── summary.py        # Summary model
│   ├── schemas/              # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── task.py           # Task schemas
│   │   ├── message.py        # Message schemas
│   │   └── computer_action.py # Computer action schemas
│   ├── services/             # Business logic services
│   │   ├── __init__.py
│   │   ├── agent.py          # AI agent service
│   │   ├── computer_use.py   # Computer automation service
│   │   ├── llm/              # LLM provider services
│   │   │   ├── __init__.py
│   │   │   ├── anthropic.py
│   │   │   ├── openai.py
│   │   │   └── google.py
│   │   └── task.py           # Task management service
│   ├── api/                  # FastAPI routers
│   │   ├── __init__.py
│   │   ├── deps.py           # Dependencies
│   │   ├── tasks.py          # Task endpoints
│   │   ├── messages.py       # Message endpoints
│   │   ├── computer_use.py   # Computer use endpoints
│   │   └── websocket.py      # WebSocket endpoints
│   ├── desktop/              # Desktop automation (bytebotd equivalent)
│   │   ├── __init__.py
│   │   ├── automation.py     # Desktop automation logic
│   │   ├── screenshot.py     # Screenshot functionality
│   │   ├── input_tracking.py # Input tracking
│   │   └── vnc_proxy.py      # VNC proxy functionality
│   └── utils/                # Utility functions
│       ├── __init__.py
│       ├── message_content.py # Message content utilities
│       └── computer_action.py # Computer action utilities
├── migrations/               # Alembic database migrations
├── tests/                    # Test files
├── scripts/                  # Utility scripts
├── docker/                   # Docker configurations
├── .env.example              # Environment variables example
├── alembic.ini               # Alembic configuration
├── pyproject.toml            # Project configuration
└── README.md                 # This file
```

## Services

### 1. Bytebot Agent Service
- **Port**: 9991
- **Purpose**: Main AI agent service
- **Features**: Task management, AI conversation, WebSocket communication

### 2. Bytebot Desktop Service
- **Port**: 9990
- **Purpose**: Desktop automation and VNC proxy
- **Features**: Computer control, screenshot capture, input tracking

### 3. Bytebot UI Backend
- **Port**: 9992
- **Purpose**: API proxy and static file serving
- **Features**: Proxy to agent service, WebSocket forwarding

## Installation

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Redis 6+

### Setup

1. **Clone and navigate to Python directory**:
   ```bash
   cd python
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e .
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Start services**:
   ```bash
   # Terminal 1: Agent service
   python -m bytebot.main agent
   
   # Terminal 2: Desktop service
   python -m bytebot.main desktop
   
   # Terminal 3: UI backend
   python -m bytebot.main ui
   ```

## Development

### Code Quality

```bash
# Format code
black bytebot/
isort bytebot/

# Lint code
flake8 bytebot/
mypy bytebot/

# Run tests
pytest

# Run tests with coverage
pytest --cov=bytebot
```

### Pre-commit Hooks

```bash
pre-commit install
```

## Migration from Node.js Version

This Python implementation maintains API compatibility with the original Node.js version while providing:

- **Better Performance**: Python 3.12 performance improvements
- **Type Safety**: Full type hints with mypy checking
- **Modern Async**: Native async/await support
- **Simplified Deployment**: Single language stack
- **Better Desktop Integration**: Native Python desktop automation libraries

## Docker Support

Docker configurations are provided for all services with Python 3.12 base images.

## Contributing

Please follow the existing code style and ensure all tests pass before submitting PRs.