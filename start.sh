#!/bin/bash
# Startup script for POI Ahead

# Use PORT environment variable or default to 8000
PORT=${PORT:-8000}

# Set PYTHONPATH to current directory (works for both local and Docker)
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Check for --reload flag (for development)
RELOAD=""
if [[ "$1" == "--reload" ]]; then
    RELOAD="--reload"
fi

# Start uvicorn
exec uvicorn Backend.main:app --host 0.0.0.0 --port $PORT $RELOAD

