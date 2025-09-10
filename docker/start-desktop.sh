#!/bin/bash

# Start desktop environment script for ByteBot Desktop Service

set -e

echo "Starting ByteBot Desktop Service..."

# Create log directory
mkdir -p /var/log/supervisor

# Set up display
export DISPLAY=:0

# Wait for X server to be ready
echo "Waiting for X server to start..."
while ! xdpyinfo >/dev/null 2>&1; do
    sleep 1
done
echo "X server is ready"

# Start supervisor with all services
echo "Starting supervisor..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf -n