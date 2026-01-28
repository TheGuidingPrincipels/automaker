#!/bin/bash
# Knowledge Library Startup Script for Automaker Integration
# This script provides lenient startup that warns but continues on missing optional dependencies

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
KL_PORT="${API_PORT:-8002}"
KL_HOST="${API_HOST:-0.0.0.0}"
HEALTH_URL="http://localhost:${KL_PORT}/health"

# Automaker integration: Set DATA_DIR to automaker's data directory
# This allows the SDK to find credentials.json stored by automaker
if [ -z "$DATA_DIR" ]; then
    # Default to automaker's data directory (parent of 2.ai-library)
    AUTOMAKER_ROOT="$(dirname "$SCRIPT_DIR")"
    export DATA_DIR="${AUTOMAKER_ROOT}/data"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
FOREGROUND=false
QUIET=false
for arg in "$@"; do
    case "$arg" in
        --foreground|-f) FOREGROUND=true ;;
        --quiet|-q) QUIET=true ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --foreground, -f  Run in foreground (for Terminal windows)"
            echo "  --quiet, -q       Suppress non-error output"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  API_PORT          Server port (default: 8002)"
            echo "  API_HOST          Server host (default: 0.0.0.0)"
            echo "  CORS_ORIGINS      Comma-separated CORS origins"
            echo "  MISTRAL_API_KEY   Required for embeddings"
            exit 0
            ;;
    esac
done

