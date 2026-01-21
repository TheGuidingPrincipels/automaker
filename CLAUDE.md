# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automaker is an autonomous AI development studio built as an npm workspace monorepo. It provides a Kanban-based workflow where AI agents (powered by Claude Agent SDK) implement features in isolated git worktrees.

## Common Commands

```bash
# Development
npm run dev                 # Interactive launcher (choose web or electron)
npm run dev:web             # Web browser mode (localhost:3007)
npm run dev:electron        # Desktop app mode
npm run dev:electron:debug  # Desktop with DevTools open

# Building
npm run build               # Build web application
npm run build:packages      # Build all shared packages (required before other builds)
npm run build:electron      # Build desktop app for current platform
npm run build:server        # Build server only

# Testing
npm run test                # E2E tests (Playwright, headless)
npm run test:headed         # E2E tests with browser visible
npm run test:server         # Server unit tests (Vitest)
npm run test:packages       # All shared package tests
npm run test:all            # All tests (packages + server)

# Single test file
npm run test:server -- tests/unit/specific.test.ts

# Linting and formatting
npm run lint                # ESLint
npm run format              # Prettier write
npm run format:check        # Prettier check
```

## Architecture

### Monorepo Structure

```
automaker/
├── apps/
│   ├── ui/           # React + Vite + Electron frontend (port 3007)
│   └── server/       # Express + WebSocket backend (port 3008)
└── libs/             # Shared packages (@automaker/*)
    ├── types/        # Core TypeScript definitions (no dependencies)
    ├── utils/        # Logging, errors, image processing, context loading
    ├── prompts/      # AI prompt templates
    ├── platform/     # Path management, security, process spawning
    ├── model-resolver/    # Claude model alias resolution
    ├── dependency-resolver/  # Feature dependency ordering
    └── git-utils/    # Git operations & worktree management
```

### Package Dependency Chain

Packages can only depend on packages above them:

```
@automaker/types (no dependencies)
    ↓
@automaker/utils, @automaker/prompts, @automaker/platform, @automaker/model-resolver, @automaker/dependency-resolver
    ↓
@automaker/git-utils
    ↓
@automaker/server, @automaker/ui
```

### Key Technologies

- **Frontend**: React 19, Vite 7, Electron 39, TanStack Router, Zustand 5, Tailwind CSS 4
- **Backend**: Express 5, WebSocket (ws), Claude Agent SDK, node-pty
- **Testing**: Playwright (E2E), Vitest (unit)

### Server Architecture

The server (`apps/server/src/`) follows a modular pattern:

- `routes/` - Express route handlers organized by feature (agent, features, auto-mode, worktree, etc.)
- `services/` - Business logic (AgentService, AutoModeService, FeatureLoader, TerminalService)
- `providers/` - AI provider abstraction (currently Claude via Claude Agent SDK)
- `lib/` - Utilities (events, auth, worktree metadata)

### Frontend Architecture

The UI (`apps/ui/src/`) uses:

- `routes/` - TanStack Router file-based routing
- `components/views/` - Main view components (board, settings, terminal, etc.)
- `store/` - Zustand stores with persistence (app-store.ts, setup-store.ts)
- `hooks/` - Custom React hooks
- `lib/` - Utilities and API client

### SYSTEMS Feature (Agents, Systems, Knowledge Hub)

**Types** (`libs/types/src/`):

- `custom-agent.ts` - CustomAgent, tools, MCP servers, model config, execution
- `system.ts` - System, workflow steps, agents, execution, built-in system IDs
- `knowledge.ts` - Blueprint, KnowledgeEntry, Learning, search queries

**Team Storage** (`apps/server/src/lib/team-storage.ts`):

- File-based shared storage for multi-user deployment
- Collections: agents, systems, blueprints, knowledge-entries, learnings
- Uses `TEAM_DATA_DIR` env var (defaults to `DATA_DIR/team`)

**Routes** (`apps/ui/src/routes/`):
| File | URL | Purpose |
|------|-----|---------|
| `agents.tsx` | `/agents` | Custom agent management |
| `systems.tsx` | `/systems` | Layout with nested routes |
| `systems.index.tsx` | `/systems` | Gallery of multi-agent systems |
| `systems.$systemId.tsx` | `/systems/:id` | System detail (tabs: Overview, Agents, Workflow, Run) |
| `knowledge-hub.tsx` | `/knowledge-hub` | Layout with nested routes |
| `knowledge-hub.index.tsx` | `/knowledge-hub` | Gallery of knowledge sections |
| `knowledge-hub.$section.tsx` | `/knowledge-hub/:section` | Section detail (blueprints/knowledge-server/learning) |

