#!/bin/sh
set -e

echo "Waiting for Qdrant..."
until curl -sf "http://${QDRANT_HOST:-localhost}:${QDRANT_PORT:-6333}/healthz" > /dev/null 2>&1; do
  sleep 2
done
echo "Qdrant is ready."

echo "Seeding vector store..."
python scripts/seed.py || echo "Seed skipped (may already exist)"

echo "Starting Aegis API..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
