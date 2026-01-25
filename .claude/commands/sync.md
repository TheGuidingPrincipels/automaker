# Universal Worktree Sync

Synchronize the current worktree branch with main, ensuring no work is lost.

## Modes

| Command    | Mode         | Final Action                          |
| ---------- | ------------ | ------------------------------------- |
| `/sync`    | Standard     | Merge directly to main branch         |
| `/sync:pr` | Pull Request | Create a PR for review before merging |

**Check the argument**: If `$ARGUMENTS` contains `pr` or `:pr`, use **PR Mode**. Otherwise, use **Standard Mode**.

## Purpose

This command works from ANY worktree and automatically detects:

- Current worktree path and branch
- Main repository path and branch
- Sync direction

```
Current Worktree ($CURRENT_BRANCH)
        |
        | 1. Commit uncommitted changes
        | 2. Merge to main (Standard) OR Create PR (PR Mode)
        v
Main Repo ($MAIN_BRANCH)
        |
        | 3. Push to remote / PR created
        | 4. Sync worktree back
        v
Both repos synced at same commit
```

## Instructions

### Step 0: Environment Detection (ALWAYS RUN FIRST)

**This step MUST be executed before any other step.**

```bash
echo "=== Environment Detection ==="

# 1. Verify we're in a git repository
GIT_DIR=$(git rev-parse --absolute-git-dir 2>/dev/null)
if [ -z "$GIT_DIR" ]; then
    echo "ERROR: Not in a git repository."
    exit 1
fi

# 2. Get the common git directory (main repo's .git)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)

# 3. Check if running from main repo (not a worktree)
if [ "$GIT_DIR" = "$GIT_COMMON" ]; then
    echo "ERROR: Running from main repo. Nothing to sync."
    echo ""
    echo "This command must be run from a WORKTREE, not the main repository."
    echo "The main repo is already the sync target."
    echo ""
    echo "Available worktrees to sync:"
    git worktree list | grep -v '\[main\]'
    exit 1
fi

# 4. Get current worktree info
CURRENT_PATH=$(git rev-parse --show-toplevel)
CURRENT_BRANCH=$(git branch --show-current)
WORKTREE_NAME=$(basename "$GIT_DIR")

# 5. Validate branch exists (not detached HEAD)
if [ -z "$CURRENT_BRANCH" ]; then
    echo "ERROR: Worktree is in detached HEAD state."
    echo "Checkout a branch first: git checkout -b <branch-name>"
    exit 1
fi

# 6. Get main repo info
MAIN_REPO=$(dirname "$GIT_COMMON")
MAIN_BRANCH=$(git -C "$MAIN_REPO" branch --show-current)

if [ -z "$MAIN_BRANCH" ]; then
    echo "ERROR: Main repo is in detached HEAD state."
    echo "Please checkout a branch in main repo first."
    exit 1
fi

# 7. Display configuration
echo ""
echo "Sync Configuration"
echo "=================="
echo "Worktree:  $CURRENT_PATH"
echo "Branch:    $CURRENT_BRANCH"
echo "Main repo: $MAIN_REPO"
echo "Target:    $MAIN_BRANCH"
echo "Direction: $CURRENT_BRANCH -> $MAIN_BRANCH"
```

**CRITICAL**: If this step shows an error, STOP. Do not proceed with the sync.

**After running Step 0**: Store these values mentally for use in all subsequent steps:

- `$MAIN_REPO` = the main repository path (where main branch lives)
- `$CURRENT_PATH` = the current worktree path
- `$CURRENT_BRANCH` = the branch being synced (e.g., `dev/improvements`, `Reading-System`)
- `$MAIN_BRANCH` = typically `main`

---

### Step 1: Check Status of Both Repos