**Views** (`apps/ui/src/components/views/`):

- `agents-page/` - Agent gallery, CRUD, create dialog
- `systems-page/` - System gallery with 4 built-in systems
- `system-detail-page/` - Tabbed detail view
- `knowledge-hub-page/` - Section cards (Blueprints, Knowledge Server, Learning)
- `knowledge-section-page/` - Dynamic section content

**Backend Services** (`apps/server/src/services/`):

- `custom-agents-service.ts` - CRUD + duplicate, archive, activate
- `systems-service.ts` - CRUD + run execution, 4 built-in systems
- `knowledge-service.ts` - Blueprints, entries, learnings + search

**Backend Routes** (`apps/server/src/routes/`):

- `custom-agents/index.ts` - REST API for agents
- `systems/index.ts` - REST API + `/run` endpoint
- `knowledge/index.ts` - REST API for all knowledge types + search

**Keyboard Shortcuts** (in `libs/types/src/settings.ts`):

- `Shift+A` - Open Agents page
- `Shift+Y` - Open Systems page
- `Shift+K` - Open Knowledge Hub

## Data Storage

### Per-Project Data (`.automaker/`)

```
.automaker/
├── features/              # Feature JSON files and images
│   └── {featureId}/
│       ├── feature.json
│       ├── agent-output.md
│       └── images/
├── context/               # Context files for AI agents (CLAUDE.md, etc.)
├── settings.json          # Project-specific settings
├── spec.md               # Project specification
└── analysis.json         # Project structure analysis
```

### Global Data (`DATA_DIR`, default `./data`)

```
data/
├── settings.json          # Global settings, profiles, shortcuts
├── credentials.json       # API keys
├── sessions-metadata.json # Chat session metadata
└── agent-sessions/        # Conversation histories
```

## Import Conventions

Always import from shared packages, never from old paths:

```typescript
// ✅ Correct
import type { Feature, ExecuteOptions } from '@automaker/types';
import { createLogger, classifyError } from '@automaker/utils';
import { getEnhancementPrompt } from '@automaker/prompts';
import { getFeatureDir, ensureAutomakerDir } from '@automaker/platform';
import { resolveModelString } from '@automaker/model-resolver';
import { resolveDependencies } from '@automaker/dependency-resolver';
import { getGitRepositoryDiffs } from '@automaker/git-utils';

// ❌ Never import from old paths
import { Feature } from '../services/feature-loader'; // Wrong
import { createLogger } from '../lib/logger'; // Wrong
```

## Key Patterns

### Event-Driven Architecture

All server operations emit events that stream to the frontend via WebSocket. Events are created using `createEventEmitter()` from `lib/events.ts`.

### Git Worktree Isolation

Each feature executes in an isolated git worktree, created via `@automaker/git-utils`. This protects the main branch during AI agent execution.

### Context Files

Project-specific rules are stored in `.automaker/context/` and automatically loaded into agent prompts via `loadContextFiles()` from `@automaker/utils`.

### Model Resolution

Use `resolveModelString()` from `@automaker/model-resolver` to convert model aliases:

- `haiku` → `claude-haiku-4-5`
- `sonnet` → `claude-sonnet-4-20250514`
- `opus` → `claude-opus-4-5-20251101`

## Adding New Features (IMPORTANT)

When adding **new major features**, follow the Feature-First Architecture. See `FEATURE-STRATEGY.md` for complete implementation guide.

### Quick Rules

1. **Create dedicated directories** for each new feature:

   ```
   apps/ui/src/features/{feature-name}/
   apps/server/src/features/{feature-name}/
   ```

2. **Feature structure** (both frontend and backend):

   ```
   features/{feature-name}/
   ├── components/ or routes.ts   # UI components / Express routes
   ├── hooks/ or service.ts       # React hooks / Business logic
   ├── api.ts or storage.ts       # API client / Data access
   └── index.ts                   # Public API exports
   ```

