# Worktree System Reference

Quick reference for Automaker's git worktree management. Use this to understand worktree creation, navigation, and merge flows.

---

## Core Concepts

| Term         | Definition                                                      |
| ------------ | --------------------------------------------------------------- |
| **Worktree** | Isolated git working directory per branch                       |
| **Location** | `{project}/.worktrees/{branch-name}/`                           |
| **Config**   | `.automaker/` stays in main project (never copied to worktrees) |
| **Metadata** | `.automaker/worktrees/{branch}/worktree.json`                   |

---

## API Endpoints

| Endpoint                  | Method | Purpose                    |
| ------------------------- | ------ | -------------------------- |
| `/worktree/create`        | POST   | Create worktree for branch |
| `/worktree/merge`         | POST   | Merge branch into target   |
| `/worktree/delete`        | POST   | Remove worktree            |
| `/worktree/list`          | GET    | List all worktrees         |
| `/worktree/status`        | GET    | Git status of worktree     |
| `/worktree/commit`        | POST   | Commit changes             |
| `/worktree/push`          | POST   | Push to remote             |
| `/worktree/pull`          | POST   | Pull from remote           |
| `/worktree/create-pr`     | POST   | Create PR from worktree    |
| `/worktree/switch-branch` | POST   | Switch to different branch |

---

## Key Files

| Purpose             | Location                                                  |
| ------------------- | --------------------------------------------------------- |
| Worktree API Router | `apps/server/src/routes/worktree/index.ts`                |
| Create Route        | `apps/server/src/routes/worktree/routes/create.ts`        |
| Merge Route         | `apps/server/src/routes/worktree/routes/merge.ts`         |
| Delete Route        | `apps/server/src/routes/worktree/routes/delete.ts`        |
| Metadata Util       | `apps/server/src/lib/worktree-metadata.ts`                |
| UI Panel            | `apps/ui/src/components/views/board-view/worktree-panel/` |
| UI Hook             | `apps/ui/src/hooks/queries/use-worktrees.ts`              |
| Feature Execution   | `apps/server/src/services/auto-mode-service.ts`           |
| Git Utils           | `libs/git-utils/src/`                                     |

---

## Feature → Worktree Mapping

```typescript
// Feature has optional branchName
interface Feature {
  id: string;
  branchName?: string; // Links to worktree
}

// Execution flow in AutoModeService.executeFeature():
// 1. Load feature.branchName
// 2. Find worktree via `git worktree list --porcelain`
// 3. Execute AI agent in worktree path (or main if not found)
```

---

## Worktree Creation Flow

```
UI: User selects work mode (current/auto/custom)
  → api.worktree.create({ projectPath, branchName, baseBranch })
  → POST /worktree/create
  → Git: `git worktree add -b {branch} .worktrees/{name} {base}`
  → Save metadata to .automaker/worktrees/{branch}/worktree.json
  → Track in .automaker/.worktrees-branches.json
```

**Work Modes:**
| Mode | Behavior |
|------|----------|
| `current` | Uses selected worktree's branch |
| `auto` | Generates `feature/{title}-{random}` |
| `custom` | Uses user-provided branch name |

---

## Merge Flow

```
UI: User clicks Merge action
  → POST /worktree/merge { branchName, targetBranch, worktreePath, options }
  → Git: `git merge {branchName}` (or --squash)
  → On conflict: Returns 409, hasConflicts: true
  → On success: Optionally delete worktree + branch
```

**Merge Options:**

```typescript
{
  squash?: boolean;           // Squash commits
  message?: string;           // Custom commit message
  deleteWorktreeAndBranch?: boolean;  // Cleanup after merge
}
```

---

## Directory Structure

```
project/
├── .worktrees/                    # All worktrees
│   ├── feature-login/             # One worktree per branch
│   └── bugfix-header/
├── .automaker/                    # Shared config (NOT in worktrees)
│   ├── features/                  # Feature definitions
│   ├── context/                   # CLAUDE.md, etc.
│   ├── worktrees/                 # Metadata per branch
│   │   └── {branch}/worktree.json
│   └── .worktrees-branches.json   # Branch tracking
└── src/                           # Main project files
```

---

## Git Commands Used

| Operation    | Command                                      |
| ------------ | -------------------------------------------- |
| List         | `git worktree list --porcelain`              |
| Create       | `git worktree add -b {branch} {path} {base}` |
| Remove       | `git worktree remove {path} --force`         |
| Merge        | `git merge {branch}`                         |
| Squash Merge | `git merge --squash {branch}`                |

---

## Worktree Metadata Schema

```typescript
interface WorktreeMetadata {
  branch: string;
  createdAt: string;
  pr?: {
    number: number;
    url: string;
    state: string;
    mergeable: boolean;
  };
  initScriptRan?: boolean;
  initScriptStatus?: 'running' | 'success' | 'failed';
  initScriptError?: string;
}
```

---

## Execution Context

| Aspect            | Source                                 |
| ----------------- | -------------------------------------- |
| Working directory | Worktree path (fallback: project root) |
| Context files     | `.automaker/context/` in main project  |
| Feature data      | `.automaker/features/` in main project |
| Code changes      | Written to worktree directory          |

---

## UI Navigation

| Element          | Location      | Action                           |
| ---------------- | ------------- | -------------------------------- |
| Worktree Panel   | Right sidebar | Shows all worktrees as tabs      |
| Tab Click        | Panel header  | Select/switch worktree           |
| Actions Dropdown | Tab menu      | Commit, push, merge, open editor |
| Branch Switcher  | Panel         | Change branches                  |

---

## Terminal Navigation

```bash
# From Automaker UI: Opens in selected worktree dir

# Manual navigation:
cd .worktrees/{branch-name}/

# List all worktrees:
git worktree list
```

---

## Common Patterns

**Find worktree for feature:**

```typescript
// In AutoModeService
const worktrees = execSync('git worktree list --porcelain').toString();
const worktreePath = parseWorktreeForBranch(worktrees, feature.branchName);
```

**Create worktree API call:**

```typescript
await api.worktree.create({
  projectPath: '/path/to/project',
  branchName: 'feature/my-feature',
  baseBranch: 'main', // optional, defaults to HEAD
});
```

**Merge worktree API call:**

```typescript
await api.worktree.merge({
  projectPath: '/path/to/project',
  branchName: 'feature/my-feature',
  worktreePath: '/path/to/project/.worktrees/feature-my-feature',
  targetBranch: 'main',
  options: { deleteWorktreeAndBranch: true },
});
```
