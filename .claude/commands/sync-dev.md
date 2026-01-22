# Sync Development Worktree

Synchronize automaker (main) and automaker-dev (dev/improvements) to ensure both are aligned before starting new work.

## Purpose

Ensures no commits are lost and both repositories are in sync before development.

```
automaker (main) ←────────→ automaker-dev (dev/improvements)
                  bidirectional sync
```

## Instructions

### Step 1: Check Status of Both Repos

```bash
echo "=== Main Repo (automaker) ==="
cd /Users/ruben/Documents/GitHub/automaker
git fetch origin
git status --short
MAIN_COMMIT=$(git rev-parse HEAD)
MAIN_BRANCH=$(git branch --show-current)
echo "Branch: $MAIN_BRANCH"
echo "Commit: $MAIN_COMMIT"
echo "Message: $(git log --oneline -1)"

echo ""
echo "=== Dev Worktree (automaker-dev) ==="
cd /Users/ruben/Documents/GitHub/automaker-dev
git status --short
DEV_COMMIT=$(git rev-parse HEAD)
DEV_BRANCH=$(git branch --show-current)
echo "Branch: $DEV_BRANCH"
echo "Commit: $DEV_COMMIT"
echo "Message: $(git log --oneline -1)"
```

### Step 2: Check for Uncommitted Changes

**If either repo has uncommitted changes**, stop and ask the user:

Present options:

1. **Commit the changes** - Create a commit with the uncommitted work
2. **Stash the changes** - Temporarily save for later
3. **Discard the changes** - Only if user confirms (dangerous)

Do NOT proceed with sync until both repos have clean working directories.

### Step 3: Compare Commits

Check if repos are in sync:

```bash
cd /Users/ruben/Documents/GitHub/automaker

# Check if dev is ahead of main
DEV_AHEAD=$(git rev-list --count main..dev/improvements 2>/dev/null || echo "0")

# Check if main is ahead of dev
MAIN_AHEAD=$(git rev-list --count dev/improvements..main 2>/dev/null || echo "0")

echo "Dev is $DEV_AHEAD commits ahead of main"
echo "Main is $MAIN_AHEAD commits ahead of dev"
```

### Step 4: Sync Based on State

**Case A: Both in sync (DEV_AHEAD=0, MAIN_AHEAD=0)**

```
✅ Both repositories are already in sync.
No action needed.
```

**Case B: Dev is ahead of main (DEV_AHEAD > 0, MAIN_AHEAD = 0)**

Ask user: "Dev has X commits not in main. What would you like to do?"

Options:

1. **Merge dev into main** - Bring main up to date with dev's changes

   ```bash
   cd /Users/ruben/Documents/GitHub/automaker
   git merge dev/improvements
   git push origin main
   ```

2. **Keep them separate** - Dev is ahead intentionally (work in progress)

**Case C: Main is ahead of dev (MAIN_AHEAD > 0, DEV_AHEAD = 0)**

Ask user: "Main has X commits not in dev. Update dev?"

Action:

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev
git merge origin/main
npm install
npm run build:packages
```

**Case D: Both have unique commits (diverged)**

This is the critical case - both have commits the other doesn't.

Show the commits:

```bash
echo "=== Commits in dev not in main ==="
git log --oneline main..dev/improvements

echo "=== Commits in main not in dev ==="
git log --oneline dev/improvements..main
```

Ask user which approach:

1. **Merge dev into main first, then sync dev** (recommended)

   ```bash
   cd /Users/ruben/Documents/GitHub/automaker
   git merge dev/improvements
   git push origin main
   cd /Users/ruben/Documents/GitHub/automaker-dev
   git merge origin/main
   ```

2. **Merge main into dev first, then merge back**
   ```bash
   cd /Users/ruben/Documents/GitHub/automaker-dev
   git merge origin/main
   # Resolve any conflicts, test
   cd /Users/ruben/Documents/GitHub/automaker
   git merge dev/improvements
   git push origin main
   ```

### Step 5: Rebuild Dev if Updated

If dev received new commits:

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev
npm install
npm run build:packages
```

### Step 6: Final Verification

```bash
echo "=== Final Sync Status ==="
cd /Users/ruben/Documents/GitHub/automaker

MAIN_COMMIT=$(git rev-parse HEAD)
cd /Users/ruben/Documents/GitHub/automaker-dev
DEV_COMMIT=$(git rev-parse HEAD)

if [ "$MAIN_COMMIT" = "$DEV_COMMIT" ]; then
  echo "✅ SYNCED: Both repos at commit $MAIN_COMMIT"
else
  echo "⚠️  Repos are at different commits:"
  echo "   Main: $MAIN_COMMIT"
  echo "   Dev:  $DEV_COMMIT"
  echo "   This may be intentional if dev has work in progress."
fi
```

### Step 7: Report to User

```
Sync Complete
=============
Main (automaker):     [commit] [message]
Dev (automaker-dev):  [commit] [message]
Status:               ✅ Synced / ⚠️ Dev is X commits ahead (WIP)

Ready for development.
```

## Quick Sync Commands

For manual use:

```bash
# Update dev from main (most common)
cd /Users/ruben/Documents/GitHub/automaker-dev
git merge origin/main
npm install && npm run build:packages

# Merge dev work to main
cd /Users/ruben/Documents/GitHub/automaker
git merge dev/improvements
git push origin main
```

## Safety Checks

- Never sync with uncommitted changes
- Always show what will be merged before merging
- Rebuild packages after receiving new commits
- Verify sync state at the end
