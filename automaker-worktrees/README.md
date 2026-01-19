# AutoMaker Worktrees

This directory contains Git worktrees for parallel development on the AutoMaker fork.

## Purpose

Each worktree is an isolated checkout of a feature branch, allowing multiple developers (including Claude) to work on different features simultaneously without conflicts.

## Structure

```
automaker-worktrees/
├── README.md              # This file
├── feature-auth/          # Example: auth feature worktree
├── fix-performance/       # Example: performance fix worktree
└── claude-refactor-api/   # Example: Claude working on API refactor
```

## Rules

1. **Never commit directly to main** - Always use feature branches
2. **One worktree per feature** - Don't mix work
3. **Clean up when done** - Remove worktrees after PR is merged
4. **Use descriptive names** - `feature-`, `fix-`, `claude-` prefixes

## Commands

```bash
# Create a worktree for a new feature
cd /Users/ruben/Documents/GitHub/Coding-Dream-System/automaker
git worktree add ../automaker-worktrees/feature-name -b feature/feature-name

# List all worktrees
git worktree list

# Remove a worktree (after PR merged)
git worktree remove ../automaker-worktrees/feature-name

# Prune stale worktrees
git worktree prune
```

## Note

This directory is gitignored - worktrees are local development artifacts and should not be committed.
