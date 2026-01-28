# Environment Variables

Complete reference for Automaker environment variables.

## API Keys

| Variable            | Purpose                   | Required                          |
| ------------------- | ------------------------- | --------------------------------- |
| `ANTHROPIC_API_KEY` | Claude API authentication | Yes (or use Claude Code CLI auth) |

## Server Configuration

| Variable      | Default     | Purpose                                |
| ------------- | ----------- | -------------------------------------- |
| `HOST`        | `0.0.0.0`   | Host to bind server to                 |
| `HOSTNAME`    | `localhost` | Hostname for user-facing URLs          |
| `PORT`        | `3008`      | Backend server port                    |
| `CORS_ORIGIN` | -           | Allowed CORS origins (comma-separated) |

## Data Storage

| Variable                 | Default         | Purpose                                        |
| ------------------------ | --------------- | ---------------------------------------------- |
| `DATA_DIR`               | `./data`        | Global data storage directory                  |
| `TEAM_DATA_DIR`          | `DATA_DIR/team` | Shared team data for SYSTEMS feature           |
| `ALLOWED_ROOT_DIRECTORY` | -               | Restrict file operations to specific directory |

## Frontend Configuration

| Variable           | Default     | Purpose                               |
| ------------------ | ----------- | ------------------------------------- |
| `VITE_HOSTNAME`    | `localhost` | Hostname for frontend API URLs        |
| `TEST_PORT`        | `3007`      | Frontend/Vite dev server port         |
| `TEST_SERVER_PORT` | `3008`      | Backend port for Vite proxy           |
| `VITE_SERVER_URL`  | -           | Explicit server URL (overrides proxy) |

## Knowledge Library (AI Library)

| Variable                     | Default                 | Purpose                    |
| ---------------------------- | ----------------------- | -------------------------- |
| `VITE_KNOWLEDGE_LIBRARY_API` | `http://localhost:8002` | AI Library backend API URL |

## Development & Testing

| Variable                     | Default | Purpose                                    |
| ---------------------------- | ------- | ------------------------------------------ |
| `AUTOMAKER_MOCK_AGENT`       | `false` | Enable mock agent mode for CI testing      |
| `AUTOMAKER_AUTO_LOGIN`       | `false` | Skip login prompt (disabled in production) |
| `LOG_LEVEL`                  | -       | Logger verbosity                           |
| `AUTOMAKER_DEBUG_RAW_OUTPUT` | `false` | Save raw agent output for debugging        |

## Worktree-Specific Configuration

Each worktree needs its own `.env` file with unique ports:

```bash
# .worktrees/feature-1/.env
PORT=3018
TEST_PORT=3017
TEST_SERVER_PORT=3018
VITE_SERVER_URL=http://localhost:3018
CORS_ORIGIN=http://localhost:3017
DATA_DIR=/Users/ruben/Documents/GitHub/automaker/data
```

## Port Ranges by Worktree

| Worktree  | UI Port | Server Port |
| --------- | ------- | ----------- |
| Main repo | 3007    | 3008        |
| feature-1 | 3017    | 3018        |
| feature-2 | 3027    | 3028        |
| feature-3 | 3037    | 3038        |

## Usage Examples

### Development

```bash
# Standard development
npm run dev:web

# With custom ports
PORT=3018 TEST_PORT=3017 npm run dev:web

# With debug output
AUTOMAKER_DEBUG_RAW_OUTPUT=true npm run dev:web
```

### Testing

```bash
# Mock agent for CI
AUTOMAKER_MOCK_AGENT=true npm run test

# Verbose logging
LOG_LEVEL=debug npm run test:server
```

### Production

```bash
# Typical production setup
HOST=0.0.0.0 \
PORT=3008 \
DATA_DIR=/var/data/automaker \
CORS_ORIGIN=https://myapp.com \
npm start
```
