#!/bin/bash
#
# MCP Knowledge Server - Production Environment Setup
#
# This script sets up a production environment for the MCP Knowledge Server.
# Run once during initial deployment.
#
# Usage:
#   sudo ./production_setup.sh
#
# What it does:
# - Creates system user and group
# - Sets up directory structure
# - Configures file permissions
# - Installs systemd service (Linux only)
# - Sets up log rotation
# - Configures cron jobs for backups and monitoring

set -e

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
INSTALL_DIR="${INSTALL_DIR:-/opt/mcp-knowledge-server}"
USER="${MCP_USER:-mcp}"
GROUP="${MCP_GROUP:-mcp}"
DATA_DIR="$INSTALL_DIR/data"
LOG_DIR="/var/log/mcp-knowledge-server"
BACKUP_DIR="${BACKUP_DIR:-$INSTALL_DIR/backups}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  MCP Knowledge Server - Production Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}⚠️  This script should be run as root for full setup${NC}"
    echo "Some operations may be skipped."
    echo ""
    SUDO_PREFIX="sudo "
else
    SUDO_PREFIX=""
fi

# 1. Create system user and group
echo -e "${YELLOW}[1/9] Creating system user and group...${NC}"

if id "$USER" &>/dev/null; then
    echo "  User '$USER' already exists"
else
    ${SUDO_PREFIX}useradd --system --shell /bin/bash --home-dir "$INSTALL_DIR" --create-home "$USER" || true
    echo -e "${GREEN}  ✅ User '$USER' created${NC}"
fi

# 2. Create directory structure
echo -e "${YELLOW}[2/9] Creating directory structure...${NC}"

${SUDO_PREFIX}mkdir -p "$INSTALL_DIR"
${SUDO_PREFIX}mkdir -p "$DATA_DIR"/{chroma,embeddings}
${SUDO_PREFIX}mkdir -p "$LOG_DIR"
${SUDO_PREFIX}mkdir -p "$BACKUP_DIR"/{neo4j,sqlite,chromadb,unified}
${SUDO_PREFIX}mkdir -p "$INSTALL_DIR/monitoring"

echo -e "${GREEN}  ✅ Directories created${NC}"

# 3. Copy project files
echo -e "${YELLOW}[3/9] Copying project files...${NC}"

