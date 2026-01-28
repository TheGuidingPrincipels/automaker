# Universal Worktree Sync

Synchronize a worktree branch with main, ensuring no work is lost and no merge conflicts go undetected.

## Syntax

| Command      | Description                                       |
| ------------ | ------------------------------------------------- |
| `/sync`      | Sync current worktree (must be run from worktree) |
| `/sync 1`    | Sync feature-1 worktree                           |
| `/sync 2`    | Sync feature-2 worktree                           |
| `/sync:pr`   | Create PR instead of direct merge                 |
| `/sync 1:pr` | Sync feature-1 via PR                             |
| `/sync 2:pr` | Sync feature-2 via PR                             |

## Argument Parsing

**Parse `$ARGUMENTS` to determine:**

1. **Worktree selection**:
   - If contains `1` → use `.worktrees/feature-1`
   - If contains `2` → use `.worktrees/feature-2`
   - Otherwise → use current directory (must be a worktree)

2. **Mode selection**:
   - If contains `pr` or `:pr` → **PR Mode**
   - Otherwise → **Standard Mode**

## Purpose

This command works from ANY location when a number is specified:

- Current worktree path and branch
- Main repository path and branch
- Sync direction

```
Current Worktree ($CURRENT_BRANCH)
        |
        | 1. Commit uncommitted changes
        | 2. Conflict preview & safety checks
        | 3. Merge to main (Standard) OR Create PR (PR Mode)
        v
Main Repo ($MAIN_BRANCH)
        |
        | 4. Push to remote / PR created
        | 5. Sync worktree back
        v
Both repos synced at same commit
```

## Instructions

### Step 0: Environment Detection (ALWAYS RUN FIRST)

**This step MUST be executed before any other step.**

**First, parse `$ARGUMENTS` to determine worktree:**

- If `$ARGUMENTS` contains `1` → `WORKTREE_PATH=.worktrees/feature-1`
- If `$ARGUMENTS` contains `2` → `WORKTREE_PATH=.worktrees/feature-2`
- Otherwise → use current directory

```bash
echo "=== Environment Detection ==="

# 1. Parse arguments for worktree selection
ARGS="$ARGUMENTS"
MAIN_REPO="/Users/ruben/Documents/GitHub/automaker"

if echo "$ARGS" | grep -q "1"; then
    WORKTREE_PATH="$MAIN_REPO/.worktrees/feature-1"
    echo "Selected: feature-1 worktree (from argument)"
elif echo "$ARGS" | grep -q "2"; then
    WORKTREE_PATH="$MAIN_REPO/.worktrees/feature-2"
    echo "Selected: feature-2 worktree (from argument)"
else
    WORKTREE_PATH=$(pwd)
    echo "Using: current directory"
fi

# 2. Navigate to worktree
cd "$WORKTREE_PATH" || { echo "ERROR: Cannot access $WORKTREE_PATH"; exit 1; }

# 3. Verify we're in a git repository
GIT_DIR=$(git rev-parse --absolute-git-dir 2>/dev/null)
if [ -z "$GIT_DIR" ]; then
    echo "ERROR: Not in a git repository."
    exit 1
fi

# 4. Get the common git directory (main repo's .git)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)

# 5. Check if running from main repo (not a worktree)
if [ "$GIT_DIR" = "$GIT_COMMON" ]; then
    echo "ERROR: Running from main repo. Nothing to sync."
    echo ""
    echo "Specify a worktree to sync:"
    echo "  /sync 1  - sync feature-1"
    echo "  /sync 2  - sync feature-2"
    echo ""
    echo "Available worktrees:"
    git worktree list | grep -v '\[main\]'
    exit 1
fi

# 6. Get worktree info
CURRENT_PATH=$(git rev-parse --show-toplevel)
CURRENT_BRANCH=$(git branch --show-current)
WORKTREE_NAME=$(basename "$CURRENT_PATH")

# 7. Validate branch exists (not detached HEAD)
if [ -z "$CURRENT_BRANCH" ]; then
    echo "ERROR: Worktree is in detached HEAD state."
    echo "Checkout a branch first: git checkout -b <branch-name>"
    exit 1
fi

# 8. Get main repo info
MAIN_REPO=$(dirname "$GIT_COMMON")
MAIN_BRANCH=$(git -C "$MAIN_REPO" branch --show-current)

if [ -z "$MAIN_BRANCH" ]; then
    echo "ERROR: Main repo is in detached HEAD state."
    echo "Please checkout a branch in main repo first."
    exit 1
fi

# 9. Display configuration
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
- `$CURRENT_BRANCH` = the branch being synced (e.g., `feature-1`, `feature-2`)
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

### Step 5: Create Safety Backups

**CRITICAL**: Before any merge operations, create backup refs for recovery.

```bash
echo "=== Creating Safety Backups ==="
cd "$MAIN_REPO"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup main branch position
git tag "backup/main-pre-sync-$TIMESTAMP" "$MAIN_BRANCH"
echo "✓ Created: backup/main-pre-sync-$TIMESTAMP"

