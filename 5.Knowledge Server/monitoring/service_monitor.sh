#!/bin/bash
#
# MCP Knowledge Server - Service Monitor
#
# Monitors the MCP server process and can automatically restart it
# Checks Neo4j dependency and logs monitoring events
#
# Usage:
#   ./service_monitor.sh [--auto-restart] [--cooldown 300]
#
# Options:
#   --auto-restart: Automatically restart server if it's down
#   --cooldown N: Minimum seconds between restart attempts (default: 300)
#
# Designed to run via cron for continuous monitoring

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
AUTO_RESTART=false
COOLDOWN_SECONDS=300
LOG_FILE="/var/log/mcp-service-monitor.log"

# If not writable, use project directory
if [ ! -w "$(dirname "$LOG_FILE")" ]; then
    LOG_FILE="$PROJECT_DIR/monitoring/service_monitor.log"
fi

STATE_FILE="$PROJECT_DIR/monitoring/.service_monitor_state"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --auto-restart)
            AUTO_RESTART=true
            shift
            ;;
        --cooldown)
            COOLDOWN_SECONDS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Check if MCP server is running
check_server_running() {
    if pgrep -f "mcp_server.py" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Check if Neo4j is running
check_neo4j_running() {
    if docker ps | grep -q neo4j; then
        return 0
    else
        return 1
    fi
}

# Check port availability
check_port() {
    local port=$1
    if command -v nc &> /dev/null; then
        if nc -z localhost "$port" 2>/dev/null; then
            return 0
        fi
    elif command -v lsof &> /dev/null; then
        if lsof -i:"$port" -t > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Get last restart time from state file
get_last_restart_time() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
    else
        echo "0"
    fi
}

# Set last restart time
set_last_restart_time() {
    echo "$(date +%s)" > "$STATE_FILE"
}

# Start MCP server
start_server() {
    log "Attempting to start MCP server..."

    # Check if we're in cooldown period
    LAST_RESTART=$(get_last_restart_time)
    CURRENT_TIME=$(date +%s)
    TIME_SINCE_RESTART=$((CURRENT_TIME - LAST_RESTART))

    if [ "$TIME_SINCE_RESTART" -lt "$COOLDOWN_SECONDS" ]; then
        REMAINING=$((COOLDOWN_SECONDS - TIME_SINCE_RESTART))
        log "COOLDOWN: Last restart was ${TIME_SINCE_RESTART}s ago. Must wait ${REMAINING}s more."
        return 1
    fi

    # Check prerequisites
    if ! check_neo4j_running; then
        log "ERROR: Cannot start server - Neo4j is not running"
        return 1
    fi

    # Change to project directory
    cd "$PROJECT_DIR"

    # Check if virtual environment exists
    if [ ! -d ".venv" ]; then
        log "ERROR: Virtual environment not found at .venv"
        return 1
    fi

    # Start server in background
    source .venv/bin/activate

    nohup python mcp_server.py > /dev/null 2>&1 &
    SERVER_PID=$!

    # Wait a moment and verify it started
    sleep 3

    if kill -0 "$SERVER_PID" 2>/dev/null; then
        log "SUCCESS: MCP server started (PID: $SERVER_PID)"
        set_last_restart_time
        return 0
    else
        log "ERROR: MCP server failed to start"
        return 1
    fi
}

# Main monitoring logic
run_monitoring_check() {
    log "========== Service Monitor Check =========="

    # 1. Check MCP server status
    if check_server_running; then
        SERVER_PID=$(pgrep -f "mcp_server.py")
        log "✅ MCP server is running (PID: $SERVER_PID)"

        # Get process details
        if command -v ps &> /dev/null; then
            CPU_MEM=$(ps -p "$SERVER_PID" -o %cpu,%mem --no-headers 2>/dev/null || echo "N/A N/A")
            log "   CPU/Memory: $CPU_MEM"
        fi
    else
        log "❌ MCP server is NOT running"

        if [ "$AUTO_RESTART" = true ]; then
            log "AUTO-RESTART enabled, attempting to start server..."
            if start_server; then
                log "Server restart successful"
            else
                log "Server restart failed"
                return 1
            fi
        else
            log "AUTO-RESTART disabled, manual intervention required"
            return 1
        fi
    fi

    # 2. Check Neo4j status
    if check_neo4j_running; then
        log "✅ Neo4j is running"
    else
        log "⚠️  Neo4j is NOT running - server may fail"
    fi

    # 3. Check Neo4j port
    if check_port 7687; then
        log "✅ Neo4j port 7687 is accessible"
    else
        log "⚠️  Neo4j port 7687 is NOT accessible"
    fi

    # 4. Check data directories
    if [ -d "$PROJECT_DIR/data" ]; then
        DISK_USAGE=$(du -sh "$PROJECT_DIR/data" | cut -f1)
        log "📊 Data directory size: $DISK_USAGE"
    else
        log "⚠️  Data directory not found"
    fi

    # 5. Check log file size (rotate if too large)
    if [ -f "$LOG_FILE" ]; then
        LOG_SIZE=$(du -k "$LOG_FILE" | cut -f1)
        if [ "$LOG_SIZE" -gt 10240 ]; then  # > 10MB
            log "Log file exceeds 10MB, rotating..."
            mv "$LOG_FILE" "$LOG_FILE.old"
            log "Log file rotated"
        fi
    fi

    log "========== Check Complete =========="
    return 0
}

# Main execution
echo -e "${BLUE}MCP Service Monitor${NC}"
echo "Log file: $LOG_FILE"
echo "Auto-restart: $AUTO_RESTART"
echo ""

# Run the check
if run_monitoring_check; then
    echo -e "${GREEN}✅ Monitoring check passed${NC}"
    exit 0
else
    echo -e "${RED}❌ Monitoring check failed${NC}"
    exit 1
fi
