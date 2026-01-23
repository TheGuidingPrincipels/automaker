# Session 10: Integration, Polish & Deployment

> ⚠️ **Deployment Note**: v1 is **web-only** and integrated into Automaker. This session is mainly for standalone deployment hardening; treat it as **deferred** for the Automaker-integrated rollout.

## Overview

**Duration**: ~4 hours
**Goal**: Final integration testing, error handling polish, and deployment configuration for Hetzner.

**Deliverable**: Production-ready application with Docker Compose, environment configuration, and deployment documentation.

---

## Prerequisites

- Sessions 1-9 completed
- Docker and Docker Compose installed
- Hetzner Cloud account (for deployment)

---

## Objectives & Acceptance Criteria

| #   | Objective             | Acceptance Criteria         |
| --- | --------------------- | --------------------------- |
| 1   | End-to-end testing    | Full user flow works        |
| 2   | Error boundaries      | Graceful error handling     |
| 3   | Loading states        | Consistent loading UX       |
| 4   | Production Dockerfile | Optimized multi-stage build |
| 5   | Docker Compose prod   | Production configuration    |
| 6   | Environment config    | All settings via env vars   |
| 7   | Health checks         | Container health monitoring |
| 8   | Hetzner deployment    | Working deployment guide    |

---

## File Structure

```
Speed Reading/
├── backend/
│   ├── Dockerfile              # Production Dockerfile
│   └── .env.example
├── frontend/
│   ├── Dockerfile              # Production Dockerfile
│   └── nginx.conf              # Nginx config for SPA
├── docker-compose.yml          # Development
├── docker-compose.prod.yml     # Production
├── .env.example                # Environment template
├── deploy/
│   ├── hetzner-setup.md        # Hetzner deployment guide
│   └── nginx-site.conf         # Reverse proxy config
└── scripts/
    ├── deploy.sh               # Deployment script
    └── backup-db.sh            # Database backup
```

---

## Implementation Details

### 1. Frontend Error Boundary (`src/components/common/ErrorBoundary.tsx`)

```typescript
import { Component, ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
          <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
          <h2 className="text-xl font-bold mb-2">Something went wrong</h2>
          <p className="text-muted-foreground mb-4 text-center max-w-md">
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <div className="flex gap-4">
            <Button onClick={this.handleRetry}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
            <Button variant="outline" onClick={() => window.location.href = '/deepread'}>
              Go Home
            </Button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
```

### 2. Global Error Handler (`src/lib/errorHandler.ts`)

```typescript
export function setupGlobalErrorHandler() {
  // Unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);

    // Could send to error tracking service here
  });

  // Global errors
  window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
  });
}

export function isNetworkError(error: unknown): boolean {
  if (error instanceof Error) {
    return (
      error.message.includes('fetch') ||
      error.message.includes('network') ||
      error.message.includes('Failed to fetch')
    );
  }
  return false;
}

export function getUserFriendlyMessage(error: unknown): string {
  if (error instanceof Error) {
    if (isNetworkError(error)) {
      return 'Unable to connect to the server. Please check your internet connection.';
    }

    if (error.message.includes('413')) {
      return 'The document is too large. Please use a smaller file.';
    }

    if (error.message.includes('422')) {
      return 'The file could not be processed. It may be corrupted or in an unsupported format.';
    }

    if (error.message.includes('404')) {
      return 'The requested resource was not found.';
    }

    return error.message;
  }

  return 'An unexpected error occurred';
}
```

### 3. Update App with Error Boundary (`src/App.tsx`)

```typescript
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { ErrorBoundary } from '@/components/common/ErrorBoundary'
import { setupGlobalErrorHandler, getUserFriendlyMessage } from '@/lib/errorHandler'
import { router } from './utils/router'
import { useEffect } from 'react'
import { SplashScreen } from './components/splash-screen'
import { useState } from 'react'

export function App() {
  const [showSplash, setShowSplash] = useState(() => {
    if (sessionStorage.getItem('automaker-splash-shown')) {
      return false
    }
    return true
  })

  useEffect(() => {
    setupGlobalErrorHandler()
  }, [])

  const handleSplashComplete = () => {
    sessionStorage.setItem('automaker-splash-shown', 'true')
    setShowSplash(false)
  }

  return (
    <ErrorBoundary>
      <RouterProvider router={router} />
      {showSplash && <SplashScreen onComplete={handleSplashComplete} />}
    </ErrorBoundary>
  )
}
```

