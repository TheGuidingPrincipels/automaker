# Commands Meta Guide

Guide for creating, updating, and managing slash commands in this repository.

## Philosophy

Our command system follows a **token-efficient architecture**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLAUDE.md (~85 lines)                        │
│              Always loaded, minimal footprint                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   /automaker-arch    /worktree    /test-guide    /env    ...   │
│                                                                 │
│              Detailed context loaded on-demand                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│              .automaker/context/*.md                            │
│              (For Automaker AI agents)                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Principle**: Downstream Claude Code sessions start with minimal context. Detailed information is loaded only when needed via commands.

## Existing Commands

### Architecture & Development

| Command           | File                | Purpose                          |
| ----------------- | ------------------- | -------------------------------- |
| `/automaker-arch` | `automaker-arch.md` | Full architecture reference      |
| `/new-feature`    | `new-feature.md`    | Feature-first architecture guide |
| `/env`            | `env.md`            | Environment variables reference  |

### Worktree & Git

| Command     | File          | Purpose                     |
| ----------- | ------------- | --------------------------- |
| `/worktree` | `worktree.md` | Port allocation, .env setup |
| `/sync`     | `sync.md`     | Worktree sync workflow      |

### Testing

| Command           | File                | Purpose                |
| ----------------- | ------------------- | ---------------------- |
| `/test-guide`     | `test-guide.md`     | Complete testing guide |
| `/validate-tests` | `validate-tests.md` | Run and fix tests      |
| `/validate-build` | `validate-build.md` | Run and fix builds     |

### Knowledge Library

| Command            | File                 | Purpose                  |
| ------------------ | -------------------- | ------------------------ |
| `/ai-library-api`  | `ai-library-api.md`  | Backend API reference    |
| `/ai-library-ui`   | `ai-library-ui.md`   | Frontend components      |
| `/session-cleanup` | `session-cleanup.md` | Cleanup workflow details |

### Code Review

| Command       | File            | Purpose                      |
| ------------- | --------------- | ---------------------------- |
| `/review`     | `review.md`     | Deep code review (10 agents) |
| `/deepreview` | `deepreview.md` | Extended review              |
| `/thorough`   | `thorough.md`   | 3-pass verification          |

### Other

| Command           | File                             | Purpose                |
| ----------------- | -------------------------------- | ---------------------- |
| `/upstream-check` | `skills/upstream-check/SKILL.md` | Fork upstream tracking |
| `/dev-setup`      | `dev-setup.md`                   | Dev worktree setup     |
| `/release`        | `release.md`                     | Version bump workflow  |
| `/gh-issue`       | `gh-issue.md`                    | GitHub issue handling  |
| `/automaker-ui`   | `automaker-ui.md`                | Browser automation     |

## File Locations

```
.claude/
├── commands/           # Slash commands (this directory)
│   ├── automaker-arch.md
│   ├── worktree.md
│   ├── test-guide.md
│   └── ... (all *.md files become /command-name)
├── skills/             # Skills with YAML frontmatter
│   └── upstream-check/SKILL.md
├── agents/             # Agent definitions (@deepdive, @deepcode, etc.)
└── guides/             # General guidance documents

.automaker/
└── context/            # Context for Automaker AI agents
    ├── architecture.md
    ├── knowledge-hub.md
    ├── testing.md
    ├── worktree.md
    └── context-metadata.json

Root:
├── CLAUDE.md           # Slim, always-loaded context
└── .commands.md        # Developer guide (this guide)
```

## Creating a New Command

### Step 1: Identify the Need

Ask yourself:

- Is this information needed frequently? → Consider adding to CLAUDE.md
- Is this detailed, situational context? → Create a command
- Will Automaker agents need this? → Also create context file

### Step 2: Create Command File

Create `.claude/commands/{command-name}.md`:

```markdown
# Command Title

Brief description of what this command provides.

## Overview

High-level explanation.

## Key Information

Tables, code blocks, structured content.

## When to Use

- Scenario 1
- Scenario 2

## Key Files

| File              | Purpose     |
| ----------------- | ----------- |
| `path/to/file.ts` | Description |
```

### Step 3: Update Developer Guide

Edit `.commands.md` in repo root:

1. Add to Quick Reference table
2. Add detailed section in appropriate category
3. Update Decision Flowchart if applicable

### Step 4: For Automaker Agents (Optional)

If Automaker's AI agents need this context:

1. Create `.automaker/context/{name}.md` with condensed version
2. Update `.automaker/context/context-metadata.json`:

```json
{
  "files": {
    "existing.md": { "description": "..." },
    "new-file.md": { "description": "Brief description for relevance scoring" }
  }
}
```

## Updating Existing Commands

### Checklist

1. **Read current content**: Understand existing structure
2. **Make targeted edits**: Don't restructure unnecessarily
3. **Update related files**:
   - [ ] `.commands.md` if command purpose/usage changed
   - [ ] `.automaker/context/` if Automaker agents need updates
   - [ ] `CLAUDE.md` if core info changed (rare)
4. **Keep token-efficient**: Don't add unnecessary verbosity

### When to Update

- New feature added that command should document
- Information became outdated
- User feedback indicates confusion
- Related codebase changed significantly

## Token Efficiency Guidelines

### Do

- Use tables for structured data
- Use code blocks for commands/paths
- Keep explanations concise
- Use headers for scanability
- Include "When to Use" sections

### Don't

- Duplicate information across commands
- Add verbose explanations for simple concepts
- Include full file contents (reference paths instead)
- Add examples for obvious usage

### Size Guidelines

| Command Type               | Target Size   |
| -------------------------- | ------------- |
| Reference (env, worktree)  | 100-150 lines |
| Architecture               | 150-250 lines |
| Workflow (session-cleanup) | 200-300 lines |
| CLAUDE.md                  | <100 lines    |

## Command Naming

| Pattern          | Example          | Use For           |
| ---------------- | ---------------- | ----------------- |
| `{feature}-arch` | `automaker-arch` | Architecture docs |
| `{feature}-api`  | `ai-library-api` | API references    |
| `{feature}-ui`   | `ai-library-ui`  | UI components     |
| `{action}`       | `sync`, `review` | Workflow commands |
| `{noun}-guide`   | `test-guide`     | How-to guides     |

## Context Files vs Commands

| Aspect       | Commands (`.claude/commands/`) | Context (`.automaker/context/`) |
| ------------ | ------------------------------ | ------------------------------- |
| Used by      | Claude Code sessions           | Automaker AI agents             |
| Invocation   | `/command-name`                | Automatic (relevance-based)     |
| Detail level | Comprehensive                  | Condensed essentials            |
| Updates      | Manual via this guide          | Manual, keep in sync            |

## Quality Checklist

Before finalizing a new/updated command:

- [ ] Clear title and purpose
- [ ] Structured with headers and tables
- [ ] "When to Use" section included
- [ ] Key files/paths referenced
- [ ] No duplicate info from other commands
- [ ] `.commands.md` updated
- [ ] Context file created/updated (if needed)
- [ ] Tested by invoking the command

## Example: Creating `/my-feature` Command

```bash
# 1. Create command file
touch .claude/commands/my-feature.md

# 2. Write content (see template above)

# 3. Update developer guide
# Edit .commands.md - add to table and create section

# 4. If Automaker agents need it:
touch .automaker/context/my-feature.md
# Edit context-metadata.json

# 5. Test
# Start new Claude Code session, invoke /my-feature
```
