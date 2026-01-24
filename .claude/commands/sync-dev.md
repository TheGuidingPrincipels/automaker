# Sync Development Worktree

Synchronize automaker (main) and automaker-dev (dev/improvements) ensuring no work is lost.

## Modes

| Command        | Mode         | Final Action                          |
| -------------- | ------------ | ------------------------------------- |
| `/sync-dev`    | Standard     | Push directly to main branch          |
| `/sync-dev:pr` | Pull Request | Create a PR for review before merging |

**Check the argument**: If `$ARGUMENTS` contains `pr` or `:pr`, use **PR Mode**. Otherwise, use **Standard Mode**.

## Purpose

Commits all uncommitted changes, merges dev into main (or creates PR), and syncs repos.

```
automaker-dev (dev/improvements)
        │
        │ 1. Commit uncommitted changes
        │ 2. Merge to main (Standard) OR Create PR (PR Mode)
        ▼
automaker (main)
        │
        │ 3. Push to remote / PR created
        │ 4. Sync dev back
        ▼
Both repos synced at same commit
```

## Workflow Summary

**Both modes do steps 1-5, then diverge:**

1. Commits any uncommitted changes in dev (never leaves work behind)
2. Commits any uncommitted changes in main
3. Syncs main from remote (if behind)
4. Pushes dev branch to remote (backup)
5. **Standard Mode**: Merge dev→main, push main, sync dev back
6. **PR Mode**: Create a PR from dev/improvements → main with summary

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

### Step 5: Push Dev Branch to Remote (Both Modes)

Push dev branch as backup before any merge operations:

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev
git push origin dev/improvements
```

**Why push dev first?** If something goes wrong during merge, the dev commits are already safely on the remote.

---

## ⚡ MODE SPLIT: Check `$ARGUMENTS` now

- If `$ARGUMENTS` contains `pr` → Go to **Step 6A (PR Mode)**
- Otherwise → Go to **Step 6B (Standard Mode)**

---

### Step 6A: PR Mode - Create Pull Request

**Skip the direct merge.** Instead, create a well-formatted PR.

#### 6A.1: Gather Commit Information

```bash
cd /Users/ruben/Documents/GitHub/automaker

echo "=== Commits to include in PR ==="
git log main..dev/improvements --oneline

echo ""
echo "=== Detailed changes ==="
git log main..dev/improvements --pretty=format:"### %s%n%n%b%n---" --no-merges

echo ""
echo "=== Files changed ==="
git diff main...dev/improvements --stat
```

#### 6A.2: Analyze and Summarize

Based on the commit history and changes, create a summary that:

- Groups related commits into logical features/improvements
- Uses simple, non-technical language where possible
- Highlights user-facing changes prominently
- Mentions technical changes briefly

#### 6A.3: Create the Pull Request

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev

gh pr create \
  --repo TheGuidingPrincipels/automaker \
  --base main \
  --head dev/improvements \
  --title "[title based on main theme of changes]" \
  --body "$(cat <<'EOF'
## Summary

[2-3 sentence overview of what this PR accomplishes]

## What's New

[Bulleted list of features/improvements, grouped logically]

### Features
- [Feature 1: brief description]
- [Feature 2: brief description]

### Improvements
- [Improvement 1]
- [Improvement 2]

### Fixes
- [Fix 1]
- [Fix 2]

## Technical Details

[Optional: Brief notes on implementation approach if relevant]

## Files Changed

[Summary of areas affected: e.g., "UI components, server routes, shared types"]

---
🤖 Synced from dev/improvements via `/sync-dev:pr`

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

**Important:** Customize the title and body based on actual changes. The template above is a guide.

#### 6A.4: Report PR to User

```
Pull Request Created
====================
URL: [PR URL from gh pr create output]
From: dev/improvements → main

Summary:
[Brief 1-2 line summary]

Changes included:
- [Key change 1]
- [Key change 2]
- [Key change 3]

Next steps:
1. Review the PR at the URL above
2. Merge when ready
3. Run /sync-dev after merging to sync dev back
```

**PR Mode complete.** The dev branch is pushed and PR is created. Skip to Step 7 for final status report.

---

### Step 6B: Standard Mode - Merge and Push

Merge dev into main and push:

```bash
cd /Users/ruben/Documents/GitHub/automaker
git merge dev/improvements
git push origin main
```

If there are merge conflicts:

1. Show the conflicting files
2. Resolve conflicts (prefer dev changes unless there's a reason not to)
3. Complete the merge
4. Push main

#### 6B.1: Sync Dev Back from Main

```bash
cd /Users/ruben/Documents/GitHub/automaker-dev
git merge origin/main
```

### Step 7: Final Verification (Standard Mode Only)

**Note:** In PR Mode, skip this step - repos won't be fully synced until PR is merged.

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

### Step 8: Report to User

#### Standard Mode Report

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

#### PR Mode Report

```
Pull Request Created
====================
URL: [PR URL]
From: dev/improvements → main

Summary:
[Brief description of changes]

What's included:
- [Feature/improvement 1]
- [Feature/improvement 2]
- [etc.]

Next steps:
1. Review the PR: [URL]
2. Merge when ready
3. Run `/sync-dev` after merging to sync dev back

Dev branch: pushed ✅
PR: created ✅
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

### Both Modes

- ✅ All uncommitted work is committed (never lost)
- ✅ Dev branch pushed to remote (backed up)
- ✅ Pre-sync orphan check prevents silent commit loss
- ✅ Stash check warns about potentially forgotten work

### Standard Mode

- ✅ Both repos end at the same commit (synced)
- ✅ Dev branch always has all main changes
- ✅ Post-sync verification confirms zero orphaned commits

### PR Mode

- ✅ Changes reviewed before merging to main
- ✅ Clear summary of all work in PR description
- ✅ Merge happens through GitHub (audit trail)

## Quick Reference

```
/sync-dev (Standard Mode):
1. Pre-check → 2. Commit main → 3. Commit dev → 4. Sync main from remote → 5. Push dev → 6B. Merge dev→main, push main, sync dev → 7. Verify → 8. Report

/sync-dev:pr (PR Mode):
1. Pre-check → 2. Commit main → 3. Commit dev → 4. Sync main from remote → 5. Push dev → 6A. Create PR → 8. Report
```

## Completion Checklists

### Standard Mode Checklist

Before marking sync complete, ALL must be true:

- [ ] `git log main..dev/improvements` shows NO commits
- [ ] `git log dev/improvements..origin/main` shows NO commits
- [ ] Main behind origin: 0
- [ ] Main ahead of origin: 0
- [ ] Dev behind origin: 0
- [ ] Dev ahead of origin: 0
- [ ] No uncommitted changes in either repo
- [ ] Stashes reviewed (if any exist)

### PR Mode Checklist

Before marking PR creation complete:

- [ ] Dev branch pushed to origin
- [ ] No uncommitted changes in dev repo
- [ ] PR created successfully
- [ ] PR URL provided to user
- [ ] PR body summarizes all changes clearly
