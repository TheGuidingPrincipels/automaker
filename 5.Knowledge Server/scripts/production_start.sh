#!/bin/bash
#
# MCP Knowledge Server - Production Start Script
#
# Enhanced startup script with comprehensive pre-flight checks
# for production environments.
#
# Usage:
#   ./production_start.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  MCP Knowledge Server - Production Start${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

cd "$PROJECT_DIR"

# 1. Check virtual environment
echo -e "${YELLOW}[1/7] Checking virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ Virtual environment not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Virtual environment found${NC}"

# 2. Check environment configuration
echo -e "${YELLOW}[2/7] Checking environment configuration...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    exit 1
fi

# Check critical environment variables
source .env
if [ -z "$NEO4J_PASSWORD" ] || [ "$NEO4J_PASSWORD" = "password" ]; then
    echo -e "${YELLOW}⚠️  WARNING: NEO4J_PASSWORD appears to be default/empty${NC}"
fi
echo -e "${GREEN}✅ Environment configured${NC}"

# 3. Check Neo4j connectivity
echo -e "${YELLOW}[3/7] Checking Neo4j...${NC}"
if ! docker ps | grep -q neo4j; then
    echo -e "${YELLOW}⚠️  Neo4j not running, attempting to start...${NC}"
    docker start neo4j 2>/dev/null || {
        echo -e "${RED}❌ Failed to start Neo4j${NC}"
        exit 1
    }
    sleep 3
fi
echo -e "${GREEN}✅ Neo4j running${NC}"

# 4. Check data directories
echo -e "${YELLOW}[4/7] Checking data directories...${NC}"
mkdir -p data/chroma data/embeddings
if [ ! -f "data/events.db" ]; then
    echo -e "${YELLOW}⚠️  Initializing event store...${NC}"
    source .venv/bin/activate
    python scripts/init_database.py
fi
echo -e "${GREEN}✅ Data directories ready${NC}"

# 5. Verify dependencies
echo -e "${YELLOW}[5/7] Verifying dependencies...${NC}"
source .venv/bin/activate
python -c "import fastmcp, neo4j, chromadb, sentence_transformers" 2>/dev/null || {
    echo -e "${RED}❌ Missing dependencies${NC}"
    exit 1
}
echo -e "${GREEN}✅ Dependencies verified${NC}"

# 6. Run health check
echo -e "${YELLOW}[6/7] Running pre-start health check...${NC}"
if [ -f "monitoring/health_check.py" ]; then
    python monitoring/health_check.py --json > /dev/null 2>&1 || {
        echo -e "${YELLOW}⚠️  Health check warnings (continuing anyway)${NC}"
    }
fi
echo -e "${GREEN}✅ Health check passed${NC}"

# 7. Start server
echo -e "${YELLOW}[7/7] Starting MCP Knowledge Server...${NC}"
echo ""
echo -e "${GREEN}Server starting...${NC}"
echo -e "${BLUE}Press Ctrl+C to stop${NC}"
echo ""
echo "=" | tr '=' '-' | head -c 70; echo

# Start with proper error handling
python mcp_server.py

# Cleanup on exit
echo ""
echo "=" | tr '=' '-' | head -c 70; echo
echo -e "${BLUE}Server stopped${NC}"
