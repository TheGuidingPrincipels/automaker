# Worktree Workflow Guide

> **A human-friendly guide to working with git worktrees in Automaker**
> Last updated: 2026-01-24

---

## What is a Worktree?

Think of a worktree as a **separate copy of your project** that lives in its own folder, connected to a specific git branch. Instead of switching branches back and forth in one folder, you have multiple folders — each one is a different branch you can work on independently.

**Benefits:**

- Work on multiple features simultaneously without conflicts
- Each feature has its own isolated environment
- No need to stash or commit before switching tasks
- AI agents work in isolation, protecting your main branch

---

## Creating a Worktree from the Kanban Board

When you create a new feature on the Kanban board, you see three work mode options:

| Work Mode   | What It Does                                                                 |
| ----------- | ---------------------------------------------------------------------------- |
| **Current** | Uses whatever worktree you already have selected (or main if none)           |
| **Auto**    | Generates a branch name like `feature/my-task-xyz123` and creates a worktree |
| **Custom**  | You type your own branch name and a worktree is created for it               |

### When you press "Create":

1. The feature is saved to `.automaker/features/{id}/feature.json`
2. If you chose "Auto" or "Custom", a worktree is immediately created
3. The worktree lives in `.worktrees/{branch-name}/` inside your project

---

## What Happens with Uncommitted Changes on Main?

**The worktree is completely separate from your main branch.**

- Your main project folder stays exactly as it was
- The new worktree is created from a **clean copy** of the base branch (usually `main` or `HEAD`)
- Any uncommitted changes in your main folder are **not affected** and **not copied** to the worktree

### Example:

```
Before creating worktree:
  /my-project/src/app.ts → Has uncommitted changes

After creating worktree for "new-feature":
  /my-project/src/app.ts → Still has your uncommitted changes (untouched)
  /my-project/.worktrees/new-feature/src/app.ts → Clean copy from main
```

---

## How to Select and Work on a Specific Worktree

### In the Automaker UI

1. Look at the **right side panel** (Worktree Panel)
2. You'll see tabs for each worktree/branch
3. Click on a branch tab to select it
4. The panel shows:
   - Current status (uncommitted changes count)
   - Actions (commit, push, pull, open in editor/terminal)
   - Dev server logs
   - Test logs

### In the Terminal

When you start a terminal from Automaker, it opens in the **currently selected worktree directory**. You can also navigate manually:

```bash
# List all worktrees
cd /your/project
git worktree list

# Go directly to a worktree
cd .worktrees/my-feature-branch/
```

### In Your Code Editor

From the Worktree Panel, click **"Open in Editor"** on any worktree to open it in VS Code (or your configured editor).

---

## How Merging Works

When your feature is complete and you want to merge it into main:

### Step-by-Step:

1. **Go to the feature's worktree** in the panel
2. **Commit any changes** (if not already committed)
3. **Click the merge action** (or use the dropdown menu)
4. **Choose the target branch** (usually `main`)
5. The system runs `git merge {your-branch}` into `main`

### If There Are Conflicts:

- The merge stops and tells you there are conflicts
- You can create a new "conflict resolution" feature to fix them
- Or resolve them manually in the terminal:

```bash
cd /your/project  # Main project, not worktree
git status        # See conflicted files
# Edit files to resolve conflicts
git add .
git commit
```

### After Successful Merge:

- You can optionally delete the worktree and branch (cleanup option)
- The changes are now in `main`
- The feature can be marked as complete

---

## Working on Multiple Features Without Conflicts

The magic of worktrees is that each one is a **completely separate folder**:

| Feature    | Branch               | Worktree Folder                  |
| ---------- | -------------------- | -------------------------------- |
| Add login  | `feature/login`      | `.worktrees/feature-login/`      |
| Fix header | `feature/header-fix` | `.worktrees/feature-header-fix/` |
| New API    | `feature/new-api`    | `.worktrees/feature-new-api/`    |

### Key Points:

- You can have all three open in different terminal tabs
- Changes in one worktree don't affect others
- When you run a feature, the AI agent works only in that feature's worktree
- Your main project folder remains untouched