# Backup worktree branch position
git tag "backup/$CURRENT_BRANCH-pre-sync-$TIMESTAMP" "$CURRENT_BRANCH"
echo "✓ Created: backup/$CURRENT_BRANCH-pre-sync-$TIMESTAMP"

echo ""
echo "Recovery commands if something goes wrong:"
echo "  Main:     git checkout $MAIN_BRANCH && git reset --hard backup/main-pre-sync-$TIMESTAMP"
echo "  Worktree: cd $CURRENT_PATH && git reset --hard backup/$CURRENT_BRANCH-pre-sync-$TIMESTAMP"
```

**Why backup?** Provides easy rollback if the merge goes wrong. These tags can be deleted after successful sync.

### Step 6: Push Worktree Branch to Remote (Both Modes)

Push worktree branch as backup before any merge operations:

```bash
cd "$CURRENT_PATH"
git push origin "$CURRENT_BRANCH"
```

**Why push first?** If something goes wrong during merge, the commits are already safely on the remote.

### Step 7: Conflict Preview & Overlap Analysis (CRITICAL)

**This step detects potential problems BEFORE attempting the merge.**

#### 7.1: Find Merge Base

```bash
cd "$MAIN_REPO"
MERGE_BASE=$(git merge-base "$MAIN_BRANCH" "$CURRENT_BRANCH")
echo "Merge base: $(git log --oneline -1 $MERGE_BASE)"
echo "Branches diverged at this commit"
```

#### 7.2: Analyze File Overlap

Check which files were modified in BOTH branches since they diverged:

```bash
echo ""
echo "=== File Overlap Analysis ==="

# Files modified in main since merge base
MAIN_FILES=$(git diff --name-only "$MERGE_BASE".."$MAIN_BRANCH")

# Files modified in worktree since merge base
WORKTREE_FILES=$(git diff --name-only "$MERGE_BASE".."$CURRENT_BRANCH")

# Find overlapping files
OVERLAP_FILES=$(comm -12 <(echo "$MAIN_FILES" | sort) <(echo "$WORKTREE_FILES" | sort))
OVERLAP_COUNT=$(echo "$OVERLAP_FILES" | grep -c . || echo "0")

if [ "$OVERLAP_COUNT" -gt 0 ]; then
    echo "⚠️  WARNING: $OVERLAP_COUNT files modified in BOTH branches:"
    echo "$OVERLAP_FILES" | head -20
    echo ""
    echo "These files may have logical conflicts even without git merge conflicts."
    echo "Review carefully after merge."
else
    echo "✓ No overlapping file modifications detected"
fi
```

#### 7.3: Conflict Prediction with git merge-tree

**Preview merge conflicts WITHOUT touching the working directory:**

```bash
echo ""
echo "=== Conflict Prediction (Dry Run) ==="

# Use git merge-tree for conflict detection (Git 2.38+)
MERGE_TREE_OUTPUT=$(git merge-tree --write-tree --name-only "$MERGE_BASE" "$MAIN_BRANCH" "$CURRENT_BRANCH" 2>&1)
MERGE_TREE_EXIT=$?

