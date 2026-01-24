# Sync Development Worktree

Synchronize automaker (main) and automaker-dev (dev/improvements) ensuring no work is lost.

## Purpose

Commits all uncommitted changes, merges dev into main, pushes to remote, and syncs both repos.

```
automaker-dev (dev/improvements)
        │
        │ 1. Commit uncommitted changes
        │ 2. Merge to main
        ▼
automaker (main)
        │
        │ 3. Push to remote
        │ 4. Sync dev back
        ▼
Both repos synced at same commit
```

## Default Workflow

This command ALWAYS:

1. Commits any uncommitted changes in dev (never leaves work behind)
2. Commits any uncommitted changes in main
3. Merges dev/improvements into main
4. Pushes main to remote
5. Syncs dev back from main

## Instructions

### Step 1: Check Status of Both Repos

```bash
echo "=== Main Repo (automaker) ==="
cd /Users/ruben/Documents/GitHub/automaker
git fetch origin
git status --short
echo "Branch: $(git branch --show-current)"
echo "Commit: $(git rev-parse --short HEAD)"
echo "Message: $(git log --oneline -1)"

echo ""
echo "=== Dev Worktree (automaker-dev) ==="
cd /Users/ruben/Documents/GitHub/automaker-dev
git fetch origin
git status --short
echo "Branch: $(git branch --show-current)"
echo "Commit: $(git rev-parse --short HEAD)"
echo "Message: $(git log --oneline -1)"

echo ""
echo "=== Pre-Sync Safety Check ==="
echo "Commits in dev not yet in main:"
cd /Users/ruben/Documents/GitHub/automaker
git log main..dev/improvements --oneline 2>/dev/null || echo "(none)"
echo ""
echo "Stashes in main repo:"
git stash list | head -3 || echo "(none)"
echo "Stashes in dev repo:"
cd /Users/ruben/Documents/GitHub/automaker-dev
git stash list | head -3 || echo "(none)"
```

**CRITICAL**: Review the "Commits in dev not yet in main" list. ALL of these commits MUST appear in main after the sync completes. If any stashes exist, verify they don't contain important uncommitted work before proceeding.

### Step 2: Commit Uncommitted Changes in Main

If main repo has uncommitted changes:

1. Review the changes with `git diff`
2. Create an appropriate commit message based on the changes
3. Commit:

```bash
cd /Users/ruben/Documents/GitHub/automaker
git add -A
git commit -m "commit message here

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

### Step 3: Commit Uncommitted Changes in Dev

If dev worktree has uncommitted changes:

1. Review the changes with `git diff --stat` and examine key files
2. Create an appropriate commit message describing the work
3. Commit:

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev
git add -A
git commit -m "commit message here

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

**Important:** Always commit dev changes - never stash or discard. The goal is to preserve all work.

### Step 4: Sync Main from Remote (if behind)

Check if main is behind origin:

```bash
cd /Users/ruben/Documents/GitHub/automaker
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo "0")
if [ "$BEHIND" -gt 0 ]; then
  echo "Main is $BEHIND commits behind origin, pulling..."
  git pull origin main
fi
```

### Step 5: Merge Dev into Main

```bash
cd /Users/ruben/Documents/GitHub/automaker
git merge dev/improvements
```

If there are merge conflicts:

1. Show the conflicting files
2. Resolve conflicts (prefer dev changes unless there's a reason not to)
3. Complete the merge

### Step 6: Push Both Branches to Remote

Push dev FIRST (backup), then main:

```bash
# Push dev branch as backup (in case merge fails later)
cd /Users/ruben/Documents/GitHub/automaker-dev
git push origin dev/improvements

# Push main
cd /Users/ruben/Documents/GitHub/automaker
git push origin main
```

**Why push dev first?** If something goes wrong after merging but before pushing main, the dev commits are already safely on the remote.

### Step 7: Sync Dev Back from Main

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev
git merge origin/main
```

### Step 8: Final Verification

Run comprehensive verification to ensure NO commits were left behind:

