# Automaker Worktree Startup Guide

## Port Allocation (Verified)

| Location  | UI Port | Server Port | URL                   |
| --------- | ------- | ----------- | --------------------- |
| Main repo | 3007    | 3008        | http://localhost:3007 |
| feature-1 | 3017    | 3018        | http://localhost:3017 |
| feature-2 | 3027    | 3028        | http://localhost:3027 |

## How It Works

1. Each directory has its own `.env` file with unique ports
2. `npm run dev:web` reads `.env` from the **current directory**
3. Backend starts first (background), waits for health check
4. Frontend starts after backend is ready

## Starting Each Environment

```bash
# Main Repository (ports 3007/3008)
cd /Users/ruben/Documents/GitHub/automaker
npm run dev:web

# feature-1 Worktree (ports 3017/3018)
cd /Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1
npm run dev:web

# feature-2 Worktree (ports 3027/3028)
cd /Users/ruben/Documents/GitHub/automaker/.worktrees/feature-2
npm run dev:web
```

## Running Two Simultaneously

You can run any two environments at once - they use different ports.

**Example: Main + feature-1**

```bash
# Terminal 1: Start main repo
cd /Users/ruben/Documents/GitHub/automaker && npm run dev:web
# Opens http://localhost:3007

# Terminal 2: Start feature-1
cd /Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1 && npm run dev:web
# Opens http://localhost:3017
```

## Environment Variable Flow

```
.env file → start-automaker.sh → exports to shell → npm commands read them

PORT=3018          → Backend server binds to :3018
TEST_PORT=3017     → Vite dev server binds to :3017
VITE_SERVER_URL    → Vite proxies /api/* to backend
CORS_ORIGIN        → Backend allows requests from frontend
DATA_DIR           → Shared across all worktrees
```

## Troubleshooting

**Port conflict?** The startup script auto-detects and offers alternatives.

**Backend not starting?** Check if PORT is already in use:

```bash
lsof -i :3008  # main
lsof -i :3018  # feature-1
lsof -i :3028  # feature-2
```

**Kill a specific port:**

```bash
kill $(lsof -t -i:3018)
```
