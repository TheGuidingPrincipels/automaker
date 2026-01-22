# Ship Changes to Remote

Complete workflow to commit, push, and create a PR from the current worktree branch.

## Purpose

Automates the full "ship it" workflow:

```
┌─────────────────┐     commit      ┌─────────────────┐     push      ┌─────────────────┐
│  Working Dir    │ ───────────►    │  Local Branch   │ ──────────►   │  Origin (fork)  │
│  (changes)      │                 │                 │               │                 │
└─────────────────┘                 └─────────────────┘               └─────────────────┘
                                                                              │
                                                                              │ PR
                                                                              ▼
                                                                    ┌─────────────────┐
                                                                    │  main branch    │
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

- "No uncommitted changes found. Would you like to create a PR for existing commits?"

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

### Step 5: Push to Origin

Push the branch to the fork:

```bash
git push -u origin $(git branch --show-current)
```

If push fails due to divergence, ask user how to proceed.

### Step 6: Create Pull Request

Create a PR with a visually appealing, easy-to-read description.

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
  --title "<type>: <summary>" \
  --body "$(cat <<'EOF'
<PR body here>
EOF
)"
```

### Step 7: Report Success

Display a summary:

```
✅ Ship Complete!
════════════════════════════════════════

📦 Commit:  <commit hash>
🌿 Branch:  <branch name>
🔗 PR:      <PR URL>

What's Next:
• Review the PR on GitHub
• Merge when ready
• Run /sync-dev to update main repo
```

## Important Rules

1. **ALWAYS use `--repo TheGuidingPrincipels/automaker`** when creating PRs
2. **NEVER push to upstream** (it's disabled anyway)
3. **Use simple, clear language** in commit messages and PR descriptions
4. **Include visual elements** (emojis, tables) to make PRs scannable
5. **Group changes logically** so reviewers can understand at a glance

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