### Tips to Avoid Merge Conflicts Later:

1. **Work on different files** in different features when possible
2. **Merge frequently** to keep branches up-to-date with main
3. **Smaller, focused features** are easier to merge than big ones
4. **Pull updates from main** before merging your branch

---

## The Complete Flow (Step by Step)

```
1. CREATE FEATURE
   ├── Open Kanban board
   ├── Click "Add Feature"
   ├── Pick "Custom" work mode
   ├── Enter branch name "my-feature"
   └── Click Create
       → Worktree created at .worktrees/my-feature/

2. WORK ON FEATURE
   ├── Click the worktree tab for "my-feature" in right panel
   ├── Click "Open in Terminal" or "Open in Editor"
   ├── Make your changes (or let the AI agent do it)
   └── Changes are isolated to this worktree only

3. COMMIT & PUSH
   ├── Use the Commit button in the panel (or git commit in terminal)
   ├── Push to remote with the Push button
   └── Create a PR if needed (optional)

4. MERGE INTO MAIN
   ├── Use the Merge action in the dropdown
   ├── Select "main" as target branch
   ├── Resolve any conflicts if they occur
   └── Changes are now in main!

5. CLEANUP (Optional)
   ├── Enable "Delete worktree and branch" option when merging
   ├── Or manually delete via the worktree panel
   └── Your work is preserved in main
```

---

## Directory Structure Explained

```
my-project/
├── .worktrees/                    # All worktrees live here
│   ├── feature-login/             # Worktree for login feature
│   │   ├── src/                   # Isolated copy of source
│   │   └── package.json           # Isolated copy of config
│   └── feature-api/               # Worktree for API feature
│       ├── src/
│       └── package.json
│
├── .automaker/                    # Shared config (NOT copied to worktrees)
│   ├── features/                  # All feature definitions
│   │   └── abc123/
│   │       └── feature.json
│   ├── context/                   # CLAUDE.md and other context files
│   ├── worktrees/                 # Metadata per worktree
│   │   └── feature-login/
│   │       └── worktree.json
│   └── settings.json
│
└── src/                           # Main project source (your main branch)
```

**Important:** The `.automaker/` folder is **never copied** to worktrees. Features, settings, and context files are always accessed from the main project. This prevents duplication and keeps everything in sync.

---

## Key Things to Remember

| Rule                               | Why It Matters                                                  |
| ---------------------------------- | --------------------------------------------------------------- |
| **Worktrees are isolated folders** | Changes in one don't affect others                              |
| **Main branch stays untouched**    | Creating a worktree doesn't modify main                         |
| **`.automaker/` folder is shared** | Features and settings live in main project only                 |
| **Select worktree first**          | Before running a feature, ensure the right worktree is selected |
| **Merge brings changes together**  | When ready, merge your branch into main                         |
| **Uncommitted changes are safe**   | Creating a worktree won't affect your uncommitted work          |

---

## Troubleshooting

### "Worktree not found" when running a feature

The feature has a `branchName` but no worktree exists. Solutions:

1. Create the worktree manually via the UI
2. Or the system will fall back to running in the main project

### Merge conflicts

1. Don't panic — your changes are safe
2. Either create a conflict resolution feature, or:
3. Manually resolve in terminal and commit

### Can't delete worktree

Make sure there are no:

- Open terminals in that directory
- Open editor windows for that worktree
- Running processes (dev servers, tests)

Close everything, then try again.

### Changes appearing in wrong worktree

Make sure you selected the correct worktree tab before:

- Opening terminal
- Opening editor
- Running the feature

---

## Quick Reference Commands

```bash
# List all worktrees
git worktree list

# Navigate to a worktree
cd .worktrees/my-branch/

# Create worktree manually (if needed)
git worktree add -b my-branch .worktrees/my-branch main

# Remove worktree manually
git worktree remove .worktrees/my-branch

# Force remove (if stuck)
git worktree remove .worktrees/my-branch --force
```
