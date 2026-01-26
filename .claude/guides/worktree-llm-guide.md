# Worktree LLM Guide

This guide teaches LLM agents how to work with git worktrees in this codebase. All review and commit commands support worktree awareness.

## Worktree Structure

This repository uses git worktrees for isolated development:

```
/Users/ruben/Documents/GitHub/automaker/              # main repo
/Users/ruben/Documents/GitHub/automaker/.worktrees/
├── dev-improvements/                                  # port 3017/3018
└── reading-system/                                    # port 3027/3028
```

Each worktree has its own branch, uncommitted changes, and port configuration.

## Detection Commands

### Get All Worktrees (Dynamic)

```bash
# List all worktrees with full paths
git worktree list --porcelain | grep "^worktree" | cut -d' ' -f2-

# Human-readable format with branch names
git worktree list
```

Output example:

```
/Users/ruben/Documents/GitHub/automaker              abc1234 [main]
/Users/ruben/Documents/GitHub/automaker/.worktrees/dev-improvements  def5678 [dev/improvements]
```

### Get Current Worktree Context

```bash
# Current worktree path
git rev-parse --show-toplevel

# Current branch name
git branch --show-current

# Combined context
echo "Path: $(git rev-parse --show-toplevel)"
echo "Branch: $(git branch --show-current)"
```

### Find Worktree by Name

Use exact matching to avoid ambiguity:

```bash
# Find worktree path by name (searches the last path component)
find_worktree() {
  local name="$1"
  git worktree list | while read path hash branch; do
    # Check if path ends with the worktree name
    if [[ "$path" == *"/$name" ]] || [[ "$path" == *"$name" && "$path" != *"/"* ]]; then
      echo "$path"
      return 0
    fi
  done
}

# Usage
WORKTREE_PATH=$(find_worktree "dev-improvements")
```

### Validate Worktree Exists

```bash
validate_worktree() {
  local name="$1"
  local found=""

  while IFS= read -r line; do
    path=$(echo "$line" | awk '{print $1}')
    if [[ "$path" == *"/$name" ]]; then
      found="$path"
      break
    fi
  done < <(git worktree list)

  if [ -z "$found" ]; then
    echo "Error: Worktree '$name' not found."
    echo "Available worktrees:"
    git worktree list
    return 1
  fi

  echo "$found"
}
```

## Command Argument Patterns

All worktree-aware commands accept optional worktree names:

| Command                    | No Argument                          | With Argument                 |
| -------------------------- | ------------------------------------ | ----------------------------- |
| `/review`                  | Reviews current worktree             | Reviews specified worktree    |
| `/review dev-improvements` | -                                    | Reviews dev-improvements      |
| `/deepreview`              | Current worktree, auto-detect branch | Worktree and/or branch        |
| `/smart-commit`            | Commits in current worktree          | Commits in specified worktree |

### Argument Parsing for Deepreview

The `/deepreview` command supports two optional arguments:

- Worktree name (path component like `dev-improvements`)
- Target branch (git ref like `main`, `develop`)

**Detection logic:**

1. If argument matches a known worktree name → use as worktree
2. If argument matches a branch name → use as target branch
3. If both provided → first is worktree, second is branch

**Examples:**

```
/deepreview                           # Current worktree, auto-detect main/master
/deepreview dev-improvements          # dev-improvements worktree, auto-detect branch
/deepreview develop                   # Current worktree, compare to develop
/deepreview dev-improvements develop  # dev-improvements worktree, compare to develop
```

## Running Commands in a Worktree

When a worktree is specified, change to that directory before running git commands:

```bash
# Pattern for worktree-aware commands
run_in_worktree() {
  local worktree_name="$1"
  shift
  local cmd="$@"

  if [ -n "$worktree_name" ]; then
    # Find worktree path
    local worktree_path
    worktree_path=$(git worktree list | grep "/$worktree_name " | awk '{print $1}')

    if [ -z "$worktree_path" ]; then
      echo "Error: Worktree '$worktree_name' not found"
      git worktree list
      return 1
    fi

    # Execute in worktree
    (cd "$worktree_path" && eval "$cmd")
  else
    # Execute in current directory
    eval "$cmd"
  fi
}

# Usage
run_in_worktree "dev-improvements" "git diff HEAD"
run_in_worktree "" "git status"  # Current directory
```

## Context Reporting

Always report the worktree context at the start of operations:

```markdown
=== WORKTREE CONTEXT ===
Path: /Users/ruben/Documents/GitHub/automaker/.worktrees/dev-improvements
Branch: dev/improvements
Port Config: 3017/3018
========================
```

## Port Configuration

Each worktree has a `.env` file with unique ports. When reporting worktree context, include port info:

```bash
# Read port configuration from worktree
get_worktree_ports() {
  local worktree_path="$1"

  if [ -f "$worktree_path/.env" ]; then
    local ui_port=$(grep "^TEST_PORT=" "$worktree_path/.env" | cut -d'=' -f2)
    local server_port=$(grep "^PORT=" "$worktree_path/.env" | cut -d'=' -f2)
    echo "UI: $ui_port, Server: $server_port"
  else
    echo "Using default ports (3007/3008)"
  fi
}
```

## Error Handling

When a worktree is not found:

1. Report the error clearly
2. List all available worktrees
3. Ask for clarification

```bash
echo "Error: Worktree '$name' not found."
echo ""
echo "Available worktrees:"
git worktree list
echo ""
echo "Did you mean one of these?"
```

## Cross-Worktree Operations

Some operations may need to compare across worktrees:

```bash
# Compare changes between worktrees
compare_worktrees() {
  local wt1="$1"
  local wt2="$2"

  local path1=$(git worktree list | grep "/$wt1 " | awk '{print $1}')
  local path2=$(git worktree list | grep "/$wt2 " | awk '{print $1}')

  if [ -n "$path1" ] && [ -n "$path2" ]; then
    diff -rq "$path1/src" "$path2/src" --exclude=node_modules
  fi
}
```

## Best Practices

1. **Always validate worktree exists** before attempting operations
2. **Use exact matching** - require full worktree name to avoid ambiguity
3. **Report context clearly** - show path, branch, and ports at operation start
4. **Default to current** - when no argument provided, use current directory
5. **Handle errors gracefully** - list available worktrees when target not found
6. **Preserve working directory** - use subshells `(cd path && cmd)` to avoid changing cwd