```bash
echo "=== Main Repo ==="
cd "$MAIN_REPO"
git fetch origin
git status --short
echo "Branch: $(git branch --show-current)"
echo "Commit: $(git rev-parse --short HEAD)"
echo "Message: $(git log --oneline -1)"

echo ""
echo "=== Current Worktree ==="
cd "$CURRENT_PATH"
git fetch origin
git status --short
echo "Branch: $(git branch --show-current)"
echo "Commit: $(git rev-parse --short HEAD)"
echo "Message: $(git log --oneline -1)"

echo ""
echo "=== Pre-Sync Safety Check ==="
echo "Commits in worktree not yet in main:"
cd "$MAIN_REPO"
git log "$MAIN_BRANCH".."$CURRENT_BRANCH" --oneline 2>/dev/null || echo "(none)"
echo ""
echo "Commits in main not in worktree:"
git log "$CURRENT_BRANCH".."$MAIN_BRANCH" --oneline 2>/dev/null || echo "(none)"
echo ""
echo "Stashes in main repo:"
git stash list | head -3 || echo "(none)"
echo "Stashes in worktree:"
cd "$CURRENT_PATH"
git stash list | head -3 || echo "(none)"
```

**CRITICAL**: Review the "Commits in worktree not yet in main" list. ALL of these commits MUST appear in main after the sync completes.

### Step 2: Commit Uncommitted Changes in Main

If main repo has uncommitted changes:

1. Review the changes with `git diff`
2. Create an appropriate commit message based on the changes
3. Commit:

```bash
cd "$MAIN_REPO"
git add -A
git commit -m "commit message here

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

### Step 3: Commit Uncommitted Changes in Worktree

If worktree has uncommitted changes:

1. Review the changes with `git diff --stat` and examine key files
2. Create an appropriate commit message describing the work
3. Commit:

```bash
cd "$CURRENT_PATH"
git add -A
git commit -m "commit message here

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

**Important:** Always commit worktree changes - never stash or discard. The goal is to preserve all work.

### Step 4: Sync Main from Remote (if behind)

Check if main is behind origin:

```bash
cd "$MAIN_REPO"
git fetch origin
BEHIND=$(git rev-list --count HEAD..origin/"$MAIN_BRANCH" 2>/dev/null || echo "0")
if [ "$BEHIND" -gt 0 ]; then
  echo "Main is $BEHIND commits behind origin, pulling..."
  git pull origin "$MAIN_BRANCH"
fi
```

### Step 5: Push Worktree Branch to Remote (Both Modes)

Push worktree branch as backup before any merge operations:

```bash
cd "$CURRENT_PATH"
git push origin "$CURRENT_BRANCH"
```

**Why push first?** If something goes wrong during merge, the commits are already safely on the remote.

---

## MODE SPLIT: Check `$ARGUMENTS` now

- If `$ARGUMENTS` contains `pr` -> Go to **Step 6A (PR Mode)**
- Otherwise -> Go to **Step 6B (Standard Mode)**

---

### Step 6A: PR Mode - Create Pull Request

**Skip the direct merge.** Instead, create a well-formatted PR.

#### 6A.1: Gather Commit Information

```bash
cd "$MAIN_REPO"

echo "=== Commits to include in PR ==="
git log "$MAIN_BRANCH".."$CURRENT_BRANCH" --oneline

echo ""
echo "=== Detailed changes ==="
git log "$MAIN_BRANCH".."$CURRENT_BRANCH" --pretty=format:"### %s%n%n%b%n---" --no-merges

echo ""
echo "=== Files changed ==="
git diff "$MAIN_BRANCH"..."$CURRENT_BRANCH" --stat
```

#### 6A.2: Check for Existing PR

```bash
EXISTING_PR=$(gh pr list --repo TheGuidingPrincipels/automaker --head "$CURRENT_BRANCH" --json number,url --jq '.[0]')
if [ -n "$EXISTING_PR" ]; then
    echo "WARNING: PR already exists for $CURRENT_BRANCH"
    echo "$EXISTING_PR"
    echo ""
    echo "Options:"
    echo "1. Update the existing PR (just push new commits)"
    echo "2. Close existing PR and create new one"
    echo ""
fi
```

#### 6A.3: Analyze and Summarize

Based on the commit history and changes, create a summary that:

- Groups related commits into logical features/improvements
- Uses simple, non-technical language where possible
- Highlights user-facing changes prominently
- Mentions technical changes briefly

#### 6A.4: Create the Pull Request

