#!/bin/bash
# Entrypoint script for Docker container
# Runs migrations and seeds before starting the app

set -e

echo "=== Non Real Assistant Startup ==="

# Run migrations
echo "Running database migrations..."
python -m migrations.migrate

# Start the application
echo "Starting application..."
exec "$@"
