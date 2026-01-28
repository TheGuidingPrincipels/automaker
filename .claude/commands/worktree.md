# Worktree Configuration

Port allocation and setup guide for git worktrees in Automaker.

## Port Allocation Table

| Location      | UI Port | Server Port | Access URL            |
| ------------- | ------- | ----------- | --------------------- |
| **Main repo** | 3007    | 3008        | http://localhost:3007 |
| **feature-1** | 3017    | 3018        | http://localhost:3017 |
| **feature-2** | 3027    | 3028        | http://localhost:3027 |

## Worktree Paths

```
/Users/ruben/Documents/GitHub/automaker/               # Main repo
/Users/ruben/Documents/GitHub/automaker/.worktrees/
├── feature-1/                                         # Worktree 1
└── feature-2/                                         # Worktree 2
```

## .env Configuration

Each worktree has a `.env` file with pre-configured ports:

```bash
# Example: feature-1 worktree (.worktrees/feature-1/.env)
PORT=3018              # Backend server
TEST_PORT=3017         # Frontend dev server
TEST_SERVER_PORT=3018  # Vite proxy target
VITE_SERVER_URL=http://localhost:3018
CORS_ORIGIN=http://localhost:3017
DATA_DIR=/Users/ruben/Documents/GitHub/automaker/data
```

## Running Commands

### Start WebUI from Worktree

```bash
cd /Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1
npm run dev:web
# Opens at http://localhost:3017 (NOT 3007!)
```

### Run E2E Tests

```bash
cd /Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1
npm run test
# Uses ports 3017/3018 automatically
```

### Run Unit Tests (Safe in Parallel)

```bash
npm run test:server   # No port conflicts - uses mocks
npm run test:packages # No port conflicts - uses mocks
```

## Creating New Worktrees

1. Create the worktree:

```bash
cd /Users/ruben/Documents/GitHub/automaker
git worktree add .worktrees/feature-3 -b feature-3
```

2. Add `.env` with next port range (+10 increment):

```bash
# .worktrees/feature-3/.env
PORT=3038
TEST_PORT=3037
TEST_SERVER_PORT=3038
VITE_SERVER_URL=http://localhost:3038
CORS_ORIGIN=http://localhost:3037
DATA_DIR=/Users/ruben/Documents/GitHub/automaker/data
```

## Simultaneous Operation Rules

| Operation     | Parallel Safe?   | Notes                        |
| ------------- | ---------------- | ---------------------------- |
| WebUI         | Yes              | Different ports per worktree |
| Unit tests    | Yes              | Use mocks, no ports          |
| E2E tests     | One per worktree | Each uses its own ports      |
| Settings/Data | Careful          | Shared via DATA_DIR          |

## Agent Instructions

When working in a worktree:

1. **Use `npm run dev:web`** (not `npm run dev`) to respect `.env` ports
2. **Note the actual port** in output (3017/3027, not 3007)
3. **Run tests normally** - `.env` handles port configuration
4. **Never hardcode ports** - always use environment variables

## Troubleshooting

### Port Already in Use

Check what's using the port:

```bash
lsof -i :3017
```

Kill the process or use a different worktree.

### Wrong Port in Browser

If the UI opens on wrong port:

1. Check `.env` file exists in worktree
2. Verify `TEST_PORT` is set correctly
3. Restart the dev server

### Data Not Synced

All worktrees share `DATA_DIR`. If settings seem out of sync:

1. Check `DATA_DIR` points to main repo's `data/`
2. Don't run concurrent writes to settings