### 4. Backend Production Dockerfile (`backend/Dockerfile`)

```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/api/health')"

# Run
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 5. Frontend Production Dockerfile (`frontend/Dockerfile`)

```dockerfile
# Build stage
FROM node:20-alpine as builder

WORKDIR /app

# Install dependencies
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

# Copy source and build
COPY . .
RUN pnpm build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:80 || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 6. Frontend Nginx Config (`frontend/nginx.conf`)

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 1000;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API proxy (when running standalone, proxy to backend)
    location /api {
        proxy_pass http://backend:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SPA routing - serve index.html for all non-file routes
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### 7. Production Docker Compose (`docker-compose.prod.yml`)

```yaml
version: '3.9'

services:
  db:
    image: postgres:16-alpine
    container_name: deepread-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER:-deepread}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME:-deepread}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U ${DB_USER:-deepread}']
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - internal

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: deepread-backend
    restart: unless-stopped
    environment:
      DATABASE_URL: postgresql://${DB_USER:-deepread}:${DB_PASSWORD}@db:5432/${DB_NAME:-deepread}
      DEBUG: 'false'
      MAX_DOCUMENT_WORDS: ${MAX_DOCUMENT_WORDS:-20000}
      CHUNK_SIZE: ${CHUNK_SIZE:-500}
      SESSION_EXPIRY_DAYS: ${SESSION_EXPIRY_DAYS:-7}
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test:
        [
          'CMD',
          'python',
          '-c',
          "import urllib.request; urllib.request.urlopen('http://localhost:8001/api/health')",
        ]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - internal

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: deepread-frontend
    restart: unless-stopped
    depends_on:
      - backend
    networks:
      - internal
      - external

  nginx:
    image: nginx:alpine
    container_name: deepread-nginx
    restart: unless-stopped
    ports:
      - '80:80'
      - '443:443'
    volumes:
      - ./deploy/nginx-site.conf:/etc/nginx/conf.d/default.conf:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - frontend
    networks:
      - external

  certbot:
    image: certbot/certbot
    container_name: deepread-certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"

volumes:
  postgres_data:

networks:
  internal:
    driver: bridge
  external:
    driver: bridge
```

### 8. Reverse Proxy Config (`deploy/nginx-site.conf`)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # API routes
    location /api {
        proxy_pass http://backend:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long uploads
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # File upload size
        client_max_body_size 10M;
    }

    # Frontend
    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 9. Environment Template (`.env.example`)

```env
# Database
DB_USER=deepread
DB_PASSWORD=your-secure-password-here
DB_NAME=deepread

# Backend
DATABASE_URL=postgresql://deepread:password@db:5432/deepread
DEBUG=false
MAX_DOCUMENT_WORDS=20000
CHUNK_SIZE=500
SESSION_EXPIRY_DAYS=7

# Domain (for SSL)
DOMAIN=your-domain.com
```

### 10. Deployment Script (`scripts/deploy.sh`)

```bash
#!/bin/bash
set -e

echo "=== DeepRead Deployment Script ==="

# Check environment
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    echo "Copy .env.example to .env and configure it"
    exit 1
fi

# Load environment
source .env

# Build and deploy
echo "Building containers..."
docker-compose -f docker-compose.prod.yml build

echo "Running database migrations..."
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

echo "Starting services..."
docker-compose -f docker-compose.prod.yml up -d

echo "Waiting for services to be healthy..."
sleep 10

# Health check
echo "Checking health..."
if curl -f http://localhost/api/health > /dev/null 2>&1; then
    echo "✅ Deployment successful!"
    echo "Application is running at http://localhost"
else
    echo "❌ Health check failed"
    docker-compose -f docker-compose.prod.yml logs
    exit 1
fi
```

### 11. Database Backup Script (`scripts/backup-db.sh`)

```bash
#!/bin/bash
set -e

# Configuration
BACKUP_DIR="/backups/deepread"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/deepread_$DATE.sql.gz"

# Create backup directory
mkdir -p $BACKUP_DIR

# Dump database
echo "Creating backup..."
docker-compose -f docker-compose.prod.yml exec -T db \
    pg_dump -U deepread deepread | gzip > $BACKUP_FILE

echo "Backup created: $BACKUP_FILE"

# Keep only last 7 days of backups
echo "Cleaning old backups..."
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Done!"
```

### 12. Hetzner Deployment Guide (`deploy/hetzner-setup.md`)

````markdown
# DeepRead Hetzner Deployment Guide

## Prerequisites

- Hetzner Cloud account
- Domain name pointing to your server
- SSH key configured

## Server Setup

### 1. Create Cloud Server

1. Go to Hetzner Cloud Console
2. Create new server:
   - Location: Choose nearest to users
   - Image: Ubuntu 24.04
   - Type: CX21 (2 vCPU, 4 GB RAM) minimum
   - SSH Key: Add your public key

### 2. Initial Server Configuration

```bash
# SSH into server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
apt install docker-compose-plugin -y

# Create app user
useradd -m -s /bin/bash deepread
usermod -aG docker deepread

# Create app directory
mkdir -p /opt/deepread
chown deepread:deepread /opt/deepread
```
````

### 3. Deploy Application

```bash
# Switch to app user
su - deepread
cd /opt/deepread

# Clone repository (or copy files)
git clone https://github.com/your-repo/deepread.git .

# Create environment file
cp .env.example .env
nano .env  # Edit with your settings

# Generate secure password
openssl rand -base64 32  # Use this for DB_PASSWORD

# Run deployment
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### 4. SSL Setup with Let's Encrypt

```bash
# Initial certificate
docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email your-email@domain.com \
    --agree-tos \
    --no-eff-email \
    -d your-domain.com

# Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

### 5. Set Up Automated Backups

```bash
# Add to crontab
crontab -e

# Add line for daily backups at 3 AM
0 3 * * * /opt/deepread/scripts/backup-db.sh >> /var/log/deepread-backup.log 2>&1
```

### 6. Monitoring

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f

# View specific service
docker-compose -f docker-compose.prod.yml logs -f backend

# Check container health
docker ps
```

## Maintenance

### Update Application

```bash
cd /opt/deepread
git pull
./scripts/deploy.sh
```

### Restore Database

```bash
# Stop services
docker-compose -f docker-compose.prod.yml stop backend

# Restore
gunzip < /backups/deepread/deepread_YYYYMMDD_HHMMSS.sql.gz | \
    docker-compose -f docker-compose.prod.yml exec -T db psql -U deepread deepread

# Start services
docker-compose -f docker-compose.prod.yml start backend
```

## Troubleshooting

### Container won't start

```bash
docker-compose -f docker-compose.prod.yml logs backend
```

### Database connection issues

```bash
docker-compose -f docker-compose.prod.yml exec db psql -U deepread -c "SELECT 1"
```

### SSL certificate issues

```bash
docker-compose -f docker-compose.prod.yml run --rm certbot certificates
```

````

---

## Testing Requirements

### End-to-End Test Suite

```typescript
// tests/e2e/full-flow.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Full User Flow', () => {
  test('complete reading session', async ({ page }) => {
    // 1. Navigate to home
    await page.goto('/deepread')
    await expect(page.locator('h1')).toContainText('DeepRead')

    // 2. Paste text
    const testText = 'This is a test document. '.repeat(50)
    await page.fill('textarea', testText)

    // 3. Select language
    await page.click('text=English')

    // 4. Submit
    await page.click('text=Continue to Preview')

    // 5. Verify preview
    await expect(page.locator('text=This is a test')).toBeVisible()

    // 6. Click a word to select start
    await page.click('text=document')

    // 7. Start reading
    await page.click('text=Start Reading')

    // 8. Verify reader mode
    await expect(page.locator('[data-testid="reader-overlay"]')).toBeVisible()

    // 9. Let it read for a bit
    await page.waitForTimeout(3000)

    // 10. Pause
    await page.keyboard.press('Space')
    await expect(page.locator('text=PAUSED')).toBeVisible()

    // 11. Adjust WPM
    await page.keyboard.press('ArrowUp')

    // 12. Resume
    await page.keyboard.press('Space')

    // 13. Rewind
    await page.keyboard.press('ArrowLeft')

    // 14. Exit
    await page.keyboard.press('Escape')

    // 15. Verify back at preview
    await expect(page.locator('text=Continue')).toBeVisible()

    // 16. Go home
    await page.click('text=Back')

    // 17. Verify session in history
    await expect(page.locator('text=Recent Sessions')).toBeVisible()

    // 18. Continue from history
    await page.click('text=Continue')

    // 19. Verify resumed (progress > 0)
    await expect(page.locator('[data-testid="progress"]')).not.toContainText('0 /')
  })

  test('handles large document', async ({ page }) => {
    await page.goto('/deepread')

    // Create 15k word document (under limit)
    const largeText = 'Word '.repeat(15000)
    await page.fill('textarea', largeText)
    await page.click('text=Continue to Preview')

    // Should work
    await expect(page.locator('text=15,000')).toBeVisible()
  })

  test('rejects oversized document', async ({ page }) => {
    await page.goto('/deepread')

    // Create 25k word document (over limit)
    const oversizedText = 'Word '.repeat(25000)
    await page.fill('textarea', oversizedText)

    // Word count should show warning
    await expect(page.locator('text=exceeds')).toBeVisible()
  })
})
````