if [ "$PROJECT_DIR" != "$INSTALL_DIR" ]; then
    ${SUDO_PREFIX}cp -r "$PROJECT_DIR"/* "$INSTALL_DIR/" 2>/dev/null || true
    echo -e "${GREEN}  ✅ Files copied to $INSTALL_DIR${NC}"
else
    echo "  Already in install directory, skipping copy"
fi

# 4. Set up Python virtual environment
echo -e "${YELLOW}[4/9] Setting up Python virtual environment...${NC}"

if [ ! -d "$INSTALL_DIR/.venv" ]; then
    ${SUDO_PREFIX}python3 -m venv "$INSTALL_DIR/.venv"
    ${SUDO_PREFIX}"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
    ${SUDO_PREFIX}"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    echo -e "${GREEN}  ✅ Virtual environment created and dependencies installed${NC}"
else
    echo "  Virtual environment already exists"
fi

# 5. Set up environment configuration
echo -e "${YELLOW}[5/9] Setting up environment configuration...${NC}"

if [ ! -f "$INSTALL_DIR/.env" ]; then
    if [ -f "$INSTALL_DIR/.env.production" ]; then
        ${SUDO_PREFIX}cp "$INSTALL_DIR/.env.production" "$INSTALL_DIR/.env"
        echo -e "${GREEN}  ✅ Environment file created from .env.production${NC}"
        echo -e "${YELLOW}  ⚠️  IMPORTANT: Edit $INSTALL_DIR/.env with production values${NC}"
    else
        ${SUDO_PREFIX}cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env" 2>/dev/null || true
        echo -e "${YELLOW}  ⚠️  Created .env from example - MUST be configured${NC}"
    fi
else
    echo "  Environment file already exists"
fi

# 6. Set file permissions
echo -e "${YELLOW}[6/9] Setting file permissions...${NC}"

${SUDO_PREFIX}chown -R "$USER:$GROUP" "$INSTALL_DIR"
${SUDO_PREFIX}chown -R "$USER:$GROUP" "$LOG_DIR"
${SUDO_PREFIX}chown -R "$USER:$GROUP" "$BACKUP_DIR"

# Secure .env file
${SUDO_PREFIX}chmod 600 "$INSTALL_DIR/.env"

# Make scripts executable
${SUDO_PREFIX}chmod +x "$INSTALL_DIR"/backup/*.sh
${SUDO_PREFIX}chmod +x "$INSTALL_DIR"/monitoring/*.py
${SUDO_PREFIX}chmod +x "$INSTALL_DIR"/monitoring/*.sh
${SUDO_PREFIX}chmod +x "$INSTALL_DIR"/scripts/*.sh

echo -e "${GREEN}  ✅ Permissions set${NC}"

# 7. Install systemd service (Linux only)
echo -e "${YELLOW}[7/9] Installing systemd service...${NC}"

if command -v systemctl &> /dev/null; then
    # Update paths in service file
    SERVICE_FILE="$INSTALL_DIR/deployment/mcp-knowledge-server.service"
    TEMP_SERVICE="/tmp/mcp-knowledge-server.service"

    sed "s|/opt/mcp-knowledge-server|$INSTALL_DIR|g" "$SERVICE_FILE" > "$TEMP_SERVICE"
    sed -i "s|User=mcp|User=$USER|g" "$TEMP_SERVICE"
    sed -i "s|Group=mcp|Group=$GROUP|g" "$TEMP_SERVICE"

    ${SUDO_PREFIX}cp "$TEMP_SERVICE" /etc/systemd/system/mcp-knowledge-server.service
    ${SUDO_PREFIX}systemctl daemon-reload
    ${SUDO_PREFIX}systemctl enable mcp-knowledge-server.service

    echo -e "${GREEN}  ✅ Systemd service installed and enabled${NC}"
    echo "     Start with: sudo systemctl start mcp-knowledge-server"
else
    echo "  Systemd not available, skipping service installation"
fi

# 8. Set up log rotation
echo -e "${YELLOW}[8/9] Setting up log rotation...${NC}"

if [ -d /etc/logrotate.d ]; then
    cat > /tmp/mcp-logrotate << EOF
$LOG_DIR/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 $USER $GROUP
    sharedscripts
    postrotate
        systemctl reload mcp-knowledge-server > /dev/null 2>&1 || true
    endscript
}
EOF
    ${SUDO_PREFIX}cp /tmp/mcp-logrotate /etc/logrotate.d/mcp-knowledge-server
    echo -e "${GREEN}  ✅ Log rotation configured${NC}"
else
    echo "  Logrotate not available, skipping"
fi

# 9. Set up cron jobs
echo -e "${YELLOW}[9/9] Setting up cron jobs...${NC}"

CRON_FILE="/tmp/mcp-cron-$USER"

cat > "$CRON_FILE" << EOF
# MCP Knowledge Server Automated Tasks

# Daily backup at 2 AM
0 2 * * * $INSTALL_DIR/backup/backup_all.sh >> $LOG_DIR/backup.log 2>&1

# Service monitoring every 5 minutes
*/5 * * * * $INSTALL_DIR/monitoring/service_monitor.sh --auto-restart >> $LOG_DIR/service_monitor.log 2>&1

# Resource monitoring every 10 minutes
*/10 * * * * $INSTALL_DIR/monitoring/resource_monitor.py --alert >> $LOG_DIR/resource_monitor.log 2>&1

# Health check every hour
0 * * * * $INSTALL_DIR/monitoring/health_check.py >> $LOG_DIR/health_check.log 2>&1
EOF

if command -v crontab &> /dev/null; then
    ${SUDO_PREFIX}crontab -u "$USER" "$CRON_FILE"
    echo -e "${GREEN}  ✅ Cron jobs configured${NC}"
else
    echo "  Cron not available, manual setup required"
    echo "  See: $CRON_FILE"
fi

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Production Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Installation Details:"
echo "  Install Directory: $INSTALL_DIR"
echo "  Data Directory: $DATA_DIR"
echo "  Log Directory: $LOG_DIR"
echo "  Backup Directory: $BACKUP_DIR"
echo "  User: $USER"
echo "  Group: $GROUP"
echo ""
echo "Next Steps:"
echo "  1. Edit configuration: $INSTALL_DIR/.env"
echo "  2. Update Neo4j password in .env"
echo "  3. Start Neo4j: docker start neo4j"
echo "  4. Initialize database: $INSTALL_DIR/scripts/init_database.py"
echo "  5. Start server:"
if command -v systemctl &> /dev/null; then
    echo "     sudo systemctl start mcp-knowledge-server"
else
    echo "     $INSTALL_DIR/scripts/production_start.sh"
fi
echo "  6. Check status: $INSTALL_DIR/monitoring/health_check.py"
echo ""
echo "Documentation:"
echo "  - Production Deployment: $INSTALL_DIR/docs/PRODUCTION_DEPLOYMENT.md"
echo "  - Backup & Restore: $INSTALL_DIR/docs/BACKUP_AND_RESTORE.md"
echo "  - Monitoring Guide: $INSTALL_DIR/docs/MONITORING_GUIDE.md"
echo ""
