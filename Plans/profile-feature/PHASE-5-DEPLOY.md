# Phase 5: Production Deployment

> **Status**: Planning
> **Estimated Duration**: 1 week
> **Prerequisites**: Phases 1-4 complete
> **Blocks**: None (final phase)

## Objective

Deploy the multi-user Automaker to Hetzner cloud with proper SSL, monitoring, and backup. After this phase:

- System accessible via HTTPS at your domain
- 3 team members can use it simultaneously
- Automated backups protect data
- Monitoring alerts on issues

## What This Phase DOES

- Configures production Docker deployment
- Sets up SSL with Traefik/Caddy
- Configures environment variables for production
- Sets up automated backups
- Adds basic monitoring and alerting
- Documents operational procedures

## What This Phase DOES NOT Do

| Excluded Feature        | Handled In |
| ----------------------- | ---------- |
| User registration/login | Phase 1    |
| Per-user credentials    | Phase 2    |
| Knowledge Hub sync      | Phase 3    |
| OAuth authentication    | Phase 4    |

---

## Infrastructure Specification

### Recommended Server

**Hetzner CPX41** (Shared vCPU):

- 16 vCPU (AMD EPYC)
- 32 GB RAM
- 360 GB SSD
- 20 TB Traffic
- **Cost**: ~72 EUR/month

This supports:

- 3 concurrent users
- Up to 9 concurrent agent runs (3 per user)
- Room for growth