```bash
echo "=== Final Sync Status ==="
cd /Users/ruben/Documents/GitHub/automaker
MAIN_COMMIT=$(git rev-parse HEAD)
MAIN_SHORT=$(git rev-parse --short HEAD)
MAIN_MSG=$(git log --oneline -1)

cd /Users/ruben/Documents/GitHub/automaker-dev
DEV_COMMIT=$(git rev-parse HEAD)
DEV_SHORT=$(git rev-parse --short HEAD)
DEV_MSG=$(git log --oneline -1)

echo ""
if [ "$MAIN_COMMIT" = "$DEV_COMMIT" ]; then
  echo "✅ SYNCED: Both repos at commit $MAIN_SHORT"
else
  echo "⚠️ Repos at different commits:"
  echo "   Main: $MAIN_SHORT"
  echo "   Dev:  $DEV_SHORT"
fi

echo ""
echo "=== Orphan Check ==="
echo "Commits in dev NOT in main (should be empty):"
cd /Users/ruben/Documents/GitHub/automaker
git log main..dev/improvements --oneline 2>/dev/null || echo "(none - ✅)"

echo ""
echo "Commits in main NOT in dev (should be empty):"
cd /Users/ruben/Documents/GitHub/automaker-dev
git log dev/improvements..origin/main --oneline 2>/dev/null || echo "(none - ✅)"

echo ""
echo "=== Remote Sync ==="
cd /Users/ruben/Documents/GitHub/automaker
echo "Main behind origin: $(git rev-list --count HEAD..origin/main) (should be 0)"
echo "Main ahead of origin: $(git rev-list --count origin/main..HEAD) (should be 0)"
cd /Users/ruben/Documents/GitHub/automaker-dev
echo "Dev behind origin: $(git rev-list --count HEAD..origin/dev/improvements) (should be 0)"
echo "Dev ahead of origin: $(git rev-list --count origin/dev/improvements..HEAD) (should be 0)"

echo ""
echo "=== Uncommitted Work Check ==="
cd /Users/ruben/Documents/GitHub/automaker
MAIN_DIRTY=$(git status --short | wc -l | tr -d ' ')
cd /Users/ruben/Documents/GitHub/automaker-dev
DEV_DIRTY=$(git status --short | wc -l | tr -d ' ')
if [ "$MAIN_DIRTY" = "0" ] && [ "$DEV_DIRTY" = "0" ]; then
  echo "✅ No uncommitted changes in either repo"
else
  echo "⚠️ Uncommitted changes exist (main: $MAIN_DIRTY files, dev: $DEV_DIRTY files)"
fi
```

**CRITICAL**: If ANY of these checks show warnings, DO NOT proceed. Investigate and resolve before considering the sync complete.

### Step 9: Report to User

Provide a summary table:

```
Sync Complete
=============
| Repo                 | Commit     | Message              |
|----------------------|------------|----------------------|
| Main (automaker)     | [commit]   | [message]            |
| Dev (automaker-dev)  | [commit]   | [message]            |

Status: ✅ Synced

Actions taken:
1. [List commits created]
2. [List merges performed]
3. Pushed main to origin
4. Synced dev from main

Both repositories are ready for development.
```

## Edge Cases

### Main Has Commits Dev Doesn't

If main was updated directly (not through this workflow):

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev
git merge origin/main
# Then continue with normal workflow
```

### Merge Conflicts

If conflicts occur during merge:

1. List conflicting files
2. For each file, examine both versions
3. Resolve preferring the most complete/recent work
4. Stage resolved files and complete merge
5. Continue with push and sync

### Dev Has No Changes

If dev has no uncommitted changes and is already synced with main:

- Report "Already synced, no action needed"
- Still verify both repos are at same commit

## Safety Guarantees

- ✅ All uncommitted work is committed (never lost)
- ✅ All commits are pushed to remote (backed up)
- ✅ Both repos end at the same commit (synced)
- ✅ Dev branch always has all main changes
- ✅ Dev branch pushed BEFORE main merge (double backup)
- ✅ Pre-sync orphan check prevents silent commit loss
- ✅ Post-sync verification confirms zero orphaned commits
- ✅ Stash check warns about potentially forgotten work

## Quick Reference

```
/sync-dev workflow:
1. Pre-check (orphans, stashes) → 2. Commit dev → 3. Commit main → 4. Merge dev→main → 5. Push dev+main → 6. Sync dev → 7. Verify (zero orphans)
```

## Never Leave Commits Behind Checklist

Before marking sync complete, ALL must be true:

- [ ] `git log main..dev/improvements` shows NO commits
- [ ] `git log dev/improvements..origin/main` shows NO commits
- [ ] Main behind origin: 0
- [ ] Main ahead of origin: 0
- [ ] Dev behind origin: 0
- [ ] Dev ahead of origin: 0
- [ ] No uncommitted changes in either repo
- [ ] Stashes reviewed (if any exist)
