#!/bin/sh
set -e

export PYTHONPATH=/app

echo "Running database migrations..."
alembic upgrade head

echo "Starting application..."
exec "$@"
