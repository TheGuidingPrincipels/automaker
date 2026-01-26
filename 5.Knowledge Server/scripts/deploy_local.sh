#!/bin/bash
# Local Deployment Script for MCP Knowledge Server
# This script deploys the application locally using Docker Compose

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  MCP Knowledge Server - Local Deploy${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Configuration
VERSION="${1:-latest}"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.deploy.yml"

echo -e "${YELLOW}ℹ️  Deployment Version: ${VERSION}${NC}"
echo ""

# Step 1: Build Docker image
echo -e "${GREEN}[1/5] Building Docker image...${NC}"
docker build -t mcp-knowledge-server:${VERSION} .
echo -e "${GREEN}✅ Build complete${NC}"
echo ""

# Step 2: Tag as latest if this is a new deployment
if [ "$VERSION" != "latest" ]; then
    echo -e "${GREEN}[2/5] Tagging image as latest...${NC}"
    docker tag mcp-knowledge-server:${VERSION} mcp-knowledge-server:latest
    echo -e "${GREEN}✅ Tagged as latest${NC}"
else
    echo -e "${YELLOW}[2/5] Skipping tag (already latest)${NC}"
fi
echo ""

# Step 3: Stop existing containers (graceful)
echo -e "${GREEN}[3/5] Stopping existing containers...${NC}"
docker-compose ${COMPOSE_FILES} down || true
echo -e "${GREEN}✅ Containers stopped${NC}"
echo ""

# Step 4: Start new containers
echo -e "${GREEN}[4/5] Starting services...${NC}"
docker-compose ${COMPOSE_FILES} up -d
echo -e "${GREEN}✅ Services started${NC}"
echo ""

# Step 5: Wait for services to be healthy
echo -e "${GREEN}[5/5] Waiting for services to be healthy...${NC}"
sleep 10

# Check Neo4j
echo -n "   Checking Neo4j... "
if docker-compose ${COMPOSE_FILES} exec -T neo4j cypher-shell -u neo4j -p password "RETURN 1" &>/dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${YELLOW}⚠️  Neo4j not ready yet${NC}"
fi

# Check MCP Server
echo -n "   Checking MCP Server... "
if docker-compose ${COMPOSE_FILES} ps | grep -q "mcp-knowledge-server.*Up"; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${YELLOW}⚠️  MCP Server not ready yet${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Version deployed: ${GREEN}${VERSION}${NC}"
echo -e "View logs: ${YELLOW}docker-compose ${COMPOSE_FILES} logs -f${NC}"
echo -e "Stop services: ${YELLOW}docker-compose ${COMPOSE_FILES} down${NC}"
echo ""

# Run smoke tests if script exists
if [ -f "scripts/smoke_tests.py" ]; then
    echo -e "${YELLOW}Running smoke tests...${NC}"
    python3 scripts/smoke_tests.py --env local --critical-only || echo -e "${RED}⚠️  Smoke tests failed${NC}"
fi

echo ""
echo -e "${GREEN}Deployment successful!${NC}"
