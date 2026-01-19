# Multi-Developer Workflow Guide

This guide covers how multiple developers (including Claude) work on the AutoMaker fork simultaneously without conflicts.

---

## Quick Reference

| Action | Command |
|--------|---------|
| Start new feature | `git worktree add ../automaker-worktrees/feature-x -b feature/x` |
| List worktrees | `git worktree list` |
| Create PR (safe) | `gh pr create --repo TheGuidingPrincipels/automaker --base main` |
| Remove worktree | `git worktree remove ../automaker-worktrees/feature-x` |
| Sync with main | `git fetch origin && git rebase origin/main` |

---

## Core Principles

1. **Never push to upstream** - Push disabled as safety measure
2. **Never commit directly to main** - Always use feature branches
3. **One worktree per feature** - Isolation prevents conflicts
4. **PRs stay in our fork** - Always use `--repo` flag

---

## Directory Structure

```
/Users/ruben/Documents/GitHub/Coding-Dream-System/
├── automaker/                    # Main repo (stay on main branch)
│   ├── .automaker-fork/          # Fork tracking infrastructure
│   ├── CLAUDE.md                 # Claude instructions
│   └── ...
└── automaker-worktrees/          # Parallel development
    ├── feature-auth/             # Developer A
    ├── feature-dashboard/        # Developer B
    └── claude-refactor-api/      # Claude
```

---

## Branch Naming Conventions

| Prefix | Use Case | Example |
|--------|----------|---------|
| `feature/` | New functionality | `feature/user-authentication` |
| `fix/` | Bug fixes | `fix/memory-leak-terminal` |
| `refactor/` | Code improvements | `refactor/api-structure` |
| `claude/` | Claude-initiated work | `claude/optimize-build` |
| `docs/` | Documentation only | `docs/api-reference` |

---

## Workflows

### Starting New Work

#### Step 1: Create Worktree

```bash
cd /Users/ruben/Documents/GitHub/Coding-Dream-System/automaker

# Create worktree with new branch
git worktree add ../automaker-worktrees/feature-name -b feature/feature-name

# Move to worktree
cd ../automaker-worktrees/feature-name
```

#### Step 2: Do Your Work

```bash
# Make changes
# ...

# Commit regularly
git add .
git commit -m "feat: description of change"
```

#### Step 3: Push and Create PR

```bash
# Push branch to origin (your fork)
git push -u origin feature/feature-name

# Create PR within YOUR fork (not upstream!)
gh pr create \
  --repo TheGuidingPrincipels/automaker \
  --base main \
  --title "feat: your feature title" \
  --body "Description of changes"
```

#### Step 4: After PR Merged

```bash
# Return to main repo
cd /Users/ruben/Documents/GitHub/Coding-Dream-System/automaker

# Remove worktree
git worktree remove ../automaker-worktrees/feature-name

# Delete branch locally
git branch -d feature/feature-name

# Update main
git checkout main
git pull origin main
```

---

### Syncing Your Branch with Main

If main has been updated while you're working:

```bash
cd ../automaker-worktrees/your-feature

# Fetch latest
git fetch origin

# Rebase on main (preferred - cleaner history)
git rebase origin/main

# Or merge (if rebase causes issues)
git merge origin/main
```

---

### Reviewing Someone Else's PR

```bash
# Fetch their branch
git fetch origin feature/their-feature

# Create a worktree to review
git worktree add ../automaker-worktrees/review-their-feature origin/feature/their-feature

# Review, test, then clean up
git worktree remove ../automaker-worktrees/review-their-feature
```

---

## Claude-Specific Workflow

When Claude works on a task:

### Before Starting

1. Check for existing worktrees: `git worktree list`
2. Create new worktree with `claude/` prefix
3. Never work directly in the main repo directory

### Naming Convention

```bash
# Claude-initiated features
git worktree add ../automaker-worktrees/claude-feature-name -b claude/feature-name

# Claude working on assigned task
git worktree add ../automaker-worktrees/claude-task-123 -b claude/task-123
```

### PR Creation (Critical)

```bash
# ALWAYS use these exact flags
gh pr create \
  --repo TheGuidingPrincipels/automaker \
  --base main \
  --title "type: description" \
  --body "$(cat <<'EOF'
## Summary
- What this PR does

## Changes
- List of changes

## Testing
- How to test

---
Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### After PR is Merged

1. Remove the worktree
2. Delete the local branch
3. Confirm cleanup with `git worktree list`

---

## Common Scenarios

### "I want to work on two features at once"

```bash
# Create two worktrees
git worktree add ../automaker-worktrees/feature-a -b feature/a
git worktree add ../automaker-worktrees/feature-b -b feature/b

# Work in either directory independently
cd ../automaker-worktrees/feature-a
# or
cd ../automaker-worktrees/feature-b
```

### "I need to switch to someone else's branch"

```bash
# Don't checkout in main - create a worktree
git worktree add ../automaker-worktrees/review-feature origin/feature/their-branch
cd ../automaker-worktrees/review-feature
```

### "My worktree is out of sync"

```bash
cd ../automaker-worktrees/your-feature
git fetch origin
git rebase origin/main

# If conflicts, resolve them, then:
git add .
git rebase --continue
```

### "I accidentally created PR to wrong repo"

```bash
# Close the PR on GitHub (or via CLI)
gh pr close <pr-number> --repo AutoMaker-Org/automaker

# Create correct PR
gh pr create --repo TheGuidingPrincipels/automaker --base main
```

### "I need to see all active work"

```bash
# List all worktrees
git worktree list

# List all branches
git branch -a

# List open PRs in your fork
gh pr list --repo TheGuidingPrincipels/automaker
```

---

## Safety Checklist

Before creating any PR, verify:

- [ ] Branch name follows convention (`feature/`, `fix/`, `claude/`, etc.)
- [ ] Working in a worktree, not main directory
- [ ] Using `--repo TheGuidingPrincipels/automaker` flag
- [ ] Base branch is `main`
- [ ] Not accidentally targeting upstream

---

## Git Configuration (Already Applied)

```bash
# Upstream push is disabled
upstream	https://github.com/AutoMaker-Org/automaker.git (fetch)
upstream	DISABLE (push)

# Origin points to your fork
origin	https://github.com/TheGuidingPrincipels/automaker.git (fetch)
origin	https://github.com/TheGuidingPrincipels/automaker.git (push)
```

---

## Troubleshooting

### "fatal: 'origin/branch' is not a commit"

```bash
git fetch origin
# Then retry your command
```

### "worktree already exists"

```bash
# List worktrees
git worktree list

# Remove if stale
git worktree remove ../automaker-worktrees/stale-worktree

# Or prune all stale
git worktree prune
```

### "cannot create worktree, branch already exists"

```bash
# Use existing branch (without -b flag)
git worktree add ../automaker-worktrees/feature-name feature/feature-name
```

### "gh pr create targets wrong repo"

Always use the full command with `--repo`:
```bash
gh pr create --repo TheGuidingPrincipels/automaker --base main
```

---

*Last updated: 2026-01-18*
