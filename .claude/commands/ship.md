# Ship Changes to Remote

Complete workflow to commit, push, merge locally, and create a PR from the current worktree branch.

## Purpose

Automates the full "ship it" workflow with local merging:

```
┌─────────────────┐     commit      ┌─────────────────┐     push      ┌─────────────────┐
│  Working Dir    │ ───────────►    │  Feature Branch │ ──────────►   │  origin/branch  │
│  (changes)      │                 │  (worktree)     │               │                 │
└─────────────────┘                 └─────────────────┘               └─────────────────┘
                                            │
                                            │ merge locally
                                            ▼
                                    ┌─────────────────┐     push      ┌─────────────────┐
                                    │  Local main     │ ──────────►   │  origin/main    │
                                    │  (main repo)    │               │                 │
                                    └─────────────────┘               └─────────────────┘
                                                                              │
                                                                              │ PR (docs)
                                                                              ▼
                                                                    ┌─────────────────┐
                                                                    │  GitHub PR #    │
                                                                    │  (for record)   │
                                                                    └─────────────────┘
```

## Instructions

### Step 1: Gather Information

Run these commands to understand the current state:

```bash
# Get branch and remote info
BRANCH=$(git branch --show-current)
REMOTE_URL=$(git remote get-url origin)
echo "Branch: $BRANCH"
echo "Remote: $REMOTE_URL"

# Get changed files
git status --short

# Get recent commits on this branch for context
git log --oneline -5
```

### Step 2: Check for Changes

If there are no uncommitted changes, ask the user:

- "No uncommitted changes found. Would you like to ship existing commits?"

If there ARE uncommitted changes, proceed to Step 3.

### Step 3: Analyze Changes

Carefully analyze ALL changes to understand what was done:

```bash
# Show staged and unstaged changes
git diff --stat
git diff --cached --stat

# Show untracked files
git ls-files --others --exclude-standard
```

Read the actual diffs to understand the changes deeply. Group them by:

- **Features**: New functionality added
- **Fixes**: Bugs fixed or issues resolved
- **Improvements**: Refactoring, performance, code quality
- **Tests**: New or updated tests
- **Docs**: Documentation changes

### Step 4: Create Commit

Stage all changes and create a commit with a well-formatted message.

**Commit Message Format:**

```
<type>: <short summary>

<body - what changed and why, in simple language>

Co-Authored-By: Claude <noreply@anthropic.com>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

**Example:**

```bash
git add -A
git commit -m "$(cat <<'EOF'
feat: add multi-provider authentication modes

Added support for per-provider auth mode configuration:
- Anthropic and OpenAI can now have independent auth modes
- New UI toggle for each provider in Settings
- Environment variable support with whitespace trimming
- Cached SettingsService to prevent race conditions

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### Step 5: Push Feature Branch to Origin

Push the branch to the fork:

```bash
git push -u origin $(git branch --show-current)
```

If push fails due to divergence, ask user how to proceed.

### Step 6: Merge Locally into Main

**IMPORTANT**: Always merge locally before creating the PR.

```bash
# Go to main repo
cd /Users/ruben/Documents/GitHub/automaker

# Merge the feature branch into main
git merge <feature-branch-name>

# Push main to origin
git push origin main

# Return to worktree
cd /Users/ruben/Documents/GitHub/automaker-dev
```

This ensures:

- Changes are immediately available on main
- Both repos stay in sync
- No waiting for GitHub PR review

### Step 7: Create Pull Request (Documentation)

Create a PR as documentation of the changes. Since we already merged locally, this PR serves as a record.

**PR Format:**

```markdown
## What Changed

A brief, human-friendly summary of what this PR does.

## Changes

### ✨ Features

- Feature 1
- Feature 2

### 🔧 Fixes

- Fix 1
- Fix 2

### 🛠️ Improvements

- Improvement 1
- Improvement 2

### 🧪 Tests

- Test changes

## Files Modified

| Area   | Files                  |
| ------ | ---------------------- |
| Server | `file1.ts`, `file2.ts` |
| UI     | `component.tsx`        |
| Types  | `types.ts`             |

## How to Test

1. Step 1
2. Step 2
3. Step 3

---

🤖 Generated with Claude
```

**Create the PR:**

```bash
gh pr create \
  --repo TheGuidingPrincipels/automaker \
  --base main \
  --head <feature-branch> \
  --title "<type>: <summary>" \
  --body "$(cat <<'EOF'
<PR body here>
EOF
)"
```

Note: The PR may show as already merged or have no diff since we merged locally first. That's expected - the PR serves as documentation.

### Step 8: Report Success

Display a summary:

```
✅ Ship Complete!
════════════════════════════════════════

📦 Commit:  <commit hash>
🌿 Branch:  <branch name>
🔀 Merged:  Into main locally
🚀 Pushed:  origin/main updated
🔗 PR:      <PR URL> (documentation)

Both repos are now in sync!
```

## Important Rules

1. **ALWAYS merge locally** before creating the PR
2. **ALWAYS use `--repo TheGuidingPrincipels/automaker`** when creating PRs
3. **NEVER push to upstream** (it's disabled anyway)
4. **Use simple, clear language** in commit messages and PR descriptions
5. **Include visual elements** (emojis, tables) to make PRs scannable
6. **Group changes logically** so reviewers can understand at a glance

## Repository Paths

- **Main repo**: `/Users/ruben/Documents/GitHub/automaker`
- **Dev worktree**: `/Users/ruben/Documents/GitHub/automaker-dev`

## Arguments

The command accepts an optional argument for the commit type:

- `/ship` - Auto-detect type from changes
- `/ship feat` - Force feature type
- `/ship fix` - Force fix type
- `/ship refactor` - Force refactor type

## Dry Run Mode

If user says "dry run" or asks to preview:

- Show the commit message that WOULD be created
- Show the PR body that WOULD be used
- Ask for confirmation before executing

## Skip PR Mode

If user says "no pr" or "skip pr":

- Complete steps 1-6 (commit, push, merge)
- Skip creating the PR
- Just report the merge was successful
