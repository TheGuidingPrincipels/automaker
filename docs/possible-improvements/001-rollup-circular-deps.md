# Rollup Circular Dependency Warnings

**Status:** Deferred
**Priority:** Low
**Impact:** Build warnings only (no runtime issues)
**Date Added:** 2026-01-21
**Related Upstream:** Intentional pattern, unlikely to change

## Summary

During production builds, Rollup emits ~24 warnings about circular chunk dependencies caused by barrel file re-exports combined with TanStack Router's automatic code splitting.

## The Warning

```
Export "useClaudeUsage" of module "src/hooks/queries/use-usage.ts" was reexported
through module "src/hooks/queries/index.ts" while both modules are dependencies
of each other and will end up in different chunks by current Rollup settings.
```

## Root Cause

1. **Barrel files** (`hooks/queries/index.ts`, `hooks/mutations/index.ts`) re-export hooks from individual files for cleaner imports
2. **TanStack Router's `autoCodeSplitting: true`** splits route components into separate chunks
3. **Rollup's chunking** places barrel files and their source modules in different chunks
4. This creates circular references between chunks at the bundler level

## Why It's Not Breaking Anything

- React Query hooks are pure function definitions with no side effects
- No module initialization order dependencies
- All tests pass, app works correctly
- "Broken execution order" warning doesn't apply to stateless function exports

## Investigation Findings

- **Upstream aware?** Partially - they fixed one specific cycle but not the pattern
- **Intentional?** Yes - barrel files are documented architecture (`docs/folder-pattern.md`)
- **Fix coming from upstream?** No - no open issues or PRs about this
- **Upstream stance:** Accepting warnings as tradeoff for cleaner import syntax

## Possible Fixes

### Option A: Direct Imports (Recommended if fixing)

Change ~40 files from barrel imports to direct imports:

```typescript
// Before (causes warning)
import { useClaudeUsage } from '@/hooks/queries';

// After (no warning)
import { useClaudeUsage } from '@/hooks/queries/use-usage';
```

**Pros:** Clean fix, improves tree-shaking
**Cons:** ~40 files to change, potential merge conflicts with upstream

### Option B: Configure manualChunks

Add to `vite.config.mts`:

```typescript
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        'query-hooks': ['./src/hooks/queries/index.ts', /* ... all query files */],
        'mutation-hooks': ['./src/hooks/mutations/index.ts', /* ... all mutation files */],
      }
    }
  }
}
```

**Pros:** Single config change
**Cons:** Larger chunks, requires maintenance when adding hooks

### Option C: Suppress Warnings

Add to `vite.config.mts`:

```typescript
build: {
  rollupOptions: {
    onwarn(warning, warn) {
      if (warning.code === 'CIRCULAR_DEPENDENCY' &&
          warning.message.includes('hooks/queries/index.ts')) {
        return;
      }
      warn(warning);
    }
  }
}
```

**Pros:** Quick, non-breaking
**Cons:** Hides the warnings without fixing root cause

## Affected Files (for Option A)

### Query Imports (~29 files)

- `components/usage-popover.tsx` → `use-usage`
- `components/views/board-view/components/kanban-card/agent-info-panel.tsx` → `use-features`
- `components/views/board-view/dialogs/create-pr-dialog.tsx` → `use-worktrees`
- `components/views/board-view/worktree-panel/worktree-panel.tsx` → `use-worktrees`
- `components/views/board-view/worktree-panel/hooks/use-available-editors.ts` → `use-worktrees`
- `components/views/board-view/hooks/use-board-features.ts` → `use-features`
- `components/views/board-view/worktree-panel/hooks/use-worktrees.ts` → `use-worktrees`
- `components/ui/git-diff-panel.tsx` → `use-worktrees` + `use-git`
- ... and more (see build output for full list)

### Mutation Imports (~11 files)

- `components/views/board-view/hooks/use-board-actions.ts` → `use-auto-mode-mutations`
- `components/views/running-agents-view.tsx` → `use-auto-mode-mutations`
- `hooks/use-board-background-settings.ts` → `use-settings-mutations`
- ... and more

## Decision

**Deferred** - Not fixing now because:

1. No runtime impact - app works correctly
2. Upstream uses this pattern intentionally
3. Fixing would cause merge conflicts with upstream changes
4. Low priority compared to feature work

## When to Reconsider

- If upstream changes their import pattern
- If warnings become significantly more numerous
- If actual runtime bugs emerge from chunk ordering
- During a major refactoring effort where these files are already being modified