### Network Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HETZNER VPS                                        │
│                        (CPX41 - 32GB RAM)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         TRAEFIK                                      │   │
│  │                    (Reverse Proxy + SSL)                             │   │
│  │                                                                      │   │
│  │  Port 80  ───► Redirect to HTTPS                                    │   │
│  │  Port 443 ───► Route to services                                    │   │
│  │                                                                      │   │
│  │  - automaker.yourdomain.com → UI (nginx)                            │   │
│  │  - automaker.yourdomain.com/api/* → Server (node)                   │   │
│  │  - automaker.yourdomain.com/api/events → WebSocket                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│              ┌───────────────┴───────────────┐                             │
│              │                               │                              │
│              ▼                               ▼                              │
│  ┌─────────────────────┐       ┌─────────────────────┐                     │
│  │   automaker-ui      │       │  automaker-server   │                     │
│  │   (nginx:alpine)    │       │   (node:22-slim)    │                     │
│  │                     │       │                     │                     │
│  │   Static assets     │       │   Express + WS      │                     │
│  │   Port 80 internal  │       │   Port 3008         │                     │
│  └─────────────────────┘       └──────────┬──────────┘                     │
│                                           │                                 │
│                                           ▼                                 │
│                              ┌─────────────────────┐                       │
│                              │   Named Volumes     │                       │
│                              │                     │                       │
│                              │  - automaker-data   │                       │
│                              │  - automaker-db     │                       │
│                              │  - traefik-certs    │                       │
│                              └─────────────────────┘                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Configuration Files

### 1. Production Docker Compose

**File to Create**: `docker-compose.production.yml`

```yaml
version: '3.8'

services:
  traefik:
    image: traefik:v3.0
    container_name: automaker-traefik
    restart: unless-stopped
    command:
      - '--api.dashboard=true'
      - '--providers.docker=true'
      - '--providers.docker.exposedbydefault=false'
      - '--entrypoints.web.address=:80'
      - '--entrypoints.websecure.address=:443'
      - '--entrypoints.web.http.redirections.entryPoint.to=websecure'
      - '--certificatesresolvers.letsencrypt.acme.httpchallenge=true'
      - '--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web'
      - '--certificatesresolvers.letsencrypt.acme.email=${ACME_EMAIL}'
      - '--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json'
    ports:
      - '80:80'
      - '443:443'
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik-certs:/letsencrypt
    labels:
      - 'traefik.enable=true'
      # Dashboard (optional, protected)
      - 'traefik.http.routers.traefik.rule=Host(`traefik.${DOMAIN}`)'
      - 'traefik.http.routers.traefik.service=api@internal'
      - 'traefik.http.routers.traefik.tls.certresolver=letsencrypt'
      - 'traefik.http.routers.traefik.middlewares=auth'
      - 'traefik.http.middlewares.auth.basicauth.users=${TRAEFIK_USERS}'
    networks:
      - automaker-network

  ui:
    build:
      context: .
      dockerfile: Dockerfile
      target: ui
      args:
        - VITE_SERVER_URL=https://${DOMAIN}
    container_name: automaker-ui
    restart: unless-stopped
    labels:
      - 'traefik.enable=true'
      - 'traefik.http.routers.ui.rule=Host(`${DOMAIN}`)'
      - 'traefik.http.routers.ui.tls.certresolver=letsencrypt'
      - 'traefik.http.routers.ui.priority=1'
      - 'traefik.http.services.ui.loadbalancer.server.port=80'
    networks:
      - automaker-network

  server:
    build:
      context: .
      dockerfile: Dockerfile
      target: server
      args:
        - UID=1001
        - GID=1001
    container_name: automaker-server
    restart: unless-stopped
    environment:
      - NODE_ENV=production
      - DATA_DIR=/data
      - DATABASE_URL=file:/data/automaker.db
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - AUTOMAKER_ENCRYPTION_KEY=${AUTOMAKER_ENCRYPTION_KEY}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID:-}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET:-}
      - GOOGLE_CALLBACK_URL=https://${DOMAIN}/api/auth/google/callback
      - CORS_ORIGIN=https://${DOMAIN}
      - IS_CONTAINERIZED=true
      - AUTOMAKER_HIDE_API_KEY=true
    volumes:
      - automaker-data:/data
      - automaker-claude-config:/home/automaker/.claude
      - automaker-cursor-config:/home/automaker/.cursor
      - /projects:/projects:rw # Mount projects directory
    labels:
      - 'traefik.enable=true'
      - 'traefik.http.routers.api.rule=Host(`${DOMAIN}`) && PathPrefix(`/api`)'
      - 'traefik.http.routers.api.tls.certresolver=letsencrypt'
      - 'traefik.http.routers.api.priority=2'
      - 'traefik.http.services.api.loadbalancer.server.port=3008'
    networks:
      - automaker-network
    healthcheck:
      test: ['CMD', 'curl', '-f', 'http://localhost:3008/api/health']
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

volumes:
  traefik-certs:
  automaker-data:
  automaker-claude-config:
  automaker-cursor-config:

networks:
  automaker-network:
    driver: bridge
```

### 2. Production Environment File

**File to Create**: `.env.production.example`

```bash
# ===========================================
# AUTOMAKER PRODUCTION CONFIGURATION
# ===========================================

# Domain Configuration
DOMAIN=automaker.yourdomain.com
ACME_EMAIL=admin@yourdomain.com

# Traefik Dashboard Auth (generate with: htpasswd -nb admin password)
TRAEFIK_USERS=admin:$$apr1$$...

# ===========================================
# SECURITY (REQUIRED)
# ===========================================

# Encryption key for user credentials (64 hex chars)
# Generate with: node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
AUTOMAKER_ENCRYPTION_KEY=

# ===========================================
# AI PROVIDER CREDENTIALS (Optional - users can add their own)
# ===========================================

# Global fallback API keys (optional)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# ===========================================
# OAUTH (Optional)
# ===========================================

# Google OAuth (from Google Cloud Console)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# ===========================================
# OPERATIONAL
# ===========================================

# Disable API key display in logs
AUTOMAKER_HIDE_API_KEY=true

# Projects directory (mounted in container)
PROJECTS_DIR=/projects
```

### 3. Backup Script

**File to Create**: `scripts/backup.sh`

```bash
#!/bin/bash
set -e

# Configuration
BACKUP_DIR="/backups/automaker"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Stop containers briefly for consistent backup
echo "Creating backup $DATE..."

# Backup SQLite database
docker exec automaker-server sqlite3 /data/automaker.db ".backup '/tmp/backup.db'"
docker cp automaker-server:/tmp/backup.db "$BACKUP_DIR/automaker-db-$DATE.db"
docker exec automaker-server rm /tmp/backup.db

# Backup data volume
docker run --rm \
  -v automaker-data:/data:ro \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf "/backup/automaker-data-$DATE.tar.gz" -C /data .

# Backup team storage
docker run --rm \
  -v automaker-data:/data:ro \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf "/backup/automaker-team-$DATE.tar.gz" -C /data/team .

# Delete old backups
find "$BACKUP_DIR" -name "*.db" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"/*-$DATE.*
```

**Cron job** (add to `/etc/crontab`):

```
0 3 * * * root /opt/automaker/scripts/backup.sh >> /var/log/automaker-backup.log 2>&1
```

### 4. Restore Script

**File to Create**: `scripts/restore.sh`

```bash
#!/bin/bash
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <backup-date>"
  echo "Example: $0 20260123_030000"
  exit 1
fi

BACKUP_DIR="/backups/automaker"
DATE=$1

echo "Restoring from backup $DATE..."

# Stop services
docker compose -f docker-compose.production.yml stop server

# Restore database
docker cp "$BACKUP_DIR/automaker-db-$DATE.db" automaker-server:/data/automaker.db

# Restore data volume
docker run --rm \
  -v automaker-data:/data \
  -v "$BACKUP_DIR":/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/automaker-data-$DATE.tar.gz -C /data"

# Start services
docker compose -f docker-compose.production.yml start server

echo "Restore completed"
```

---

## Deployment Steps

### 1. Server Setup (Hetzner)

```bash
# 1. Create CPX41 server in Hetzner Cloud Console
# - Location: Your preferred region
# - Image: Ubuntu 24.04
# - SSH key: Your public key

# 2. SSH into server
ssh root@your-server-ip

# 3. Update system
apt update && apt upgrade -y

# 4. Install Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# 5. Install Docker Compose
apt install docker-compose-plugin -y

# 6. Create directories
mkdir -p /opt/automaker
mkdir -p /projects
mkdir -p /backups/automaker

# 7. Clone repository
cd /opt/automaker
git clone https://github.com/your-repo/automaker.git .

# 8. Copy and configure environment
cp .env.production.example .env
nano .env  # Edit with your values
```

### 2. Generate Secrets

```bash
# Generate encryption key
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
# Copy output to AUTOMAKER_ENCRYPTION_KEY

# Generate Traefik password
apt install apache2-utils -y
htpasswd -nb admin your-secure-password
# Copy output to TRAEFIK_USERS (double $ signs for docker-compose)
```

### 3. Deploy

```bash
# Build and start
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml up -d

# Check logs
docker compose -f docker-compose.production.yml logs -f

# Verify health
curl https://your-domain.com/api/health
```

### 4. DNS Configuration

Add DNS records:

```
A    automaker.yourdomain.com    → your-server-ip
A    traefik.yourdomain.com      → your-server-ip  (optional, for dashboard)
```

### 5. First User Setup

```bash
# Create first admin user via API
curl -X POST https://automaker.yourdomain.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yourdomain.com","password":"secure-password","name":"Admin"}'

# Or use Google OAuth (if configured)
# Visit: https://automaker.yourdomain.com/login
# Click "Sign in with Google"
```

---

## Monitoring

### 1. Health Check Endpoint

The `/api/health/detailed` endpoint returns:

```json
{
  "status": "healthy",
  "timestamp": "2026-01-23T10:00:00Z",
  "version": "1.0.0",
  "memory": {
    "heapUsed": 150000000,
    "heapTotal": 250000000,
    "rss": 300000000
  },
  "uptime": 86400,
  "activeAgents": 3,
  "activeWorktrees": 5
}
```

### 2. Simple Monitoring Script

**File to Create**: `scripts/monitor.sh`

```bash
#!/bin/bash

DOMAIN="automaker.yourdomain.com"
ALERT_EMAIL="admin@yourdomain.com"

# Check health endpoint
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/api/health")

if [ "$HEALTH" != "200" ]; then
  echo "ALERT: Automaker health check failed (HTTP $HEALTH)" | \
    mail -s "Automaker Down" "$ALERT_EMAIL"
fi

# Check memory usage
MEMORY=$(docker stats --no-stream --format "{{.MemPerc}}" automaker-server | tr -d '%')
if (( $(echo "$MEMORY > 80" | bc -l) )); then
  echo "WARNING: Automaker memory usage at ${MEMORY}%" | \
    mail -s "Automaker High Memory" "$ALERT_EMAIL"
fi

# Check disk usage
DISK=$(df /var/lib/docker | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK" -gt 85 ]; then
  echo "WARNING: Disk usage at ${DISK}%" | \
    mail -s "Automaker Low Disk" "$ALERT_EMAIL"
fi
```

**Cron job**:

```
*/5 * * * * /opt/automaker/scripts/monitor.sh
```

### 3. Log Aggregation

```bash
# View all logs
docker compose -f docker-compose.production.yml logs -f

