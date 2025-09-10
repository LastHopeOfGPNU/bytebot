# Python ByteBot Services Dockerfile
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy Python project files
COPY python/pyproject.toml python/README.md ./
COPY python/alembic.ini ./
COPY python/alembic/ ./alembic/
COPY python/bytebot/ ./bytebot/

# Install Python dependencies
RUN pip install -e .

# Create non-root user
RUN useradd --create-home --shell /bin/bash bytebot
USER bytebot

# Expose ports
EXPOSE 8000 3000

# Default command (can be overridden)
CMD ["bytebot-agent"]