3. **Types go in shared package**: `libs/types/src/{feature}.ts`

4. **DO NOT** add feature state to global `app-store.ts` - create feature-specific stores

5. **Export through `index.ts`** - internal files are private to the feature

### Template

Use the **SYSTEMS feature** as the canonical reference:

- Types: `libs/types/src/custom-agent.ts`, `system.ts`, `knowledge.ts`
- Services: `apps/server/src/services/custom-agents-service.ts`
- Routes: `apps/server/src/routes/custom-agents/index.ts`

## Environment Variables

- `ANTHROPIC_API_KEY` - Anthropic API key (or use Claude Code CLI auth)
- `HOST` - Host to bind server to (default: 0.0.0.0)
- `HOSTNAME` - Hostname for user-facing URLs (default: localhost)
- `PORT` - Server port (default: 3008)
- `DATA_DIR` - Data storage directory (default: ./data)
- `TEAM_DATA_DIR` - Shared team data for SYSTEMS feature (default: DATA_DIR/team)
- `ALLOWED_ROOT_DIRECTORY` - Restrict file operations to specific directory
- `AUTOMAKER_MOCK_AGENT=true` - Enable mock agent mode for CI testing
- `AUTOMAKER_AUTO_LOGIN=true` - Skip login prompt in development (disabled when NODE_ENV=production)
- `VITE_HOSTNAME` - Hostname for frontend API URLs (default: localhost)

---

## Fork Workflow (CRITICAL)

This is a **heavily modified fork** of the original AutoMaker repository. Follow these rules strictly.

### Repository Context

```
Remotes:
├── origin   → github.com/TheGuidingPrincipels/automaker (YOUR fork - push here)
└── upstream → github.com/AutoMaker-Org/automaker (original - READ ONLY)

Branches:
├── main     → Your modified version (default)
└── upstream → Clean mirror of original (never modify)
```

### Safety Rules

1. **NEVER push to upstream** - Push is disabled as safety measure
2. **NEVER create PRs to upstream** - Always use `--repo` flag
3. **NEVER commit directly to main** - Use feature branches
4. **ALWAYS use worktrees** - Never work in the main repo directory

### Before Starting Any Work

```bash
# 1. Navigate to the repo
cd /Users/ruben/Documents/GitHub/Coding-Dream-System/automaker

# 2. Check existing worktrees
git worktree list

# 3. Create a new worktree for your task
git worktree add ../automaker-worktrees/claude-task-name -b claude/task-name

# 4. Work in the worktree
cd ../automaker-worktrees/claude-task-name
```

### Branch Naming for Claude

Use the `claude/` prefix for all Claude-initiated work:

| Task Type | Branch Name                   |
| --------- | ----------------------------- |
| Feature   | `claude/feature-description`  |
| Bug fix   | `claude/fix-description`      |
| Refactor  | `claude/refactor-description` |

### Creating Pull Requests (CRITICAL)

**ALWAYS use the full command with `--repo` flag:**

```bash
gh pr create \
  --repo TheGuidingPrincipels/automaker \
  --base main \
  --title "type: description" \
  --body "$(cat <<'EOF'
## Summary
- What this PR does

## Changes
- List of changes

---
Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**NEVER use:**

- `gh pr create` without `--repo` flag
- Any command that might target `AutoMaker-Org/automaker`

### After Work is Complete

```bash
# 1. Push your branch
git push -u origin claude/task-name

# 2. Create PR (with correct flags)
gh pr create --repo TheGuidingPrincipels/automaker --base main

# 3. Return to main repo
cd /Users/ruben/Documents/GitHub/Coding-Dream-System/automaker

# 4. Clean up worktree
git worktree remove ../automaker-worktrees/claude-task-name
```

### Upstream Tracking

This fork tracks upstream changes via `.automaker-fork/`:

```
.automaker-fork/
├── config.json      # Tracking configuration
├── reports/         # Upstream analysis reports
└── adopted/         # Record of adopted features
```

To check for upstream updates, run the `/upstream-check` skill or ask:
"Run an upstream check on the automaker fork"

### Related Documentation

- `WORKFLOW-GUIDE.md` - Full multi-developer workflow documentation
- `FORK-USAGE-GUIDE.md` - Simple fork management guide
- `.automaker-fork/README.md` - Tracking infrastructure details
