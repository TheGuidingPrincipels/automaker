#!/bin/bash
# Local Rollback Script for MCP Knowledge Server
# Rolls back to a previous version by deploying a tagged Docker image

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if version argument provided
if [ -z "$1" ]; then
    echo -e "${RED}❌ Error: Version tag required${NC}"
    echo ""
    echo "Usage: $0 <version-tag>"
    echo ""
    echo "Examples:"
    echo "  $0 0.1.0-main-abc12345"
    echo "  $0 previous"
    echo ""
    echo "Available images:"
    docker images mcp-knowledge-server --format "table {{.Tag}}\t{{.CreatedAt}}" | head -10
    exit 1
fi

VERSION="$1"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.deploy.yml"

echo -e "${RED}========================================${NC}"
echo -e "${RED}  ⚠️  ROLLBACK WARNING${NC}"
echo -e "${RED}========================================${NC}"
echo ""
echo -e "${YELLOW}This will rollback to version: ${VERSION}${NC}"
echo ""
echo -n "Are you sure? (yes/no): "
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${YELLOW}Rollback cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}[1/4] Verifying rollback image exists...${NC}"
if ! docker images | grep -q "mcp-knowledge-server.*${VERSION}"; then
    echo -e "${RED}❌ Error: Image mcp-knowledge-server:${VERSION} not found${NC}"
    echo ""
    echo "Available images:"
    docker images mcp-knowledge-server --format "table {{.Tag}}\t{{.CreatedAt}}"
    exit 1
fi
echo -e "${GREEN}✅ Image found${NC}"
echo ""

# Create backup of current state
echo -e "${GREEN}[2/4] Creating backup of current state...${NC}"
BACKUP_TAG="backup-$(date +%Y%m%d-%H%M%S)"
docker tag mcp-knowledge-server:latest mcp-knowledge-server:${BACKUP_TAG} || true
echo -e "${GREEN}✅ Backup created: ${BACKUP_TAG}${NC}"
echo ""

# Stop current containers
echo -e "${GREEN}[3/4] Stopping current deployment...${NC}"
docker-compose ${COMPOSE_FILES} down
echo -e "${GREEN}✅ Stopped${NC}"
echo ""

# Deploy rollback version
echo -e "${GREEN}[4/4] Deploying rollback version...${NC}"
docker tag mcp-knowledge-server:${VERSION} mcp-knowledge-server:latest
docker-compose ${COMPOSE_FILES} up -d
echo -e "${GREEN}✅ Rollback deployed${NC}"
echo ""

# Wait for services
echo -e "${YELLOW}Waiting for services to start...${NC}"
sleep 10

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ Rollback Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Rolled back to: ${GREEN}${VERSION}${NC}"
echo -e "Backup created: ${YELLOW}${BACKUP_TAG}${NC}"
echo -e "View logs: ${YELLOW}docker-compose ${COMPOSE_FILES} logs -f${NC}"
echo ""

# Run smoke tests
if [ -f "scripts/smoke_tests.py" ]; then
    echo -e "${YELLOW}Running smoke tests...${NC}"
    python3 scripts/smoke_tests.py --env local --critical-only || echo -e "${RED}⚠️  Smoke tests failed - you may need to rollback further${NC}"
fi

echo ""
echo -e "${GREEN}Rollback successful!${NC}"
echo ""
echo -e "${YELLOW}To revert this rollback:${NC}"
echo -e "  ./scripts/rollback_local.sh ${BACKUP_TAG}"
