#!/bin/sh
set -e

export PYTHONPATH=/app

# Only run migrations for the main backend (uvicorn), not celery workers/beat
if echo "$@" | grep -q "uvicorn"; then
  echo "Running database migrations..."
  alembic upgrade head
fi

echo "Starting application..."
exec "$@"