```bash
cd "$CURRENT_PATH"

gh pr create \
  --repo TheGuidingPrincipels/automaker \
  --base "$MAIN_BRANCH" \
  --head "$CURRENT_BRANCH" \
  --title "Merge $CURRENT_BRANCH: [descriptive title]" \
  --body "$(cat <<'EOF'
## Summary

[2-3 sentence overview of what this PR accomplishes]

## What's New

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
Synced from $CURRENT_BRANCH via `/sync:pr`

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

**Important:** Customize the title and body based on actual changes. The template above is a guide.

#### 6A.5: Report PR to User

```
Pull Request Created
====================
URL: [PR URL from gh pr create output]
From: $CURRENT_BRANCH -> $MAIN_BRANCH

Summary:
[Brief 1-2 line summary]

Changes included:
- [Key change 1]
- [Key change 2]
- [Key change 3]

Next steps:
1. Review the PR at the URL above
2. Merge when ready via GitHub
3. Run /sync after merging to sync worktree back
```

**PR Mode complete.** The branch is pushed and PR is created. Skip to Step 8 for final status report.

---

### Step 6B: Standard Mode - Merge and Push

Merge worktree branch into main and push:

```bash
cd "$MAIN_REPO"
git merge "$CURRENT_BRANCH" -m "Merge $CURRENT_BRANCH: [descriptive message]

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
git push origin "$MAIN_BRANCH"
```

If there are merge conflicts:

1. Show the conflicting files
2. Resolve conflicts (prefer worktree changes unless there's a reason not to)
3. Complete the merge
4. Push main

#### 6B.1: Sync Worktree Back from Main

```bash
cd "$CURRENT_PATH"
git merge origin/"$MAIN_BRANCH"
```

### Step 7: Final Verification (Standard Mode Only)

**Note:** In PR Mode, skip this step - repos won't be fully synced until PR is merged.

Run comprehensive verification to ensure NO commits were left behind:

```bash
echo "=== Final Sync Status ==="
cd "$MAIN_REPO"
MAIN_COMMIT=$(git rev-parse HEAD)
MAIN_SHORT=$(git rev-parse --short HEAD)
MAIN_MSG=$(git log --oneline -1)

cd "$CURRENT_PATH"
WORKTREE_COMMIT=$(git rev-parse HEAD)
WORKTREE_SHORT=$(git rev-parse --short HEAD)
WORKTREE_MSG=$(git log --oneline -1)

echo ""
if [ "$MAIN_COMMIT" = "$WORKTREE_COMMIT" ]; then
  echo "SYNCED: Both repos at commit $MAIN_SHORT"
else
  echo "WARNING: Repos at different commits:"
  echo "   Main:     $MAIN_SHORT"
  echo "   Worktree: $WORKTREE_SHORT"
fi

echo ""
echo "=== Orphan Check ==="
echo "Commits in worktree NOT in main (should be empty):"
cd "$MAIN_REPO"
git log "$MAIN_BRANCH".."$CURRENT_BRANCH" --oneline 2>/dev/null || echo "(none)"

echo ""
echo "Commits in main NOT in worktree (should be empty):"
cd "$CURRENT_PATH"
git log "$CURRENT_BRANCH"..origin/"$MAIN_BRANCH" --oneline 2>/dev/null || echo "(none)"

echo ""
echo "=== Remote Sync ==="
cd "$MAIN_REPO"
echo "Main behind origin: $(git rev-list --count HEAD..origin/$MAIN_BRANCH) (should be 0)"
echo "Main ahead of origin: $(git rev-list --count origin/$MAIN_BRANCH..HEAD) (should be 0)"
cd "$CURRENT_PATH"
echo "Worktree behind origin: $(git rev-list --count HEAD..origin/$CURRENT_BRANCH) (should be 0)"
echo "Worktree ahead of origin: $(git rev-list --count origin/$CURRENT_BRANCH..HEAD) (should be 0)"