if [ $MERGE_TREE_EXIT -eq 0 ]; then
    echo "✓ No merge conflicts predicted - clean merge expected"
else
    echo "⚠️  CONFLICTS PREDICTED:"
    echo ""
    # Extract conflict information
    echo "$MERGE_TREE_OUTPUT" | grep -A5 "CONFLICT" || true
    echo ""
    echo "Conflicting files:"
    echo "$MERGE_TREE_OUTPUT" | grep -E "^[a-zA-Z]" | head -20 || true

    # Set flag for user confirmation
    CONFLICTS_PREDICTED=true
fi
```

#### 7.4: Pre-Flight Summary & User Confirmation

Display summary and get confirmation before proceeding:

```bash
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║              SYNC PRE-FLIGHT CHECK                     ║"
echo "╠════════════════════════════════════════════════════════╣"

# Count commits to merge
COMMIT_COUNT=$(git log "$MAIN_BRANCH".."$CURRENT_BRANCH" --oneline | wc -l | tr -d ' ')
echo "║ Commits to merge from worktree: $COMMIT_COUNT"

# Count files changed
FILES_CHANGED=$(git diff "$MAIN_BRANCH"..."$CURRENT_BRANCH" --name-only | wc -l | tr -d ' ')
echo "║ Files changed in worktree:      $FILES_CHANGED"

echo "║ Files also changed in main:     $OVERLAP_COUNT"

if [ "$CONFLICTS_PREDICTED" = "true" ]; then
    echo "║ Predicted conflicts:            ⚠️  YES - REVIEW ABOVE"
else
    echo "║ Predicted conflicts:            ✓ None"
fi

echo "║ Backup refs:                    ✓ Created"
echo "╚════════════════════════════════════════════════════════╝"
```

**DECISION POINT:**

- If **conflicts predicted** → Ask user: "Conflicts detected. Proceed with merge? (y/n)"
- If **overlap > 5 files** → Warn user: "High file overlap. Recommend careful review."
- If **clean merge expected** → Proceed automatically

**CRITICAL**: If user says NO or wants to abort, go to **Recovery Procedures** section.

---

## MODE SPLIT: Check for PR mode

- If `$ARGUMENTS` contains `pr` or `:pr` -> Go to **Step 8A (PR Mode)**
- Otherwise -> Go to **Step 8B (Standard Mode)**

Examples:

- `/sync 1` → Standard mode for feature-1
- `/sync 2:pr` → PR mode for feature-2
- `/sync:pr` → PR mode for current worktree

---

### Step 8A: PR Mode - Create Pull Request

**Skip the direct merge.** Instead, create a well-formatted PR.

#### 8A.1: Gather Commit Information

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

#### 8A.2: Check for Existing PR

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

#### 8A.3: Analyze and Summarize

Based on the commit history and changes, create a summary that:

- Groups related commits into logical features/improvements
- Uses simple, non-technical language where possible
- Highlights user-facing changes prominently
- Mentions technical changes briefly

#### 8A.4: Create the Pull Request

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

#### 8A.5: Report PR to User

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

**PR Mode complete.** The branch is pushed and PR is created. Skip to Step 10 for final status report.

---

### Step 8B: Standard Mode - Merge and Push

#### 8B.1: Configure Merge for Better Conflict Display

```bash
cd "$MAIN_REPO"
# Enable diff3 conflict style for better context
git config merge.conflictstyle diff3
```

#### 8B.2: Attempt the Merge

```bash
cd "$MAIN_REPO"
git merge "$CURRENT_BRANCH" -m "Merge $CURRENT_BRANCH: [descriptive message]

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

**If merge succeeds without conflicts:** Continue to Step 8B.4

**If merge conflicts occur:** Go to Step 8B.3 (Conflict Resolution Protocol)

#### 8B.3: Conflict Resolution Protocol

**CRITICAL**: Follow this protocol carefully to ensure no work is lost.

##### 8B.3.1: Identify All Conflicts

```bash
echo "=== Conflicting Files ==="
git diff --name-only --diff-filter=U

echo ""
echo "=== Conflict Details ==="
git status
```

