# Python ByteBot Desktop Service Dockerfile
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DISPLAY=:0

# Install system dependencies for desktop automation
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    # X11 and desktop dependencies
    xvfb \
    x11vnc \
    fluxbox \
    xterm \
    supervisor \
    # Desktop automation tools
    xdotool \
    wmctrl \
    scrot \
    xclip \
    xrandr \
    # noVNC for web-based VNC access
    websockify \
    && rm -rf /var/lib/apt/lists/*

# Install noVNC
RUN git clone https://github.com/novnc/noVNC.git /opt/noVNC \
    && git clone https://github.com/novnc/websockify /opt/noVNC/utils/websockify \
    && ln -s /opt/noVNC/vnc.html /opt/noVNC/index.html

# Create app directory
WORKDIR /app

# Copy Python project files
COPY python/pyproject.toml python/README.md ./
COPY python/alembic.ini ./
COPY python/alembic/ ./alembic/
COPY python/bytebot/ ./bytebot/

# Install Python dependencies
RUN pip install -e .

# Create supervisor configuration
RUN mkdir -p /etc/supervisor/conf.d
COPY docker/supervisord-desktop.conf /etc/supervisor/conf.d/supervisord.conf

# Create VNC password
RUN mkdir -p /root/.vnc && echo "bytebot" | vncpasswd -f > /root/.vnc/passwd && chmod 600 /root/.vnc/passwd

# Create startup script
COPY docker/start-desktop.sh /start-desktop.sh
RUN chmod +x /start-desktop.sh

# Expose ports
EXPOSE 5900 6080 9990

# Start supervisor
CMD ["/start-desktop.sh"]