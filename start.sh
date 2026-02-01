#!/bin/bash
# Startup script for MapAhead on Fly.io

# Use PORT environment variable or default to 8000
PORT=${PORT:-8000}

# Set PYTHONPATH to current directory (works for both local and Docker)
# In Docker, this will be /app (set by Dockerfile)
# Locally, this will be the project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start uvicorn
exec uvicorn Backend.main:app --host 0.0.0.0 --port $PORT

