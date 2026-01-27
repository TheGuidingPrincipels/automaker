# Automaker Development Workflow Guide

Complete guide for developing Automaker while using Automaker itself (dogfooding).

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Initial Setup](#initial-setup)
4. [Daily Workflow](#daily-workflow)
5. [Development Modes](#development-modes)
6. [Syncing Repositories](#syncing-repositories)
7. [Testing Changes](#testing-changes)
8. [Merging to Stable](#merging-to-stable)
9. [Upstream Updates](#upstream-updates)
10. [Troubleshooting](#troubleshooting)
11. [Command Reference](#command-reference)

---

## Overview

This workflow allows you to:

- **Use Automaker** (stable version) for daily work
- **Develop Automaker** improvements simultaneously
- **Test changes** before they affect the stable version
- **Sync safely** without losing commits or changes

### Key Principle

```
All development → Test in dev → Merge to main when verified
```

---

## Architecture

### Directory Structure

```
/Users/ruben/Documents/GitHub/
│
├── automaker/                    ← STABLE (main branch)
│   ├── apps/
│   ├── libs/
│   ├── .automaker/               ← For other projects (not self-development)
│   └── Launch-Automaker.command runs FROM here (ports 3017/3018)
│
└── automaker-dev/                ← DEVELOPMENT (dev/improvements branch)
    ├── apps/
    ├── libs/
    ├── .automaker/               ← Feature tracking for Automaker improvements
    │   └── features/             ← Your improvement features
    ├── .worktrees/               ← Agent-created sub-worktrees (when using UI)
    │   └── claude-feature-x/
    └── Test changes here (ports 3027/3028)
```

### Visual Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              STABLE ZONE                                     │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  automaker/ (main branch)                                            │   │
│   │  • Launch-Automaker.command runs from here                           │   │
│   │  • Ports: 3017 (UI), 3018 (Server)                                   │   │
│   │  • Only receives TESTED, VERIFIED code                               │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    ▲                                         │
│                                    │ git merge dev/improvements              │
│                                    │ (only after testing)                    │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                             DEVELOPMENT ZONE                                 │
│                                    │                                         │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  automaker-dev/ (dev/improvements branch)                            │   │
│   │  • All development happens here                                      │   │
│   │  • Test ports: 3027 (UI), 3028 (Server)                              │   │
│   │  • Safe to experiment - doesn't affect stable                        │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│            ┌───────────────────────┼───────────────────────┐                │
│            │                       │                       │                │
│            ▼                       ▼                       ▼                │
│   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐          │
│   │ Direct editing  │   │ Automaker UI    │   │ Claude Code     │          │
│   │ (manual)        │   │ (agent creates  │   │ (assisted)      │          │
│   │                 │   │  sub-worktrees) │   │                 │          │
│   └─────────────────┘   └─────────────────┘   └─────────────────┘          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Initial Setup

### Prerequisites

- Git installed
- Node.js 22+ installed
- Launcher: `scripts/Launchers/Launch-Automaker.command` (optional Desktop shortcut)

### One-Time Setup

If not already done, create the development worktree:

```bash
# Navigate to main repo
cd /Users/ruben/Documents/GitHub/automaker

# Create development worktree
git worktree add ../automaker-dev -b dev/improvements

# Setup dev worktree
cd ../automaker-dev
npm install
npm run build:packages

# Create .automaker structure
mkdir -p .automaker/features .automaker/context .automaker/images
echo "[]" > .automaker/categories.json
```

Or simply run:

```
/dev-setup
```

---

## Daily Workflow

### Starting Your Day

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ 1. SYNC     │────▶│ 2. DEVELOP  │────▶│ 3. TEST     │
│ /sync-dev   │     │ Make changes│     │ PORT=3028   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
┌─────────────┐     ┌─────────────┐            │
│ 5. RESTART  │◀────│ 4. MERGE    │◀───────────┘
│ Automaker   │     │ to main     │     (when tests pass)
└─────────────┘     └─────────────┘
```

### Step-by-Step

**1. Sync Before Starting**

```bash
/sync-dev
```

This ensures main and dev are aligned.

**2. Develop in automaker-dev**

Option A - Using Claude Code:

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev
# Make your changes with Claude's help
```

Option B - Using Automaker UI:

```
1. Launch Automaker (stable) via `scripts/Launchers/Launch-Automaker.command`
2. Open project: /Users/ruben/Documents/GitHub/automaker-dev
3. Create features for improvements
4. Agent works in isolated sub-worktrees
```

**3. Test Your Changes**

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev
PORT=3028 TEST_PORT=3027 npm run dev:electron
```

**4. Merge When Ready**

```bash
cd /Users/ruben/Documents/GitHub/automaker
git merge dev/improvements
git push origin main
```

**5. Restart Stable**

- Stop the launcher Terminal window (`Ctrl+C`)
- Relaunch `scripts/Launchers/Launch-Automaker.command`
- New code is now active

---

## Development Modes

### Mode A: Claude Code (Direct)

Work directly in automaker-dev with Claude Code assistance.

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev

# Make changes with Claude's help
# Changes go directly to dev/improvements branch
```

**Best for:**

- Quick fixes
- Small features
- Manual code reviews
- Precise control

### Mode B: Automaker UI (Agent)

Use Automaker itself to develop features.

```
1. Launch Automaker (stable) via `scripts/Launchers/Launch-Automaker.command`
2. Open project: /Users/ruben/Documents/GitHub/automaker-dev
3. Create feature in Kanban board
4. Move to "In Progress" - agent starts
5. Agent creates sub-worktree at:
   automaker-dev/.worktrees/claude-feature-name/
6. Agent works in isolation
7. Review agent's work
8. Merge sub-worktree to dev/improvements
```

**Best for:**

- Larger features
- Autonomous AI development
- Complex multi-file changes
- When you want AI to handle implementation

### Mode C: Hybrid

Combine both modes:

1. Use Automaker UI for initial implementation
2. Use Claude Code for refinements
3. Test thoroughly
4. Merge to main

---

## Syncing Repositories

### When to Sync

- **Before starting new work** - Always sync first
- **After merging to main** - Sync dev back to main
- **Before testing** - Ensure you're testing latest code

### The /sync-dev Command

```bash
/sync-dev
```

This command:

1. Checks both repos for uncommitted changes
2. Compares commit history
3. Identifies which is ahead
4. Helps you merge safely
5. Rebuilds packages if needed

### Manual Sync Commands

**Update dev from main:**

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev
git merge origin/main
npm install
npm run build:packages
```

**Merge dev to main:**

```bash
cd /Users/ruben/Documents/GitHub/automaker
git merge dev/improvements
git push origin main
```

**Sync dev back after merge:**

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev
git merge origin/main
```

### Sync States

| State                    | Meaning                      | Action                          |
| ------------------------ | ---------------------------- | ------------------------------- |
| Both same commit         | In sync                      | Ready to work                   |
| Dev ahead                | Dev has new work             | Merge to main when ready        |
| Main ahead               | Main has commits dev doesn't | Update dev from main            |
| Both have unique commits | Diverged                     | Merge carefully (see /sync-dev) |

---

## Testing Changes

### Test Command

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev && PORT=3028 TEST_PORT=3027 npm run dev:electron
```

### Running Two Instances Simultaneously

**Yes, you CAN run both instances at the same time:**

- Stable Automaker continues running on ports 3017/3018
- Dev testing instance runs on ports 3027/3028
- No conflicts - they are completely independent

**Important notes:**

- Both instances share the same git repository (worktrees)
- Changes made in dev instance are visible in dev worktree only
- Stable instance remains unaffected until you merge

### Port Reference

| Instance             | UI Port | Server Port | Purpose         |
| -------------------- | ------- | ----------- | --------------- |
| Stable (launcher)    | 3017    | 3018        | Daily use       |
| Dev worktree testing | 3027    | 3028        | Testing changes |
| Docker (if used)     | 3007    | 3008        | Container       |

### Test Checklist

Before merging to main, verify:

- [ ] Application starts without errors
- [ ] No console errors in browser DevTools
- [ ] Key features work (create project, add feature, run agent)
- [ ] UI renders correctly
- [ ] Server responds to API calls

### Running Automated Tests

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev

# Server unit tests
npm run test:server

# All package tests
npm run test:packages

# E2E tests (headless)
npm run test

# E2E tests (with browser)
npm run test:headed
```

---

## Merging to Stable

### Pre-Merge Checklist

- [ ] All changes committed in dev
- [ ] Tests pass
- [ ] Manual testing done with PORT=3028
- [ ] No console errors

### Merge Commands

```bash
# 1. Ensure dev is clean
cd /Users/ruben/Documents/GitHub/automaker-dev
git status  # Should show "nothing to commit"

# 2. Switch to main and merge
cd /Users/ruben/Documents/GitHub/automaker
git merge dev/improvements

# 3. Push to remote
git push origin main

# 4. Sync dev back to main
cd /Users/ruben/Documents/GitHub/automaker-dev
git merge origin/main

# 5. Restart Automaker (launcher)
# Stop (Ctrl+C) and relaunch `scripts/Launchers/Launch-Automaker.command`
```

### After Merge

- Restart the launcher to use new code
- Verify stable version works
- Both repos should now be in sync

---

## Upstream Updates

Upstream updates are handled separately from the dev/main sync workflow.

### Upstream Workflow

```
┌─────────────────┐
│ 1. Check        │  Run /upstream-check
│    Upstream     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Merge to     │  In automaker-dev:
│    Dev First    │  git merge upstream/main
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. Test in      │  PORT=3028 npm run dev:electron
│    Dev          │  npm run test:all
└────────┬────────┘
         │
    Pass? ─────────────────┐
         │                 │
        YES               NO
         │                 │
         ▼                 ▼
┌─────────────────┐  ┌─────────────────┐
│ 4. Merge to     │  │ Fix issues in   │
│    Main         │  │ dev, then retry │
└─────────────────┘  └─────────────────┘
```

### Commands

```bash
# 1. Check for upstream updates
/upstream-check

# 2. Merge upstream to dev (test first)
cd /Users/ruben/Documents/GitHub/automaker-dev
git fetch upstream
git merge upstream/main
npm install
npm run build:packages

# 3. Test
PORT=3028 TEST_PORT=3027 npm run dev:electron
npm run test:all

# 4. If tests pass, merge to main
cd /Users/ruben/Documents/GitHub/automaker
git merge dev/improvements
git push origin main

# 5. Restart stable
```

---

## Troubleshooting

### "Worktree already exists"

```bash
git worktree list  # Check what exists
git worktree remove ../automaker-dev  # Remove if needed
```

### "Branch already exists"

```bash
git branch -d <branch-name>  # Delete local
# Or use a different branch name
```

### npm install fails

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev
rm -rf node_modules package-lock.json
npm install
```

### Build fails after sync

```bash
npm run build:packages  # Must build packages first
npm run build           # Then build apps
```

### Port already in use

```bash
# Find what's using the port
lsof -i :3017

# Kill the process
kill -9 <PID>

# Or use different ports
PORT=3038 TEST_PORT=3037 npm run dev:electron
```

### Merge conflicts

```bash
# See conflicting files
git status

# Open and resolve each conflict manually
# Look for <<<<<<< ======= >>>>>>> markers

# After resolving
git add .
git commit -m "Resolve merge conflicts"
```

### Dev and main are diverged

Run `/sync-dev` which will guide you through the merge process safely.

---

## Command Reference

### Claude Code Skills

| Skill             | Purpose                               |
| ----------------- | ------------------------------------- |
| `/dev-setup`      | Create or recreate the dev worktree   |
| `/sync-dev`       | Synchronize main and dev repositories |
| `/upstream-check` | Check and analyze upstream changes    |
| `/validate-build` | Build and fix any errors              |
| `/validate-tests` | Run tests and fix failures            |

### Git Commands

| Command                | Purpose                   |
| ---------------------- | ------------------------- |
| `git worktree list`    | Show all worktrees        |
| `git status`           | Check uncommitted changes |
| `git log --oneline -5` | Recent commits            |
| `git merge <branch>`   | Merge a branch            |
| `git push origin main` | Push to remote            |

### Development Commands

| Command                  | Purpose               |
| ------------------------ | --------------------- |
| `npm run dev:electron`   | Run Electron app      |
| `npm run dev:web`        | Run web version       |
| `npm run build:packages` | Build shared packages |
| `npm run test:server`    | Run server tests      |
| `npm run test:all`       | Run all tests         |

### Port Override

```bash
PORT=<server> TEST_PORT=<ui> npm run dev:electron
```

---

## Quick Reference Card

```
BEFORE WORK:     /sync-dev
DEVELOP:         cd automaker-dev && (make changes)
TEST:            PORT=3028 TEST_PORT=3027 npm run dev:electron
COMMIT:          git add . && git commit -m "message"
MERGE TO MAIN:   cd automaker && git merge dev/improvements && git push
RESTART STABLE:  Stop (Ctrl+C) & relaunch `scripts/Launchers/Launch-Automaker.command`
SYNC BACK:       cd automaker-dev && git merge origin/main

UPSTREAM:        /upstream-check → merge to dev → test → merge to main
```

---

## Safety Rules

1. **Always sync before new work** - Run `/sync-dev`
2. **Never work with uncommitted changes** - Commit or stash first
3. **Test before merging to main** - Use PORT=3028
4. **Upstream → Dev → Main** - Always test upstream changes in dev first
5. **Restart after merge** - Launcher needs restart for new code
6. **Keep dev tracking main** - Sync dev back after merging to main