##### 8B.3.2: For Each Conflicting File

For each file with conflicts:

1. **Examine the conflict:**

   ```bash
   # Show the conflict with full context (diff3 style shows BASE, OURS, THEIRS)
   cat <conflicting-file>
   ```

2. **Understand the three versions:**
   - `<<<<<<< HEAD` = Main branch version (current)
   - `||||||| <merge-base>` = Original version before both changes (diff3 only)
   - `=======` = Separator
   - `>>>>>>> <branch>` = Worktree branch version (incoming)

3. **Resolution Decision Matrix:**

   | Scenario                             | Action                     |
   | ------------------------------------ | -------------------------- |
   | Worktree has NEWER functionality     | Keep worktree version      |
   | Main has NEWER functionality         | Keep main version          |
   | BOTH have distinct new functionality | Manually merge (keep both) |
   | Changes are incompatible             | Ask user for guidance      |

4. **Apply resolution and verify:**

   ```bash
   # After editing the file
   git add <file>

   # Verify no conflict markers remain
   grep -n "<<<<<<\|======\|>>>>>>" <file> && echo "ERROR: Markers remain!" || echo "✓ Clean"
   ```

##### 8B.3.3: Complete the Merge

```bash
# Verify all conflicts resolved
REMAINING=$(git diff --name-only --diff-filter=U | wc -l | tr -d ' ')
if [ "$REMAINING" -gt 0 ]; then
    echo "ERROR: $REMAINING unresolved conflicts remain"
    git diff --name-only --diff-filter=U
    exit 1
fi

# Check no conflict markers in staged files
git diff --cached --name-only | while read file; do
    if grep -q "<<<<<<\|======\|>>>>>>" "$file" 2>/dev/null; then
        echo "ERROR: Conflict markers found in $file"
        exit 1
    fi
done

# Complete the merge
git commit -m "Merge $CURRENT_BRANCH: [descriptive message]

Resolved conflicts in: [list files]

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

##### 8B.3.4: Document Conflict Resolutions

**IMPORTANT**: Report to user what was resolved and how:

```
Conflict Resolution Summary
===========================
File: path/to/file.ts
  - Kept worktree version (newer feature implementation)
  - Discarded: minor formatting from main

File: path/to/other.ts
  - Merged both changes (additive, compatible)
  - Main added: function A
  - Worktree added: function B
  - Result: Both functions present

VERIFY: Please review these resolutions are correct.
```

#### 8B.4: Push Main to Remote

```bash
cd "$MAIN_REPO"
git push origin "$MAIN_BRANCH"
```

#### 8B.5: Sync Worktree Back from Main

```bash
cd "$CURRENT_PATH"
git fetch origin
git merge origin/"$MAIN_BRANCH"
```

### Step 9: Final Verification (Standard Mode Only)

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
  echo "✓ SYNCED: Both repos at commit $MAIN_SHORT"
else
  echo "⚠️ WARNING: Repos at different commits:"
  echo "   Main:     $MAIN_SHORT"
  echo "   Worktree: $WORKTREE_SHORT"
fi

echo ""
echo "=== Orphan Check ==="
echo "Commits in worktree NOT in main (should be empty):"
cd "$MAIN_REPO"
ORPHAN_WT=$(git log "$MAIN_BRANCH".."$CURRENT_BRANCH" --oneline 2>/dev/null)
if [ -z "$ORPHAN_WT" ]; then
    echo "✓ None - all worktree commits are in main"
else
    echo "⚠️ ORPHANED COMMITS DETECTED:"
    echo "$ORPHAN_WT"
    echo "ERROR: These commits were NOT merged. DO NOT consider sync complete!"
fi

echo ""
echo "Commits in main NOT in worktree (should be empty):"
cd "$CURRENT_PATH"
ORPHAN_MAIN=$(git log "$CURRENT_BRANCH"..origin/"$MAIN_BRANCH" --oneline 2>/dev/null)
if [ -z "$ORPHAN_MAIN" ]; then
    echo "✓ None - worktree has all main commits"
else
    echo "⚠️ MISSING COMMITS:"
    echo "$ORPHAN_MAIN"
fi

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
  echo "✓ No uncommitted changes in either repo"
else
  echo "⚠️ WARNING: Uncommitted changes exist (main: $MAIN_DIRTY files, worktree: $WORKTREE_DIRTY files)"
fi
```

