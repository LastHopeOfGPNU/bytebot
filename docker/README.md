# ByteBot Docker Deployment

This directory contains Docker configurations for deploying ByteBot services using Python 3.12.

## Files Overview

- `python.Dockerfile` - Main Dockerfile for ByteBot Python services
- `python-desktop.Dockerfile` - Dockerfile for desktop control service with GUI support
- `docker-compose.python.yml` - Production deployment configuration
- `docker-compose.dev.yml` - Development environment configuration
- `supervisord-desktop.conf` - Supervisor configuration for desktop services
- `start-desktop.sh` - Desktop service startup script
- `.env.example` - Environment variables template

## Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your API keys and configuration
vim .env
```

### 2. Production Deployment

```bash
# Start all services
docker-compose -f docker-compose.python.yml up -d

# View logs
docker-compose -f docker-compose.python.yml logs -f

# Stop services
docker-compose -f docker-compose.python.yml down
```

### 3. Development Environment

```bash
# Start development environment with hot reload
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop development environment
docker-compose -f docker-compose.dev.yml down
```

## Services

### ByteBot Agent (Port 8000)
- FastAPI-based AI agent service
- Handles task execution and AI interactions
- REST API and WebSocket support

### ByteBot Desktop (Port 9990)
- Desktop automation service
- VNC access on port 5900
- Web-based VNC (noVNC) on port 6080
- Desktop control API on port 9990

### ByteBot UI (Port 3000)
- Web interface backend
- Proxies requests to agent and desktop services
- Serves static files and handles WebSocket connections

### PostgreSQL (Port 5432)
- Database service
- Persistent data storage

## Environment Variables

### Required
- `ANTHROPIC_API_KEY` - Anthropic Claude API key
- `OPENAI_API_KEY` - OpenAI API key
- `GEMINI_API_KEY` - Google Gemini API key

### Optional
- `DATABASE_URL` - PostgreSQL connection string
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `BYTEBOT_UI_STATIC_DIR` - Static files directory for UI

## Accessing Services

- **Agent API**: http://localhost:8000
- **Desktop API**: http://localhost:9990
- **Desktop VNC (Web)**: http://localhost:6080
- **UI Server**: http://localhost:3000
- **PostgreSQL**: localhost:5432

## Development

### Building Images

```bash
# Build all images
docker-compose -f docker-compose.python.yml build

# Build specific service
docker-compose -f docker-compose.python.yml build bytebot-agent
```

### Debugging

```bash
# Access container shell
docker exec -it bytebot-agent-python bash

# View service logs
docker logs bytebot-agent-python

# Check service status
docker-compose -f docker-compose.python.yml ps
```

### Database Management

```bash
# Run database migrations
docker exec bytebot-agent-python alembic upgrade head

# Access PostgreSQL
docker exec -it bytebot-postgres psql -U postgres -d bytebotdb
```

## Troubleshooting

### Common Issues

1. **Desktop service not starting**
   - Check if privileged mode is enabled
   - Verify X11 socket mounting
   - Check supervisor logs: `docker logs bytebot-desktop-python`

2. **Database connection issues**
   - Ensure PostgreSQL is healthy: `docker-compose ps`
   - Check DATABASE_URL environment variable
   - Verify network connectivity between services

3. **API key errors**
   - Verify API keys are set in .env file
   - Check if .env file is loaded: `docker-compose config`

### Logs

```bash
# View all service logs
docker-compose -f docker-compose.python.yml logs

# Follow specific service logs
docker-compose -f docker-compose.python.yml logs -f bytebot-agent

# View desktop service supervisor logs
docker exec bytebot-desktop-python tail -f /var/log/supervisor/supervisord.log
```

## Production Considerations

1. **Security**
   - Use strong passwords for PostgreSQL
   - Configure CORS origins appropriately
   - Use HTTPS in production
   - Secure API keys and secrets

2. **Performance**
   - Adjust container resource limits
   - Configure PostgreSQL for production workloads
   - Use external database for high availability

3. **Monitoring**
   - Set up health checks
   - Configure log aggregation
   - Monitor resource usage

4. **Backup**
   - Regular database backups
   - Backup configuration files
   - Document recovery procedures