# Worktree LLM Guide

This guide teaches LLM agents how to work with git worktrees in this codebase. All review and commit commands support worktree awareness.

## Worktree Structure

This repository uses git worktrees for isolated development:

```
/Users/ruben/Documents/GitHub/automaker/              # main repo
/Users/ruben/Documents/GitHub/automaker/.worktrees/
├── feature-1/                                         # port 3017/3018
└── feature-2/                                         # port 3027/3028
```

Each worktree has its own branch, uncommitted changes, and port configuration.

## Quick Selection

Use numbers for fast worktree selection:

| Shorthand | Worktree  | Branch    |
| --------- | --------- | --------- |
| `1`       | feature-1 | feature-1 |
| `2`       | feature-2 | feature-2 |

Example: `/sync 1` syncs feature-1, `/review 2` reviews feature-2.

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
/Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1  def5678 [feature-1]
/Users/ruben/Documents/GitHub/automaker/.worktrees/feature-2  ghi9012 [feature-2]
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

### Find Worktree by Name or Number

Use exact matching to avoid ambiguity:

```bash
# Find worktree path by name or number
find_worktree() {
  local selector="$1"
  local main_repo="/Users/ruben/Documents/GitHub/automaker"

  # Handle numeric shortcuts
  case "$selector" in
    1) echo "$main_repo/.worktrees/feature-1"; return 0 ;;
    2) echo "$main_repo/.worktrees/feature-2"; return 0 ;;
  esac

  # Search by name
  git worktree list | while read path hash branch; do
    if [[ "$path" == *"/$selector" ]]; then
      echo "$path"
      return 0
    fi
  done
}

# Usage
WORKTREE_PATH=$(find_worktree "1")        # Returns feature-1 path
WORKTREE_PATH=$(find_worktree "feature-2") # Returns feature-2 path
```

### Validate Worktree Exists

```bash
validate_worktree() {
  local selector="$1"
  local main_repo="/Users/ruben/Documents/GitHub/automaker"

  # Handle numeric shortcuts
  case "$selector" in
    1) selector="feature-1" ;;
    2) selector="feature-2" ;;
  esac

  local found=""
  while IFS= read -r line; do
    path=$(echo "$line" | awk '{print $1}')
    if [[ "$path" == *"/$selector" ]]; then
      found="$path"
      break
    fi
  done < <(git worktree list)

  if [ -z "$found" ]; then
    echo "Error: Worktree '$selector' not found."
    echo "Available worktrees:"
    echo "  1 = feature-1"
    echo "  2 = feature-2"
    git worktree list
    return 1
  fi

  echo "$found"
}
```

## Command Argument Patterns

All worktree-aware commands accept optional worktree selectors:

| Command         | No Argument           | With Number               | With Name                    |
| --------------- | --------------------- | ------------------------- | ---------------------------- |
| `/sync`         | Sync current worktree | `/sync 1` syncs feature-1 | `/sync feature-2`            |
| `/review`       | Reviews current       | `/review 1`               | `/review feature-2`          |
| `/deepreview`   | Current, auto-detect  | `/deepreview 1`           | `/deepreview feature-1 main` |
| `/smart-commit` | Commits in current    | `/smart-commit 1`         | `/smart-commit feature-2`    |

### Argument Parsing for Commands

The commands support flexible arguments:

- Number (`1`, `2`) → maps to worktree
- Worktree name (`feature-1`, `feature-2`) → exact match
- Branch name (`main`, `develop`) → target branch for comparison

**Detection logic:**

1. If argument is `1` or `2` → use as worktree selector
2. If argument matches a known worktree name → use as worktree
3. If argument matches a branch name → use as target branch
4. If both provided → first is worktree, second is branch

**Examples:**

```
/deepreview                    # Current worktree, auto-detect main/master
/deepreview 1                  # feature-1 worktree, auto-detect branch
/deepreview 2                  # feature-2 worktree, auto-detect branch
/deepreview develop            # Current worktree, compare to develop
/deepreview 1 develop          # feature-1 worktree, compare to develop
```

## Running Commands in a Worktree

When a worktree is specified, change to that directory before running git commands:

```bash
# Pattern for worktree-aware commands
run_in_worktree() {
  local selector="$1"
  shift
  local cmd="$@"
  local main_repo="/Users/ruben/Documents/GitHub/automaker"

  if [ -n "$selector" ]; then
    # Handle numeric shortcuts
    case "$selector" in
      1) selector="feature-1" ;;
      2) selector="feature-2" ;;
    esac

    # Find worktree path
    local worktree_path
    worktree_path=$(git worktree list | grep "/$selector " | awk '{print $1}')

    if [ -z "$worktree_path" ]; then
      echo "Error: Worktree '$selector' not found"
      echo "Use: 1 (feature-1) or 2 (feature-2)"
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
run_in_worktree "1" "git diff HEAD"      # feature-1
run_in_worktree "feature-2" "git status" # feature-2
run_in_worktree "" "git status"          # Current directory
```

## Context Reporting

Always report the worktree context at the start of operations:

```markdown
=== WORKTREE CONTEXT ===
Path: /Users/ruben/Documents/GitHub/automaker/.worktrees/feature-1
Branch: feature-1
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
2. List available shortcuts
3. List all available worktrees

```bash
echo "Error: Worktree '$selector' not found."
echo ""
echo "Quick shortcuts:"
echo "  1 = feature-1 (port 3017)"
echo "  2 = feature-2 (port 3027)"
echo ""
echo "Available worktrees:"
git worktree list
```

## Cross-Worktree Operations

Some operations may need to compare across worktrees:

```bash
# Compare changes between worktrees
compare_worktrees() {
  local wt1="$1"
  local wt2="$2"
  local main_repo="/Users/ruben/Documents/GitHub/automaker"

  # Handle numeric shortcuts
  case "$wt1" in 1) wt1="feature-1" ;; 2) wt1="feature-2" ;; esac
  case "$wt2" in 1) wt2="feature-1" ;; 2) wt2="feature-2" ;; esac

  local path1=$(git worktree list | grep "/$wt1 " | awk '{print $1}')
  local path2=$(git worktree list | grep "/$wt2 " | awk '{print $1}')

  if [ -n "$path1" ] && [ -n "$path2" ]; then
    diff -rq "$path1/src" "$path2/src" --exclude=node_modules
  fi
}
```

## Best Practices

1. **Use numeric shortcuts** - `1` and `2` are faster than full names
2. **Always validate worktree exists** before attempting operations
3. **Use exact matching** - require full worktree name to avoid ambiguity
4. **Report context clearly** - show path, branch, and ports at operation start
5. **Default to current** - when no argument provided, use current directory
6. **Handle errors gracefully** - list available worktrees when target not found
7. **Preserve working directory** - use subshells `(cd path && cmd)` to avoid changing cwd