log() {
    if [ "$QUIET" = false ]; then
        echo -e "$1"
    fi
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_info() {
    log "${BLUE}[INFO]${NC} $1"
}

log_success() {
    log "${GREEN}[OK]${NC} $1"
}

# Check if Knowledge Library is already running
check_already_running() {
    if curl -s --max-time 2 "$HEALTH_URL" > /dev/null 2>&1; then
        log_success "Knowledge Library is already running on port $KL_PORT"
        return 0
    fi
    return 1
}

# Clean up orphaned Knowledge Library processes
cleanup_orphaned_kl() {
    # Find orphaned run_api.py processes on our port
    local orphan_pids=$(lsof -t -i ":$KL_PORT" 2>/dev/null | head -5)

    if [ -n "$orphan_pids" ]; then
        for pid in $orphan_pids; do
            # Check if it's a run_api.py process
            if ps -p "$pid" -o args= 2>/dev/null | grep -q "run_api.py"; then
                log_warn "Found orphaned Knowledge Library process (PID: $pid), cleaning up..."
                kill "$pid" 2>/dev/null || true
                sleep 0.5
                # Force kill if still running
                if kill -0 "$pid" 2>/dev/null; then
                    kill -9 "$pid" 2>/dev/null || true
                fi
                log_success "Cleaned up orphaned process"
            fi
        done
    fi

    # Also clean up stale PID file
    if [ -f ".kl.pid" ]; then
        local stored_pid=$(cat ".kl.pid" 2>/dev/null)
        if [ -n "$stored_pid" ] && ! kill -0 "$stored_pid" 2>/dev/null; then
            log_info "Removing stale PID file"
            rm -f ".kl.pid"
        fi
    fi
}

# Check if port is in use by something else (only LISTEN state, not CLOSED)
check_port_in_use() {
    # Check for actual LISTEN connections, not CLOSED ones
    if lsof -i ":$KL_PORT" -sTCP:LISTEN > /dev/null 2>&1; then
        local pid=$(lsof -t -i ":$KL_PORT" -sTCP:LISTEN 2>/dev/null | head -1)
        log_error "Port $KL_PORT is in use by PID $pid"
        log_error "Either stop that process or set API_PORT to a different port"
        return 1
    fi
    return 0
}

# Check optional dependencies and warn (but don't fail)
check_optional_deps() {
    local has_warnings=false

    # Check for MISTRAL_API_KEY
    if [ -z "$MISTRAL_API_KEY" ]; then
        log_warn "MISTRAL_API_KEY not set - embeddings/vector search will be disabled"
        has_warnings=true
    fi

    # Check for Qdrant (optional - only warn if vector features are needed)
    if ! curl -s --max-time 2 "http://localhost:6333/health" > /dev/null 2>&1; then
        log_warn "Qdrant not running on port 6333 - vector search will be disabled"
        has_warnings=true
    fi

    # Check OAuth token availability
    # Priority: ANTHROPIC_AUTH_TOKEN > CLAUDE_CODE_OAUTH_TOKEN > credentials.json
    if [ -n "$ANTHROPIC_AUTH_TOKEN" ]; then
        log_success "OAuth token found (ANTHROPIC_AUTH_TOKEN)"
    elif [ -n "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
        log_success "OAuth token found (CLAUDE_CODE_OAUTH_TOKEN) - CLI will handle auth internally"
    else
        log_info "No OAuth token in environment - will try to load from:"
        log_info "  1. ${DATA_DIR}/credentials.json (automaker credentials)"
        log_info "  2. ~/.automaker/credentials.json (legacy fallback)"
        log_info "If AI features fail, set CLAUDE_CODE_OAUTH_TOKEN or run 'claude login'"
    fi

    # Ensure API key auth is NOT used (OAuth only mode)
    # This prevents ANTHROPIC_API_KEY from interfering with OAuth flow
    unset ANTHROPIC_API_KEY

    if [ "$has_warnings" = true ]; then
        log_info "Knowledge Library will start with limited functionality"
    fi

    return 0  # Always succeed - these are optional
}

# Setup Python virtual environment
setup_venv() {
    if [ ! -d ".venv" ]; then
        log_info "Creating Python virtual environment..."
        # Prefer uv if available, fall back to standard venv
        if command -v uv &> /dev/null; then
            uv venv .venv
        else
            python3 -m venv .venv
        fi
        log_success "Virtual environment created"
    fi

    # Activate venv
    source .venv/bin/activate

    # Check if dependencies are installed
    if ! python -c "import fastapi" 2>/dev/null; then
        log_info "Installing Python dependencies..."
        # Use uv pip if available (for uv-created venvs), fall back to pip
        if command -v uv &> /dev/null; then
            uv pip install -q -r requirements.txt
        elif command -v pip &> /dev/null; then
            pip install -q -r requirements.txt
        else
            log_error "Neither uv nor pip found. Cannot install dependencies."
            return 1
        fi
        log_success "Dependencies installed"
    fi
}

# Start the server
start_server() {
    log_info "Starting Knowledge Library on port $KL_PORT..."

    if [ "$FOREGROUND" = true ]; then
        # Foreground mode - for Terminal windows
        log_info "Running in foreground mode (Ctrl+C to stop)"
        echo ""
        python run_api.py --port "$KL_PORT" --host "$KL_HOST"
    else
        # Background mode - for automated startup
        python run_api.py --port "$KL_PORT" --host "$KL_HOST" &
        local pid=$!

        # Wait for server to be ready (max 30 seconds)
        log_info "Waiting for server to be ready..."
        local max_attempts=30
        local attempt=0
        while [ $attempt -lt $max_attempts ]; do
            # Check if process is still alive (early crash detection)
            if ! kill -0 "$pid" 2>/dev/null; then
                log_error "Server process died unexpectedly"
                return 1
            fi
            if curl -s --max-time 2 "$HEALTH_URL" > /dev/null 2>&1; then
                log_success "Knowledge Library started successfully (PID: $pid)"
                echo "$pid" > ".kl.pid"
                return 0
            fi
            sleep 1
            attempt=$((attempt + 1))
        done

        log_error "Server failed to start within 30 seconds"
        kill $pid 2>/dev/null || true
        return 1
    fi
}

# Main execution
main() {
    log ""
    log "${BLUE}========================================${NC}"
    log "${BLUE}  Knowledge Library for Automaker${NC}"
    log "${BLUE}========================================${NC}"
    log ""

    # Clean up stale PID files FIRST (before checking if already running)
    if [ -f ".kl.pid" ]; then
        local stored_pid=$(cat ".kl.pid" 2>/dev/null)
        if [ -n "$stored_pid" ] && ! kill -0 "$stored_pid" 2>/dev/null; then
            log_info "Removing stale PID file (process $stored_pid not running)"
            rm -f ".kl.pid"
        fi
    fi

    # Check if already running
    if check_already_running; then
        return 0
    fi

    # Clean up any orphaned processes
    cleanup_orphaned_kl

    # Check port availability
    if ! check_port_in_use; then
        return 1
    fi

    # Check optional dependencies (warn but continue)
    check_optional_deps

    # Setup venv
    setup_venv

    # Start server
    start_server
}

main
