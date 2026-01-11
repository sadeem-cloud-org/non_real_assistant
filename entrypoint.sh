#!/bin/bash
# Entrypoint script for Docker container
# Runs as root to fix permissions, then drops to appuser

set -e

echo "=== Non Real Assistant Startup ==="

# Fix ownership of data directory (runs as root)
echo "Setting up data directory permissions..."
mkdir -p /app/data
chown -R appuser:appuser /app/data
chmod 755 /app/data

# Run migrations as appuser
echo "Running database migrations..."
gosu appuser python -m migrations.migrate

# Fix database permissions after migration
if [ -f /app/data/database.db ]; then
    chown appuser:appuser /app/data/database.db
    chmod 644 /app/data/database.db
    echo "Database permissions set"
fi

# Start the application as appuser
echo "Starting application..."
exec gosu appuser "$@"
