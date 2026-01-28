#!/bin/bash
# start-api.sh - Start AI-Library API server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env if exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check for required environment variables
if [ -z "$MISTRAL_API_KEY" ]; then
    echo "ERROR: MISTRAL_API_KEY environment variable is not set"
    echo "Please set it in .env or export it directly"
    exit 1
fi

# Check OAuth token availability (info only - may load from credentials.json at runtime)
if [ -z "$ANTHROPIC_AUTH_TOKEN" ]; then
    echo "INFO: ANTHROPIC_AUTH_TOKEN not set in environment"
    echo "      Will attempt to load from ~/.automaker/credentials.json at runtime"
    echo "      If AI features fail, set ANTHROPIC_AUTH_TOKEN or run 'claude login'"
fi

# Ensure API key auth is NOT used (OAuth only mode)
unset ANTHROPIC_API_KEY
echo "INFO: API key authentication disabled (OAuth only mode)"

# Check if Qdrant is running
if ! curl -s http://localhost:6333/health > /dev/null 2>&1; then
    echo "WARNING: Qdrant is not running on localhost:6333"
    echo "Start it with: docker start qdrant"
    echo "Or first time: docker run -d --name qdrant -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant:latest"
    exit 1
fi

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e ".[dev]"
fi

# Start API on port 8002 (8001 reserved for deepread-backend)
echo "Starting AI-Library API on http://localhost:8002"
echo "  - Swagger UI: http://localhost:8002/docs"
echo "  - ReDoc: http://localhost:8002/redoc"
echo "  - Health: http://localhost:8002/health"
python run_api.py --port 8002
