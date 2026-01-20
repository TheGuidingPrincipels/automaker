---
name: upstream-check
description: Check for upstream changes in forked repositories and generate analysis reports. Use for tracking changes in heavily modified forks.
user_invocable: true
---

# Upstream Change Analysis Skill

Analyze upstream repository changes, detect conflicts, investigate severity, and generate actionable reports for fork maintenance.

## When to Use

Run this skill when you want to:

- Check what's new in the upstream repository
- Get recommendations for feature adoption
- Identify breaking changes that affect your modifications
- Detect merge conflicts before they become problems
- Get severity assessments and resolution strategies for conflicts
- Generate periodic (3-7 day) upstream tracking reports

## Conflict Severity Classification

| Severity     | Criteria                                              | Action                      |
| ------------ | ----------------------------------------------------- | --------------------------- |
| **NONE**     | `git merge-tree` succeeds, no file overlaps           | ✅ Safe to merge            |
| **LOW**      | File overlaps exist but in non-critical paths         | Auto-resolve likely         |
| **MEDIUM**   | Conflicts in watch paths, but different code sections | Manual review recommended   |
| **HIGH**     | Same functions/classes modified by both sides         | Deep investigation required |
| **CRITICAL** | Breaking changes + conflicts in core APIs             | Block merge, investigate    |

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    UPSTREAM CHECK FLOW                       │
└─────────────────────────────────────────────────────────────┘
                              │
    Steps 1-7: Analysis       │      Steps 8-10: Investigation
    ─────────────────         │      ────────────────────────
                              │
    ┌─────────────────┐       │
    │ 1. Load Config  │       │
    │ 2. Fetch        │       │
    │ 3. Get Commits  │       │       ┌─────────────────────┐
    │ 4. Analyze      │───────┼──────►│ 8. Assess Severity  │
    │ 5. Report       │       │       └─────────┬───────────┘
    │ 6. Update       │       │                 │
    │ 7. Summary      │       │    Severity ≥ MEDIUM?
    └─────────────────┘       │                 │
                              │       ┌─────────┴─────────┐
                              │       ▼                   ▼
                              │    ┌──────┐          ┌────────────┐
                              │    │ NO   │          │ YES        │
                              │    │ Done │          │ Step 9     │
                              │    └──────┘          │ Investigate│
                              │                      └─────┬──────┘
                              │                            │
                              │                      ┌─────┴──────┐
                              │                      │ Step 10    │
                              │                      │ Resolution │
                              │                      └────────────┘
```

## Workflow Steps

### Step 1: Locate Fork Configuration

Find the `.automaker-fork/config.json` in the current project directory:

```bash
cat .automaker-fork/config.json
```

Extract:

- `tracking.lastCheckedCommit` - where we left off
- `analysis.skipPatterns` - commits to skip
- `analysis.priorityPatterns` - commits to prioritize
- `analysis.watchPaths` - directories to watch closely
- `investigation.autoInvestigate` - whether to auto-investigate conflicts
- `investigation.severityThreshold` - minimum severity to trigger investigation

### Step 2: Fetch Upstream Changes

```bash
git fetch upstream
```

### Step 3: Get Commits Since Last Check

Get the list of commits between the last checked commit and upstream/main:

```bash
git log --oneline --no-merges <lastCheckedCommit>..upstream/main
```

If there are many commits (>50), summarize by grouping instead of listing all.

### Step 4: Token-Efficient Analysis Pipeline

**Level 1 - Metadata Only (always do this):**

- Parse commit messages for conventional commit format (feat:, fix:, etc.)
- Group commits by type and scope
- Count commits per category

**Level 2 - File Impact (for priority commits):**

- For commits matching `priorityPatterns`, list files changed
- Flag commits touching `watchPaths`
- Identify commits with "BREAKING CHANGE" in message

**Level 3 - Selective Deep Analysis (only when necessary):**

- Only analyze diffs for:
  - Breaking changes
  - Security fixes
  - Changes to core API files (types/, prompts/)
- Use `git show <hash> --stat` first, then `git show <hash>` only if needed

**Skip Analysis For:**

- Commits matching `skipPatterns` (docs, deps, style, test, ci)
- Merge commits
- Commits only touching files outside `watchPaths` (unless breaking)

### Step 5: Generate Report

Create a markdown report at `.automaker-fork/reports/YYYY-MM-DD.md`:

```markdown
# Upstream Changes Report - [DATE]