**CRITICAL**: If ANY of these checks show warnings, DO NOT proceed. Investigate and resolve before considering the sync complete.

### Step 10: Cleanup Backup Tags (Optional)

After successful verification, optionally clean up backup tags:

```bash
echo "=== Cleanup ==="
echo "Sync verified successful. Remove backup tags? (recommended to keep for 24h)"

# To remove backup tags:
# git tag -d "backup/main-pre-sync-$TIMESTAMP"
# git tag -d "backup/$CURRENT_BRANCH-pre-sync-$TIMESTAMP"

# List recent backup tags
echo "Recent backup tags:"
git tag -l "backup/*" | tail -10
```

### Step 11: Report to User

#### Standard Mode Report

```
Sync Complete ✓
===============
╔════════════════════════════════════════════════════════╗
║ Location     │ Commit   │ Message                      ║
╠════════════════════════════════════════════════════════╣
║ Main         │ [commit] │ [message]                    ║
║ Worktree     │ [commit] │ [message]                    ║
╚════════════════════════════════════════════════════════╝

Synced: $CURRENT_BRANCH -> $MAIN_BRANCH

Actions taken:
1. [List commits created]
2. [List merges performed]
3. Conflicts resolved: [count] files (if any)
4. Pushed main to origin
5. Synced worktree from main

Verification:
✓ No orphaned commits
✓ Both repos at same commit
✓ Remote in sync

Both repositories are ready for development.

Backup tags available for 24h:
- backup/main-pre-sync-[timestamp]
- backup/$CURRENT_BRANCH-pre-sync-[timestamp]
```

#### PR Mode Report

```
Pull Request Created ✓
======================
URL: [PR URL]
From: $CURRENT_BRANCH -> $MAIN_BRANCH

Summary:
[Brief description of changes]

What's included:
- [Feature/improvement 1]
- [Feature/improvement 2]
- [etc.]

Conflict Preview: [None detected / X potential conflicts]

Next steps:
1. Review the PR: [URL]
2. Merge when ready
3. Run /sync after merging to sync worktree back

Worktree branch: pushed ✓
PR: created ✓
```

---

## Recovery Procedures

### Abort Mid-Merge

If you need to abort during a merge:

```bash
git merge --abort
echo "Merge aborted. Working directory restored to pre-merge state."
```

### Recover from Bad Merge (Using Backup Tags)

If the merge completed but was wrong:

```bash
# 1. Find your backup tag
git tag -l "backup/*-pre-sync-*" | sort | tail -5

# 2. Reset main to backup
cd "$MAIN_REPO"
git checkout "$MAIN_BRANCH"
git reset --hard backup/main-pre-sync-TIMESTAMP
git push origin "$MAIN_BRANCH" --force-with-lease

# 3. Reset worktree to backup
cd "$CURRENT_PATH"
git reset --hard backup/$CURRENT_BRANCH-pre-sync-TIMESTAMP
git push origin "$CURRENT_BRANCH" --force-with-lease
```

### Worktree in Bad State

If worktree is corrupted or in unknown state:

```bash
cd "$CURRENT_PATH"

# Option 1: Reset to remote
git fetch origin
git reset --hard origin/"$CURRENT_BRANCH"

# Option 2: Reset to backup
git reset --hard backup/$CURRENT_BRANCH-pre-sync-TIMESTAMP
```

### Lost Commits Recovery

If commits seem lost, check:

```bash
# Check reflog (keeps 90 days of history)
git reflog | head -20

# Recover specific commit
git cherry-pick <commit-hash>

# Check if commit exists anywhere
git branch --contains <commit-hash>
```

---

## Edge Cases

### Main Has Commits Worktree Doesn't

If main was updated directly (not through this workflow):

