# Automaker Development Worktree Setup

Manage the development worktree for dogfooding - using Automaker to develop Automaker itself.

## Overview

This command creates or updates a development worktree (`automaker-dev`) that you point Automaker to as a project, while the stable Automaker runs from main.

```
automaker/       ← Stable (Automaker.app runs here)
automaker-dev/   ← Development (Automaker points here as project)
```

## Instructions

### Step 1: Check Current State

```bash
cd /Users/ruben/Documents/GitHub/automaker
git worktree list
```

Determine if `automaker-dev` worktree exists.

### Step 2: Branch Decision

Ask the user which development branch to use:

**Options:**

1. **Create new feature branch** - For starting fresh work
   - Branch name format: `claude/feature-description` or `dev/feature-description`
2. **Use existing branch** - To continue previous work
   - List available branches with: `git branch -a | grep -E "(claude|dev)/"`
3. **Use main** - For simple improvements (not recommended for large changes)

### Step 3A: If Worktree Does NOT Exist

Create the development worktree:

```bash
cd /Users/ruben/Documents/GitHub/automaker

# For new feature branch:
git worktree add ../automaker-dev -b <branch-name>

# OR for existing branch:
git worktree add ../automaker-dev <existing-branch>

# OR tracking main:
git worktree add ../automaker-dev main
```

Then initialize the worktree:

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev

# Install dependencies (separate from main's node_modules)
npm install

# Build packages (required for server/UI)
npm run build:packages

# Create .automaker directory structure
mkdir -p .automaker/features .automaker/context .automaker/images

# Initialize categories
echo "[]" > .automaker/categories.json
```

### Step 3B: If Worktree EXISTS - Update Options

Present options to the user:

**Option A: Update from main (merge)**

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev
git fetch origin
git merge origin/main
npm install
npm run build:packages
```

**Option B: Update from main (rebase)**

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev
git fetch origin
git rebase origin/main
npm install
npm run build:packages
```

**Option C: Reset to main (destructive - loses uncommitted changes)**

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev
git fetch origin
git reset --hard origin/main
npm install
npm run build:packages
```

**Option D: Delete and recreate (fresh start)**

```bash
cd /Users/ruben/Documents/GitHub/automaker
git worktree remove ../automaker-dev --force
git worktree add ../automaker-dev -b <new-branch-name>
cd ../automaker-dev
npm install
npm run build:packages
mkdir -p .automaker/features .automaker/context .automaker/images
echo "[]" > .automaker/categories.json
```

### Step 4: Verify Setup

Run verification checks:

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev

# Check git status
echo "=== Git Status ==="
git status

# Check branch
echo "=== Current Branch ==="
git branch --show-current

# Check .automaker exists
echo "=== .automaker Structure ==="
ls -la .automaker/

# Verify build works
echo "=== Build Verification ==="
npm run build:packages 2>&1 | tail -5
```

### Step 5: Report to User

Provide a summary:

```
Development Worktree Ready
==========================

Location: /Users/ruben/Documents/GitHub/automaker-dev
Branch:   <branch-name>
Status:   Ready for development

Next Steps:
1. Launch Automaker.app (from Desktop)
2. In Automaker UI, open project: /Users/ruben/Documents/GitHub/automaker-dev
3. Create features for Automaker improvements
4. Agent will work in automaker-dev/.worktrees/ (isolated)

Testing Changes:
1. Stop Automaker.app
2. cd /Users/ruben/Documents/GitHub/automaker-dev
3. npm run dev:electron (or npm run dev:web)
4. Test your changes
5. If good, merge to main

Merging to Main:
1. cd /Users/ruben/Documents/GitHub/automaker
2. git merge <branch-name>
3. Restart Automaker.app to pick up changes
```

## Testing in Development Worktree

When ready to test changes:

```bash
# Stop the stable Automaker.app first!

cd /Users/ruben/Documents/GitHub/automaker-dev

# Run on DIFFERENT ports to avoid conflicts
PORT=3028 TEST_PORT=3027 npm run dev:electron

# Or for web mode:
PORT=3028 TEST_PORT=3027 npm run dev:web
```

## Merging Workflow

When features are complete and tested:

```bash
# 1. Commit all changes in dev worktree
cd /Users/ruben/Documents/GitHub/automaker-dev
git add .
git commit -m "feat: description of improvements"

# 2. Switch to main and merge
cd /Users/ruben/Documents/GitHub/automaker
git checkout main
git merge <branch-name>

# 3. Push to origin
git push origin main

# 4. Restart Automaker.app to use new code
```

## Cleaning Up

After merging, optionally clean up:

```bash
cd /Users/ruben/Documents/GitHub/automaker

# Remove worktree but keep branch
git worktree remove ../automaker-dev

# Or remove worktree and delete branch
git worktree remove ../automaker-dev
git branch -d <branch-name>
```

## Port Reference

| Instance               | UI Port | Server Port | Purpose         |
| ---------------------- | ------- | ----------- | --------------- |
| Stable (Automaker.app) | 3017    | 3018        | Daily use       |
| Dev worktree testing   | 3027    | 3028        | Testing changes |
| Docker (if used)       | 3007    | 3008        | Container       |

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
rm -rf node_modules package-lock.json
npm install
```

### Build fails after update

```bash
npm run build:packages  # Must build packages first
npm run build           # Then build apps
```
