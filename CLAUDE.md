# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project Overview

Automaker is an autonomous AI development studio (npm workspace monorepo). AI agents implement features in isolated git worktrees via a Kanban UI.

## Monorepo Structure

```
automaker/
├── apps/
│   ├── ui/           # React + Vite + Electron (port 3007)
│   └── server/       # Express + WebSocket (port 3008)
├── libs/             # Shared packages (@automaker/*)
│   ├── types/        # TypeScript definitions (no deps)
│   ├── utils/        # Logging, errors, context loading
│   ├── prompts/      # AI prompt templates
│   ├── platform/     # Paths, security, process spawning
│   ├── model-resolver/    # Claude model aliases
│   ├── dependency-resolver/  # Feature ordering
│   └── git-utils/    # Git & worktree operations
└── 2.ai-library/     # Knowledge Library Python backend
```

**Package dependency chain** (can only depend on packages above):

```
@automaker/types → utils, prompts, platform, model-resolver, dependency-resolver → git-utils → server, ui
```

**Key technologies**: React 19, Vite 7, Electron 39, Express 5, Claude Agent SDK, Playwright, Vitest

## Import Conventions (CRITICAL)

Always import from shared packages:

```typescript
import type { Feature } from '@automaker/types';
import { createLogger } from '@automaker/utils';
import { getFeatureDir } from '@automaker/platform';
import { resolveModelString } from '@automaker/model-resolver';
```

Never import from old paths like `../services/` or `../lib/`.

## Key Patterns

- **Event-driven**: Server emits events via WebSocket to frontend
- **Worktree isolation**: Features execute in isolated git worktrees
- **Context files**: Rules in `.automaker/context/` loaded into agent prompts
- **Model aliases**: `haiku`/`sonnet`/`opus` → full model IDs

## Fork Safety (CRITICAL)

This is a **fork** of AutoMaker-Org/automaker.

- **origin** = TheGuidingPrincipels/automaker (push here)
- **upstream** = AutoMaker-Org/automaker (READ ONLY - never push)
- Always use `--repo TheGuidingPrincipels/automaker` for PRs
- Use `/sync` command for all git sync operations

## Common Commands

```bash
npm run dev:web          # Web mode (localhost:3007)
npm run test             # E2E tests (Playwright)
npm run test:server      # Unit tests (Vitest)
npm run build:packages   # Build shared packages first
```

## Slash Commands

**Full guide**: See `.commands.md` in repo root for complete reference with decision flowchart.

| Command            | When to Use                        |
| ------------------ | ---------------------------------- |
| `/automaker-arch`  | Starting any feature work          |
| `/worktree`        | Port issues, parallel development  |
| `/new-feature`     | Building a new major feature       |
| `/test-guide`      | Running tests, debugging failures  |
| `/ai-library-api`  | Knowledge Library backend          |
| `/ai-library-ui`   | Knowledge Library frontend         |
| `/session-cleanup` | Session cleanup workflow           |
| `/commands-meta`   | Creating/updating commands         |
| `/execute-plan`    | Generate prompt for plan execution |
