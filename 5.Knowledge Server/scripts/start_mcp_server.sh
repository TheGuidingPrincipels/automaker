#!/bin/bash
#
# MCP Knowledge Server Startup Script (macOS/Linux)
#
# Starts the MCP Knowledge Management Server and ensures dependencies
# (Neo4j, Redis) are available. Designed to work when launched by
# Claude Desktop where PATH/env may be limited.

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🚀 Starting MCP Knowledge Server..."

# Directories
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Ensure .venv exists
if [ ! -d ".venv" ]; then
  echo -e "${RED}❌ Virtual environment not found at .venv${NC}"
  echo "Run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

# Ensure .env exists
if [ ! -f ".env" ]; then
  echo -e "${YELLOW}⚠️  .env not found, creating from .env.example...${NC}"
  if [ -f ".env.example" ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Edit .env to set Neo4j credentials, then re-run.${NC}"
    exit 1
  else
    echo -e "${RED}❌ .env.example missing; cannot proceed${NC}"
    exit 1
  fi
fi

# Env defaults (helpful when launched by Desktop)
export NEO4J_URI=${NEO4J_URI:-bolt://localhost:7687}
export NEO4J_USER=${NEO4J_USER:-neo4j}
if [ -n "$MCP_NEO4J_PASSWORD" ]; then
  export NEO4J_PASSWORD="$MCP_NEO4J_PASSWORD"
else
  export NEO4J_PASSWORD=${NEO4J_PASSWORD:-password}
fi

ensure_neo4j() {
  echo "🔍 Checking Neo4j container..."
  if docker ps --format '{{.Names}}' | grep -q '^mcp-knowledge-neo4j$'; then
    echo -e "${GREEN}✅ Neo4j running (mcp-knowledge-neo4j)${NC}"; return 0; fi
  if docker ps --format '{{.Names}}' | grep -q '^neo4j$'; then
    echo -e "${GREEN}✅ Neo4j running (neo4j)${NC}"; return 0; fi
  echo -e "${YELLOW}⚠️  Neo4j not running; attempting to start...${NC}"
  docker start mcp-knowledge-neo4j >/dev/null 2>&1 && { echo -e "${GREEN}✅ Started mcp-knowledge-neo4j${NC}"; return 0; }
  docker start neo4j >/dev/null 2>&1 && { echo -e "${GREEN}✅ Started neo4j${NC}"; return 0; }
  if [ -f "$PROJECT_ROOT/docker-compose.yml" ]; then
    echo "🧩 docker compose up -d (Neo4j)"
    (docker compose up -d || docker-compose up -d) || return 1
    sleep 3; return 0
  fi
  echo "🐳 Running Neo4j standalone container..."
  docker run -d --name mcp-knowledge-neo4j -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password neo4j:5-community >/dev/null 2>&1 || return 1
  sleep 3
}

ensure_redis() {
  echo "🔍 Checking Redis container..."
  if docker ps --format '{{.Names}}' | grep -q '^mcp-knowledge-redis$'; then
    echo -e "${GREEN}✅ Redis running (mcp-knowledge-redis)${NC}"; return 0; fi
  docker start mcp-knowledge-redis >/dev/null 2>&1 && { echo -e "${GREEN}✅ Started mcp-knowledge-redis${NC}"; return 0; }
  echo "🐳 Running Redis (redis:7) container..."
  docker run -d --name mcp-knowledge-redis -p 6379:6379 redis:7 >/dev/null 2>&1 || true
}

ensure_neo4j || { echo -e "${RED}❌ Neo4j could not be started. Aborting.${NC}"; exit 1; }
ensure_redis || true
echo ""

echo "📁 Checking data directories..."
mkdir -p data/chroma data/embeddings

if [ ! -f "data/events.db" ]; then
  echo -e "${YELLOW}⚠️  Event store missing; initializing...${NC}"
  source .venv/bin/activate
  python scripts/init_database.py
fi

echo -e "${GREEN}✅ Data directories ready${NC}"

echo "🐍 Activating venv..."
source .venv/bin/activate
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "   Python: $PYTHON_VERSION"

echo "📦 Verifying dependencies..."
python -c "import fastmcp, neo4j, chromadb, sentence_transformers" 2>/dev/null || {
  echo -e "${RED}❌ Missing dependencies; run 'pip install -r requirements.txt'${NC}"; exit 1; }

echo "🌟 Starting MCP Knowledge Server (knowledge-server)"
echo "----------------------------------------------------------------------"
python mcp_server.py
echo
echo "----------------------------------------------------------------------"
echo "🛑 Server stopped"