# View specific service
docker compose -f docker-compose.production.yml logs -f server

# Export logs
docker compose -f docker-compose.production.yml logs --no-color > logs.txt
```

---

## Operational Procedures

### Updating Automaker

```bash
cd /opt/automaker

# Pull latest code
git pull origin main

# Rebuild and restart
docker compose -f docker-compose.production.yml build
docker compose -f docker-compose.production.yml up -d

# Run database migrations (if any)
docker exec automaker-server npx prisma migrate deploy
```

### Adding a New User

Users can self-register via:

1. Google OAuth (click "Sign in with Google")
2. Email/password registration form

To create admin user manually:

```bash
docker exec -it automaker-server node -e "
const { initializeDatabase } = require('./lib/database');
const { getUserService } = require('./services/user-service');
async function createAdmin() {
  await initializeDatabase();
  const user = await getUserService().createUser({
    email: 'admin@example.com',
    password: 'secure-password',
    name: 'Admin User'
  });
  console.log('Created user:', user.id);
}
createAdmin();
"
```

### Viewing User Sessions

```bash
docker exec automaker-server sqlite3 /data/automaker.db \
  "SELECT u.email, s.createdAt FROM sessions s JOIN users u ON s.userId = u.id;"
```

### Revoking All Sessions

```bash
docker exec automaker-server sqlite3 /data/automaker.db \
  "DELETE FROM sessions WHERE userId = 'user-id-here';"