## Summary

- **Period**: [last_check] to [now]
- **Upstream Branch**: upstream/main
- **Total New Commits**: X
- **Analyzed Commits**: Y (after filtering)
- **Conflict Severity**: [NONE/LOW/MEDIUM/HIGH/CRITICAL]

## Breaking Changes

[List with full analysis - these are critical]

## New Features

| Feature | Commit | Files Changed | Recommendation   |
| ------- | ------ | ------------- | ---------------- |
| ...     | ...    | ...           | Adopt/Skip/Defer |

## Bug Fixes

[List fixes that might apply to your codebase]

## Impact on Your Modifications

[Analysis of which changes touch paths you've modified]

## Conflict Analysis

[Results from Step 8 - severity assessment]

## Investigation Findings

[Results from Step 9 - if applicable]

## Resolution Strategy

[Results from Step 10 - recommended approach]

## Cherry-Pick Commands

[Ready-to-use commands for recommended adoptions]

## Recommendations

1. [Actionable items]
2. [Priority order]

---

Generated by /upstream-check on [timestamp]
Last checked commit: [hash]
New baseline commit: [upstream/main hash]
```

### Step 6: Update Configuration

Update `.automaker-fork/config.json`:

- Set `tracking.lastCheckedCommit` to current upstream/main HEAD
- Set `tracking.lastCheckedAt` to current timestamp

### Step 7: Summary Output

Display a brief summary to the user:

- Number of new commits
- Number of breaking changes (if any)
- **Conflict severity level**
- Top 3 recommendations
- Path to full report

---

## Phase 2: Conflict Investigation (Steps 8-10)

### Step 8: Conflict Severity Assessment

Assess merge conflict severity using `git merge-tree`:

```bash
# Step 8.1: Try merge-tree simulation
MERGE_OUTPUT=$(git merge-tree --write-tree HEAD upstream/main 2>&1)

# Step 8.2: Check result
if [[ $MERGE_OUTPUT =~ ^[a-f0-9]{40}$ ]]; then
  # Clean merge - no conflicts
  SEVERITY="NONE"
  echo "✅ Clean merge possible"
else
  # Conflicts detected - extract details
  echo "$MERGE_OUTPUT" > /tmp/merge-tree-output.txt

  # Step 8.3: Extract conflicting files
  CONFLICT_FILES=$(echo "$MERGE_OUTPUT" | grep -E "^CONFLICT" | awk '{print $NF}')

  # Step 8.4: Classify severity based on paths
  SEVERITY="LOW"

  for file in $CONFLICT_FILES; do
    # Check against watch paths (from config)
    if [[ $file == apps/server/* ]] || [[ $file == libs/types/* ]] || \
       [[ $file == libs/prompts/* ]] || [[ $file == apps/ui/* ]]; then
      SEVERITY="MEDIUM"

      # Check if same functions modified (requires deeper analysis)
      # This will be done by sub-agents in Step 9
    fi
  done
fi
```

**Severity Classification Logic:**

| Check                                                | Severity |
| ---------------------------------------------------- | -------- |
| `git merge-tree` returns clean tree hash             | NONE     |
| Conflicts only in non-watch paths                    | LOW      |
| Conflicts in watch paths, unknown overlap            | MEDIUM   |
| Same functions/classes modified (detected by agents) | HIGH     |
| Breaking changes + conflicts in core APIs            | CRITICAL |

**Output for Report:**

```markdown
## Conflict Analysis

**Severity**: [NONE/LOW/MEDIUM/HIGH/CRITICAL]

### Merge Simulation Result

- Clean merge possible: [Yes/No]
- Conflicting files: [count]

### Conflicting Files

| File            | Watch Path? | Conflict Type |
| --------------- | ----------- | ------------- |
| path/to/file.ts | ✅          | content       |
| ...             | ...         | ...           |
```

### Step 9: Deep Investigation (Severity ≥ MEDIUM)

When severity is MEDIUM or higher, launch parallel investigation agents:

```
┌─────────────────────────────────────────────────────────────┐
│                    CONFLICT DETECTED                         │
│                    Severity: [MEDIUM+]                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
            ┌─────────────────┴─────────────────┐
            │     Launch Investigation Agents    │
            │     (if config.investigation.     │
            │      useSubAgents is true)        │
            └─────────────────┬─────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Agent 1:      │   │ Agent 2:      │   │ Agent 3:      │
│ Structural    │   │ Behavioral    │   │ Integration   │
│ Analysis      │   │ Analysis      │   │ Risk          │
└───────────────┘   └───────────────┘   └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │ Merged Report   │
                    │ + Resolution    │
                    │ Strategy        │
                    └─────────────────┘
```

#### Agent 1: Structural Analysis

**Purpose**: Exact line-by-line conflict mapping and dependency analysis.

**Launch Command** (use Task tool with deepdive agent):

```
Analyze the structural aspects of merge conflicts between our fork and upstream:

CONFLICTING FILES:
[list of conflicting files from Step 8]

OUR CHANGES (since fork):
[git diff upstream/main...HEAD -- <conflicting_files>]

UPSTREAM CHANGES (new):
[git diff <lastCheckedCommit>..upstream/main -- <conflicting_files>]

Determine:
1. Exact conflict locations (file:line_number)
2. Whether conflicts are in same code blocks or different sections
3. Which functions/classes are affected on each side
4. Dependency chain - what other code depends on conflicting code
5. If conflicts are truly overlapping or just adjacent

Output as structured markdown with severity recommendation.
```

#### Agent 2: Behavioral Analysis

**Purpose**: API signature and breaking change detection.

**Launch Command** (use Task tool with deepdive agent):

```
Analyze behavioral changes in the conflicting code:

CONFLICTING FILES:
[list of conflicting files]

BEFORE (our version):
[our current implementation of conflicting functions]

AFTER (upstream version):
[upstream implementation of conflicting functions]

Determine:
1. Function signature changes (params added/removed/changed)
2. Return type changes
3. Side effect changes (new mutations, I/O, state changes)
4. Breaking changes to public API surface
5. Behavioral differences that could cause runtime issues

Output as structured markdown with breaking change flags.
```

#### Agent 3: Integration Risk Assessment

**Purpose**: How our codebase uses the conflicting code.

**Launch Command** (use Task tool with deepdive agent):

```
Analyze how our fork uses the conflicting code:

CONFLICTING FILES:
[list of conflicting files]

TASK:
1. Find all imports of the conflicting files in our codebase:
   grep -r "from.*conflicting_file" --include="*.ts" --include="*.tsx"

2. Find all call sites of conflicting functions:
   [list specific functions to search for]

3. Check test coverage of affected areas:
   Find tests that import or test the conflicting code

4. Assess runtime risk:
   - What happens if merge goes wrong?
   - What user-facing features are affected?
   - What is the blast radius?

Output as structured markdown with risk matrix.
```

#### Merging Agent Results

After all agents complete, merge their findings:

```markdown
## Investigation Findings

### Structural Analysis

[Agent 1 findings]

- Conflict locations: [list]
- Overlap type: [same block / adjacent / separate]
- Dependencies affected: [list]

### Behavioral Analysis

[Agent 2 findings]

- API changes: [list]
- Breaking changes: [Yes/No - details]
- Side effect changes: [list]

### Integration Risk

[Agent 3 findings]

- Call sites affected: [count]
- Test coverage: [percentage or list]
- Risk level: [Low/Medium/High]
- Affected features: [list]

### Combined Severity Assessment

Based on investigation: [MEDIUM/HIGH/CRITICAL]
Reason: [explanation]
```

### Step 10: Resolution Strategy

Based on investigation findings, recommend a resolution approach:

#### Strategy Selection Matrix

| Severity | Overlap  | Breaking | Strategy              |
| -------- | -------- | -------- | --------------------- |
| NONE     | N/A      | N/A      | **Direct Merge**      |
| LOW      | No       | No       | **Merge with Review** |
| MEDIUM   | Adjacent | No       | **Merge + Verify**    |
| MEDIUM   | Same     | No       | **Manual Resolution** |
| HIGH     | Same     | No       | **Cherry-Pick**       |
| HIGH     | Any      | Yes      | **Staged Adoption**   |
| CRITICAL | Any      | Yes      | **Defer + Consult**   |

#### Strategy Descriptions

**Direct Merge** (Severity: NONE)

```markdown
## Resolution Strategy: Direct Merge

✅ No conflicts detected. Safe to merge directly.

### Commands

\`\`\`bash
git checkout main
git merge upstream/main
git push origin main
\`\`\`
```

**Merge with Review** (Severity: LOW)

```markdown
## Resolution Strategy: Merge with Review

⚠️ Minor conflicts in non-critical paths. Auto-resolve likely to work.

### Commands

\`\`\`bash
git checkout main
git merge upstream/main

# Review auto-resolved files:

git diff HEAD~1 -- [list of resolved files]
git push origin main
\`\`\`

### Files to Review Post-Merge

[list of files that had conflicts but were auto-resolved]
```

**Merge + Verify** (Severity: MEDIUM, adjacent overlap)

```markdown
## Resolution Strategy: Merge + Verify

⚠️ Conflicts in watch paths but in different code sections.

### Commands

\`\`\`bash
git checkout main
git merge upstream/main

# Resolve any conflicts manually

# Then verify:

npm run build
npm run test:all
git push origin main
\`\`\`

### Verification Checklist

- [ ] Build succeeds
- [ ] All tests pass
- [ ] Type exports unchanged
- [ ] No import errors
```

**Manual Resolution** (Severity: MEDIUM, same block)

```markdown
## Resolution Strategy: Manual Resolution

🔧 Conflicts require manual intervention in watch paths.

### Conflicting Sections

[list of exact locations from Agent 1]

### Resolution Guide

For each conflict:

1. Open the file
2. Find conflict markers (<<<<<<, ======, >>>>>>)
3. Decide which changes to keep:
   - Our change: [description]
   - Upstream change: [description]
4. Test the resolution

### Commands

\`\`\`bash
git checkout main
git merge upstream/main

# Manually resolve conflicts in:

[list of files]
git add [resolved files]
git commit -m "merge: resolve upstream conflicts manually"
npm run build && npm run test:all
git push origin main
\`\`\`
```

**Cherry-Pick** (Severity: HIGH)

```markdown
## Resolution Strategy: Cherry-Pick

🎯 High conflict severity. Recommend selective adoption.

### Recommended Commits to Cherry-Pick

[list of commits that don't conflict or have high value]

### Commands

\`\`\`bash

# Cherry-pick safe commits only:

git cherry-pick <commit1>
git cherry-pick <commit2>

# ...

# Skip conflicting commits for now:

# - <commit3>: [reason]

# - <commit4>: [reason]

git push origin main
\`\`\`

### Deferred Commits

These commits have conflicts and should be addressed separately:
[list with reasons]
```

**Staged Adoption** (Severity: HIGH with breaking changes)

```markdown
## Resolution Strategy: Staged Adoption

🚨 Breaking changes detected. Adopt in stages.

### Stage 1: Non-Breaking Changes

\`\`\`bash
git cherry-pick <non-breaking commits>
\`\`\`

### Stage 2: Prepare for Breaking Changes

[list of code changes needed in our fork first]

### Stage 3: Adopt Breaking Changes

After Stage 2 preparation:
\`\`\`bash
git cherry-pick <breaking commits>
npm run build
npm run test:all
\`\`\`

### Migration Guide

[steps to update our code for breaking changes]
```

**Defer + Consult** (Severity: CRITICAL)

```markdown
## Resolution Strategy: Defer + Consult

🛑 Critical conflicts detected. Do NOT merge automatically.

### Why Deferral is Recommended

[specific reasons from investigation]

### Recommended Actions

1. **Wait**: Upstream may still be in flux
2. **Discuss**: Consult team before proceeding
3. **Plan**: Create a dedicated branch for conflict resolution
4. **Test**: Extensive testing required before merge

### If You Must Proceed

\`\`\`bash

# Create a test branch first:

git checkout -b test/upstream-merge
git merge upstream/main

# Resolve all conflicts carefully

# Run full test suite

# Get team review before merging to main

\`\`\`

### Risk Assessment

[summary of what could go wrong]
```

---

## Compatibility Verification Checklist

After any merge, run these verification checks (if `investigation.verificationChecks` is configured):

| Check   | Command                                  | Pass Criteria                  |
| ------- | ---------------------------------------- | ------------------------------ |
| Build   | `npm run build`                          | Exit code 0                    |
| Tests   | `npm run test:all`                       | All tests pass                 |
| Types   | `npm run build:packages && tsc --noEmit` | No type errors                 |
| Imports | Check build output                       | No "cannot find module" errors |
| Exports | Compare public API                       | No removed exports             |

```bash
# Full verification script
echo "🔨 Building..."
npm run build || exit 1

echo "🧪 Testing..."
npm run test:all || exit 1

echo "📦 Checking types..."
npm run build:packages && npx tsc --noEmit || exit 1

echo "✅ All verification checks passed"
```

---

## Token Budget Guidelines

| Commits         | Approach                                          | Est. Tokens |
| --------------- | ------------------------------------------------- | ----------- |
| 1-20            | Full analysis + conflict check                    | ~5,000      |
| 21-50           | Group by type, priority analysis + conflict check | ~10,000     |
| 51-100          | Summary, breaking changes + conflict check        | ~15,000     |
| 100+            | Summary stats + basic conflict check              | ~8,000      |
| + Investigation | Add ~15,000-25,000 for sub-agents                 | Variable    |

## Example Commands

```bash
# Fetch and count new commits
git fetch upstream
git rev-list --count <last>..upstream/main

# Get commit messages only (token-efficient)
git log --format="%h %s" <last>..upstream/main

# Get files changed per commit
git log --format="%h" --name-only <last>..upstream/main

# Check if specific paths were touched
git log --oneline <last>..upstream/main -- apps/server/ libs/types/

# Get diff stats (not full diff)
git diff --stat <last>..upstream/main

# Simulate merge without actually merging
git merge-tree --write-tree HEAD upstream/main

# Get our changes to specific files (for investigation)
git diff upstream/main...HEAD -- <file>

# Get upstream changes to specific files
git diff <last>..upstream/main -- <file>
```

## Error Handling

| Issue                    | Action                                            |
| ------------------------ | ------------------------------------------------- |
| No config.json           | Create with sensible defaults, ask user to verify |
| No upstream remote       | Add it: `git remote add upstream <url>`           |
| Network error            | Report error, suggest retry                       |
| Too many commits         | Recommend more frequent checks                    |
| Merge conflicts detected | Proceed to Step 8-10 for investigation            |
| Sub-agent failure        | Fall back to basic conflict report                |
| Verification failure     | Report specific failure, recommend manual review  |

## Output Files

- Report: `.automaker-fork/reports/YYYY-MM-DD.md`
- Updated config: `.automaker-fork/config.json`

Always commit the report to the repository so there's a history of upstream tracking.

---

## Weekly Upstream Check Workflow (Recommended)

```
Run /upstream-check
       │
       ├─► Severity: NONE
       │   └─► Merge directly: git merge upstream/main
       │
       ├─► Severity: LOW
       │   └─► Merge with quick review of flagged files
       │
       ├─► Severity: MEDIUM
       │   ├─► Review investigation report
       │   └─► Decide: merge / cherry-pick / defer
       │
       ├─► Severity: HIGH
       │   ├─► Read full sub-agent analysis
       │   ├─► Manual conflict resolution plan
       │   └─► Test thoroughly before pushing
       │
       └─► Severity: CRITICAL
           ├─► Do NOT merge automatically
           ├─► Consult team
           └─► Consider waiting for upstream changes to stabilize
```