echo ""
echo "=== Uncommitted Work Check ==="
cd "$MAIN_REPO"
MAIN_DIRTY=$(git status --short | wc -l | tr -d ' ')
cd "$CURRENT_PATH"
WORKTREE_DIRTY=$(git status --short | wc -l | tr -d ' ')
if [ "$MAIN_DIRTY" = "0" ] && [ "$WORKTREE_DIRTY" = "0" ]; then
  echo "No uncommitted changes in either repo"
else
  echo "WARNING: Uncommitted changes exist (main: $MAIN_DIRTY files, worktree: $WORKTREE_DIRTY files)"
fi
```

**CRITICAL**: If ANY of these checks show warnings, DO NOT proceed. Investigate and resolve before considering the sync complete.

### Step 8: Report to User

#### Standard Mode Report

```
Sync Complete
=============
| Location     | Commit     | Message              |
|--------------|------------|----------------------|
| Main         | [commit]   | [message]            |
| Worktree     | [commit]   | [message]            |

Synced: $CURRENT_BRANCH -> $MAIN_BRANCH

Actions taken:
1. [List commits created]
2. [List merges performed]
3. Pushed main to origin
4. Synced worktree from main

Both repositories are ready for development.
```

#### PR Mode Report

```
Pull Request Created
====================
URL: [PR URL]
From: $CURRENT_BRANCH -> $MAIN_BRANCH

Summary:
[Brief description of changes]

What's included:
- [Feature/improvement 1]
- [Feature/improvement 2]
- [etc.]

Next steps:
1. Review the PR: [URL]
2. Merge when ready
3. Run /sync after merging to sync worktree back

Worktree branch: pushed
PR: created
```

## Edge Cases

### Main Has Commits Worktree Doesn't

If main was updated directly (not through this workflow):

```bash
cd "$CURRENT_PATH"
git fetch origin
git merge origin/"$MAIN_BRANCH"
# Then continue with normal workflow
```

### Merge Conflicts

If conflicts occur during merge:

1. List conflicting files
2. For each file, examine both versions
3. Resolve preferring the most complete/recent work
4. Stage resolved files and complete merge
5. Continue with push and sync

### Worktree Has No Changes

If worktree has no uncommitted changes and is already synced with main:

- Report "Already synced, no action needed"
- Still verify both repos are at same commit

### Running from Main Repo

Step 0 will detect this and error gracefully with available worktrees listed.

## Safety Guarantees

### Both Modes

- All uncommitted work is committed (never lost)
- Worktree branch pushed to remote (backed up)
- Pre-sync orphan check prevents silent commit loss
- Stash check warns about potentially forgotten work
- Main repo detection prevents accidental errors

### Standard Mode

- Both repos end at the same commit (synced)
- Worktree branch always has all main changes
- Post-sync verification confirms zero orphaned commits

### PR Mode

- Changes reviewed before merging to main
- Clear summary of all work in PR description
- Merge happens through GitHub (audit trail)

## Quick Reference

```
/sync (Standard Mode):
0. Detect -> 1. Pre-check -> 2. Commit main -> 3. Commit worktree -> 4. Sync main from remote -> 5. Push worktree -> 6B. Merge->main, push, sync back -> 7. Verify -> 8. Report

/sync:pr (PR Mode):
0. Detect -> 1. Pre-check -> 2. Commit main -> 3. Commit worktree -> 4. Sync main from remote -> 5. Push worktree -> 6A. Create PR -> 8. Report
```

## Completion Checklists

### Standard Mode Checklist

Before marking sync complete, ALL must be true:

- [ ] `git log $MAIN_BRANCH..$CURRENT_BRANCH` shows NO commits
- [ ] `git log $CURRENT_BRANCH..origin/$MAIN_BRANCH` shows NO commits
- [ ] Main behind origin: 0
- [ ] Main ahead of origin: 0
- [ ] Worktree behind origin: 0
- [ ] Worktree ahead of origin: 0
- [ ] No uncommitted changes in either repo
- [ ] Stashes reviewed (if any exist)

### PR Mode Checklist

Before marking PR creation complete:

- [ ] Worktree branch pushed to origin
- [ ] No uncommitted changes in worktree
- [ ] PR created successfully
- [ ] PR URL provided to user
- [ ] PR body summarizes all changes clearly