```

---

## Security Checklist

- [ ] AUTOMAKER_ENCRYPTION_KEY is set and backed up securely
- [ ] SSL certificate is valid and auto-renewing
- [ ] Traefik dashboard is password protected
- [ ] CORS_ORIGIN is set to your domain only
- [ ] SSH key authentication (disable password SSH)
- [ ] Firewall allows only 80, 443, and SSH
- [ ] Regular backups configured and tested
- [ ] Monitoring alerts configured

### Firewall Configuration

```bash
# UFW setup
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

---

## Testing Checklist

### Deployment Tests

- [ ] `curl https://your-domain.com/api/health` returns 200
- [ ] SSL certificate is valid (check with browser)
- [ ] WebSocket connects (check browser console)
- [ ] Login works (email/password and OAuth)

### Multi-User Tests

- [ ] User A can register and login
- [ ] User B can register and login
- [ ] User A creates knowledge, User B sees it
- [ ] Both users can run agents simultaneously

### Backup/Restore Tests

- [ ] Backup script runs without errors
- [ ] Backup files created with correct permissions
- [ ] Restore from backup works
- [ ] Data integrity verified after restore

---

## Success Criteria

Phase 5 is complete when:

1. System accessible via HTTPS
2. SSL auto-renewal working
3. 3 team members can login and use system
4. Automated backups running daily
5. Basic monitoring alerts configured
6. Documentation for team operations complete

---

## Troubleshooting

### Common Issues

| Issue                      | Cause                    | Solution                                  |
| -------------------------- | ------------------------ | ----------------------------------------- |
| SSL certificate error      | Let's Encrypt rate limit | Wait 1 hour, check DNS                    |
| WebSocket connection fails | Traefik config           | Check router priority                     |
| Database locked            | Concurrent access        | Restart server container                  |
| OAuth callback fails       | Wrong callback URL       | Check GOOGLE_CALLBACK_URL                 |
| Container out of memory    | Too many agents          | Increase server size or limit concurrency |

### Useful Commands

```bash
# Check container status
docker compose -f docker-compose.production.yml ps

# Restart specific service
docker compose -f docker-compose.production.yml restart server

# View real-time logs
docker compose -f docker-compose.production.yml logs -f server

# Execute command in container
docker exec -it automaker-server bash

# Check database
docker exec automaker-server sqlite3 /data/automaker.db ".tables"

# Check disk usage
df -h /var/lib/docker
```

---

## Post-Deployment

After successful deployment:

1. **Share access** with team members
2. **Document team procedures** (how to add API keys, use features)
3. **Set up Slack/Discord alerts** for monitoring (optional)
4. **Schedule quarterly security reviews**
5. **Plan capacity upgrades** if team grows
