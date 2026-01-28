---
description: Comprehensive codebase review (Quality, Security, Speed)
---

# Review Workflow

This workflow performs a deep analysis of your current uncommitted changes. It acts as a gatekeeper to ensure only high-quality, secure, and performant code is committed.

## Worktree Support

This command accepts an optional worktree selector via `$ARGUMENTS`:

- `/review` - Reviews current worktree
- `/review 1` or `/review feature-1` - Reviews feature-1 worktree
- `/review 2` or `/review feature-2` - Reviews feature-2 worktree

> [!IMPORTANT]
> **Agent Note**: If the worktree path is outside the active workspace, standard `run_command` may fail with "path is not in a workspace" error. In this case:
>
> 1. Use `mcp_cipher_cipher_bash` tool instead of `run_command`
> 2. Always `cd` to the worktree path at the start of each command
> 3. Example: `cd /path/to/worktree && git diff HEAD`

## Steps

0.  **Determine and Prepare Worktree Context**

    Use the provided argument to switch worktrees if necessary, and ensure untracked files are included.

    ```bash
    TARGET_TREE="$ARGUMENTS"

    # 1. Switch Worktree if argument provided
    if [ -n "$TARGET_TREE" ]; then
      # Find worktree path (fuzzy match)
      # We look for a line in 'git worktree list' matched by the argument
      WT_LINE=$(git worktree list | grep -- "$TARGET_TREE" | head -n 1)

      if [ -z "$WT_LINE" ]; then
        echo "Error: Worktree matching '$TARGET_TREE' not found."
        echo ""
        echo "Available worktrees:"
        git worktree list
        exit 1
      fi

      WT_PATH=$(echo "$WT_LINE" | awk '{print $1}')
      echo "Switching to worktree: $WT_PATH"
      cd "$WT_PATH"
    else
      echo "Running in current directory: $(pwd)"
    fi

    # 2. Prepare Context (Include Untracked Files)
    # 'git add -N .' creates an intent-to-add for untracked files,
    # allowing them to be captured by 'git diff HEAD' as new files.
    git add -N . 2>/dev/null || true

    echo "=== REVIEW CONTEXT ==="
    echo "Path: $(git rev-parse --show-toplevel)"
    echo "Branch: $(git branch --show-current)"
    echo "======================"
    ```

    All subsequent git commands will run in the target worktree context.

1.  **Analyze Context**
    - Target: Uncommitted changes (including new/untracked files).
    - Command: `git diff HEAD` (captures staged, unstaged, and intent-to-add files).
    - _Agent Note references_: If the diff is too large, suggest reviewing specific files or asking the user to split the commit.

2.  **Quality Check**
    - **Readability**: Is the code easy to understand? Are variable names descriptive?
    - **Patterns**: Does it follow the codebase's established patterns (e.g., specific libraries, architectural choices)?
    - **Bugs**: Are there obvious logic errors, off-by-one errors, or unhandled null states?
    - _Action_: List any "Required Improvements" that must be fixed before committing.

3.  **Security Check**
    - **Secrets**: Are there any API keys, tokens, or passwords hardcoded?
    - **Vulnerabilities**: Are there injection risks (SQL, XSS), unsafe deserialization, or insecure configuration?
    - **Permissions**: excessive permission grants?
    - _Action_: Mark these as **CRITICAL**. These are show-stoppers.

4.  **Speed/Performance Check**
    - **Complexity**: Are there O(n^2) or worse loops? deeply nested conditionals?
    - **Resources**: Memory leaks, unclosed connections, heavy imports?
    - _Action_: Suggest optimizations under "Recommended Improvements".

5.  **Report Generation**
    - Generate a structured report in Markdown.

    **Format:**

    ```markdown
    # 🔍 Code Review Report

    ## 🛑 Blocking Issues (Must Fix)

    - [File.ts:L12] **Security**: Hardcoded API key found.
    - [File.ts:L45] **Bug**: Potential null pointer exception.

    ## ⚠️ Warnings (Should Fix)

    - [File.ts:L20] **Quality**: Variable name `x` is unclear.

    ## 💡 Suggestions (Nice to Have)

    - [File.ts:L50] **Speed**: Optimize loop by caching length.

    ## ✅ Verdict

    [Pass / Fail]
    ```

6.  **Remediation Plan (If Failed)**
    - If the verdict is **Fail**, briefly outline _how_ to fix the Blocking Issues.
    - Ask the user: "Would you like me to attempt to fix these issues for you?"

## Options

- `quality`: Run only quality checks.
- `security`: Run only security checks.
- `speed`: Run only performance checks.
- Default: Run all.