```bash
cd "$CURRENT_PATH"
git fetch origin
git merge origin/"$MAIN_BRANCH"
# Then continue with normal workflow
```

### Worktree Has No Changes

If worktree has no uncommitted changes and is already synced with main:

- Report "Already synced, no action needed"
- Still verify both repos are at same commit

### Running from Main Repo

Step 0 will detect this and error gracefully with available worktrees listed.

### Git Version Compatibility

The `git merge-tree --write-tree` command requires Git 2.38+. Check version:

```bash
git --version
# If < 2.38, use fallback:
git merge --no-commit --no-ff "$CURRENT_BRANCH"
# Then abort if conflicts: git merge --abort
```

---

## Safety Guarantees

### Fork Safety (CRITICAL)

**NEVER push to or create PRs targeting `upstream` (AutoMaker-Org/automaker).**

- `origin` = TheGuidingPrincipels/automaker (YOUR fork) - push here
- `upstream` = AutoMaker-Org/automaker (READ ONLY - never push)

All `/sync` operations push to `origin` only. The `--repo TheGuidingPrincipels/automaker` flag in PR mode ensures PRs target your fork.

### Data Loss Prevention

| Protection                    | How                                               |
| ----------------------------- | ------------------------------------------------- |
| Backup refs before merge      | Recovery possible via `git reset --hard backup/*` |
| Push worktree to remote first | Commits safe even if local merge fails            |
| Conflict prediction           | See problems before they happen                   |
| Orphan commit check           | Verify nothing was left behind                    |
| Overlap analysis              | Catch logical conflicts git won't detect          |

### Both Modes

- All uncommitted work is committed (never lost)
- Worktree branch pushed to remote (backed up)
- Backup tags created before risky operations
- Pre-sync orphan check prevents silent commit loss
- Conflict prediction before merge attempt
- Stash check warns about potentially forgotten work
- Main repo detection prevents accidental errors

### Standard Mode

- Both repos end at the same commit (synced)
- Worktree branch always has all main changes
- Post-sync verification confirms zero orphaned commits
- Conflict resolution documented and reported

### PR Mode

- Changes reviewed before merging to main
- Clear summary of all work in PR description
- Conflict prediction in PR description
- Merge happens through GitHub (audit trail)

---

## Quick Reference

```
/sync (Standard Mode):
0. Detect
1. Pre-check status
2. Commit main (if dirty)
3. Commit worktree (if dirty)
4. Sync main from remote
5. Create backup tags ← NEW
6. Push worktree to remote
7. Conflict preview & overlap analysis ← NEW
8B. Merge → resolve conflicts → push → sync back
9. Final verification
10. Cleanup backups (optional)
11. Report

/sync:pr (PR Mode):
0. Detect
1. Pre-check status
2. Commit main (if dirty)
3. Commit worktree (if dirty)
4. Sync main from remote
5. Create backup tags ← NEW
6. Push worktree to remote
7. Conflict preview & overlap analysis ← NEW
8A. Create PR
11. Report
```

---

## Completion Checklists

### Standard Mode Checklist

Before marking sync complete, ALL must be true:

- [ ] Backup tags created
- [ ] Conflict preview reviewed (if conflicts predicted, user confirmed)
- [ ] `git log $MAIN_BRANCH..$CURRENT_BRANCH` shows NO commits (no orphans)
- [ ] `git log $CURRENT_BRANCH..origin/$MAIN_BRANCH` shows NO commits
- [ ] Main behind origin: 0
- [ ] Main ahead of origin: 0
- [ ] Worktree behind origin: 0
- [ ] Worktree ahead of origin: 0
- [ ] No uncommitted changes in either repo
- [ ] Stashes reviewed (if any exist)
- [ ] Conflict resolutions documented (if any)

### PR Mode Checklist

Before marking PR creation complete:

- [ ] Backup tags created
- [ ] Conflict preview included in PR description
- [ ] Worktree branch pushed to origin
- [ ] No uncommitted changes in worktree
- [ ] PR created successfully
- [ ] PR URL provided to user
- [ ] PR body summarizes all changes clearly
- [ ] Overlap analysis noted (if high overlap)
