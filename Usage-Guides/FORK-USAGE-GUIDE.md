# Fork Management Usage Guide

A simple guide to managing your customized AutoMaker fork while tracking upstream changes.

---

## Quick Reference

| Task | Command/Action |
|------|----------------|
| Check for upstream updates | Ask Claude: "Run an upstream check" |
| View latest report | Open `.automaker-fork/reports/` |
| Adopt a feature | `git cherry-pick <commit-hash>` |
| Update upstream mirror | `git fetch upstream` |
| Compare branches | `git diff main..upstream` |

---

## Your Setup

```
Your Fork (GitHub)
├── main branch      → Your modified version (work here)
└── upstream branch  → Clean mirror of original (don't touch)

Remotes:
├── origin   → github.com/TheGuidingPrincipels/automaker (your fork)
└── upstream → github.com/AutoMaker-Org/automaker (original)
```

---

## Daily Workflow

### 1. Making Your Modifications

Work on the `main` branch as normal:

```bash
cd automaker
git checkout main

# Make your changes
git add .
git commit -m "feat: your awesome improvement"
git push origin main
```

### 2. Checking for Upstream Changes (Every 3-5 Days)

**Option A - Ask Claude:**
```
"Run an upstream check on the automaker fork"
```

**Option B - Manual check:**
```bash
git fetch upstream
git log --oneline HEAD..upstream/main
```

### 3. Reading the Report

Reports are saved to `.automaker-fork/reports/YYYY-MM-DD.md`

**Key sections to focus on:**
- **Breaking Changes** - Review immediately
- **New Features** - Decide: Adopt / Skip / Defer
- **Recommendations** - Actionable next steps

---

## Adopting Upstream Features

### Simple: Cherry-Pick a Commit

When a single commit has what you need:

```bash
# Create a staging branch
git checkout -b staging main

# Cherry-pick the commit
git cherry-pick <commit-hash>

# If conflicts, resolve them, then:
git add .
git cherry-pick --continue

# Test your changes, then merge
git checkout main
git merge staging
git branch -d staging
```

### Complex: Reimplement the Feature

When upstream changes conflict heavily with your structure:

1. Read the upstream implementation for design insights
2. Implement your own version aligned with your architecture
3. Document in `.automaker-fork/adopted/manifest.json`

---

## Key Files

| File | Purpose |
|------|---------|
| `.automaker-fork/config.json` | Tracking settings & last check timestamp |
| `.automaker-fork/reports/*.md` | Generated analysis reports |
| `.automaker-fork/adopted/manifest.json` | Record of adopted/rejected features |

### Config Settings You Can Customize

Edit `.automaker-fork/config.json`:

```json
{
  "tracking": {
    "checkFrequencyDays": 3  // How often to check (3-7 recommended)
  },
  "analysis": {
    "watchPaths": [          // Directories you care most about
      "apps/server/",
      "apps/ui/",
      "libs/types/"
    ],
    "skipPatterns": [        // Commit types to skip
      "^docs:",
      "^test:",
      "^ci:"
    ]
  }
}
```

---

## Common Scenarios

### "I want to see what changed upstream"

```bash
# Quick overview
git fetch upstream
git log --oneline main..upstream/main | head -20

# Detailed with files
git log --stat main..upstream/main
```

### "I want to update my upstream branch"

```bash
git checkout upstream
git pull upstream main
git push origin upstream
git checkout main
```

### "A merge conflict happened during cherry-pick"

```bash
# See which files conflict
git status

# Edit the conflicted files, resolve the markers (<<<<, ====, >>>>)
# Then:
git add <resolved-files>
git cherry-pick --continue
```

### "I want to abandon a cherry-pick"

```bash
git cherry-pick --abort
```

### "I want to see the diff between my version and upstream"

```bash
# Summary
git diff --stat main..upstream/main

# Full diff (can be large)
git diff main..upstream/main

# Specific directory only
git diff main..upstream/main -- apps/ui/
```

---

## Maintenance Schedule

| Frequency | Task |
|-----------|------|
| Every 3-5 days | Run upstream check, review report |
| Weekly | Decide on feature adoptions |
| Per upstream release | Comprehensive review, update upstream branch to release tag |

---

## Troubleshooting

### "upstream remote not found"

```bash
git remote add upstream https://github.com/AutoMaker-Org/automaker.git
git fetch upstream
```

### "Reports directory is missing"

```bash
mkdir -p .automaker-fork/reports
```

### "Config file is missing"

Ask Claude to regenerate it, or copy from this template:

```json
{
  "fork": {
    "originalRepo": "AutoMaker-Org/automaker",
    "forkRepo": "TheGuidingPrincipels/automaker"
  },
  "tracking": {
    "lastCheckedCommit": "<run git rev-parse HEAD>",
    "lastCheckedAt": "<current date>",
    "checkFrequencyDays": 3
  }
}
```

---

## Tips for Heavy Modifications

Since you're making significant structural changes:

1. **Document your changes** - Keep notes on what you've modified
2. **Check upstream frequently** - High activity repo (~250 commits/week)
3. **Prefer reimplementation** over cherry-pick when structures differ
4. **Focus on features, not refactors** - Skip upstream refactors that conflict
5. **Track what you adopt** - Update `adopted/manifest.json`

---

## Getting Help

Ask Claude:
- "Run an upstream check"
- "What's new in upstream since last check?"
- "Help me cherry-pick commit X"
- "Show me the diff for feature Y in upstream"
- "Should I adopt this upstream change given my modifications?"

---

*Last updated: 2026-01-18*
