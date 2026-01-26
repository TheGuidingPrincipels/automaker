#!/bin/bash
# Start Redis for MCP Knowledge Server confidence scoring

set -e

echo "=========================================="
echo "Starting Redis for Confidence Scoring"
echo "=========================================="
echo ""

# Check if Redis is already running
if redis-cli ping 2>/dev/null | grep -q PONG; then
    echo "✅ Redis is already running"
    redis-cli info server | grep -E "redis_version|tcp_port|uptime_in_seconds"
    exit 0
fi

# Check if redis-server is installed
if ! command -v redis-server &> /dev/null; then
    echo "❌ redis-server not found"
    echo ""
    echo "Install Redis:"
    echo "  Ubuntu/Debian: sudo apt-get install redis-server"
    echo "  macOS:         brew install redis"
    echo "  RHEL/CentOS:   sudo yum install redis"
    exit 1
fi

# Start Redis
echo "Starting Redis server..."
redis-server --daemonize yes --port 6379 --bind 127.0.0.1

# Wait for Redis to start
sleep 2

# Verify Redis is running
if redis-cli ping 2>/dev/null | grep -q PONG; then
    echo ""
    echo "✅ Redis started successfully"
    echo ""
    redis-cli info server | grep -E "redis_version|tcp_port|uptime_in_seconds"
    echo ""
    echo "=========================================="
    echo "Next steps:"
    echo "1. Start MCP server: python mcp_server.py"
    echo "2. Verify scoring: python scripts/verify_confidence_scoring.py"
    echo "3. Backfill scores: python scripts/backfill_confidence_scores.py"
    echo "=========================================="
else
    echo "❌ Redis failed to start"
    echo "Check logs: redis-server --logfile /tmp/redis.log"
    exit 1
fi