---

## Verification Checklist

### Functionality

- [ ] Complete user flow works end-to-end
- [ ] Error boundaries catch and display errors gracefully
- [ ] Network errors show user-friendly messages
- [ ] Loading states display consistently
- [ ] Large documents work within limits

### Docker

- [ ] Backend Dockerfile builds successfully
- [ ] Frontend Dockerfile builds successfully
- [ ] docker-compose.prod.yml starts all services
- [ ] Health checks pass for all containers
- [ ] Volumes persist data correctly

### Deployment

- [ ] .env.example contains all required variables
- [ ] deploy.sh runs without errors
- [ ] Database migrations run successfully
- [ ] SSL/TLS works with Let's Encrypt
- [ ] Nginx proxies requests correctly

### Security

- [ ] No secrets in code or Dockerfiles
- [ ] Database password is configurable
- [ ] HTTPS enforced in production
- [ ] Security headers configured

---

## Final Verification

Run through this checklist before considering the project complete:

### Core Features

- [ ] Paste text creates document
- [ ] Upload .md creates document
- [ ] (Deferred) Upload .pdf creates document (see `../docs/FUTURE-PDF-UPLOAD.md`)
- [ ] Preview shows full text
- [ ] Word click sets start position
- [ ] Progress scrubber works
- [ ] Reader displays words with ORP
- [ ] Playback timing is smooth
- [ ] Ramp works correctly
- [ ] Rewind works (10s, 15s, 30s)
- [ ] WPM adjustment works
- [ ] Progress saves automatically
- [ ] Sessions resume correctly
- [ ] Recent sessions list works
- [ ] Dark theme throughout

### Production

- [ ] Docker builds work
- [ ] Migrations run
- [ ] Health checks pass
- [ ] Logs are accessible
- [ ] Backups work
- [ ] SSL works

---

## Project Complete!

You now have a fully functional RSVP speed-reading application with:

- **Backend**: FastAPI + SQLite (v1) / PostgreSQL (optional later)
- **Frontend**: React 19 + TanStack Router/Query + Tailwind
- **Features**:
  - Text/MD import (PDF deferred)
  - ORP-aligned RSVP display
  - Ramp/build-up mode
  - Time-based rewind
  - Auto-save progress
  - Session history
- **Deployment**: Docker Compose + Hetzner ready
