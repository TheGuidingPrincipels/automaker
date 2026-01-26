---
description: Run checks, generate perfect commit message, and commit
---

# Smart Commit Workflow

This workflow streamlines the commit process by ensuring code quality, generating a standardized commit message, and executing the commit.

## Worktree Support

This command accepts an optional worktree selector via `$ARGUMENTS`:

- `/smart-commit` - Commits in current worktree
- `/smart-commit 1` or `/smart-commit feature-1` - Commits in feature-1 worktree
- `/smart-commit 2` or `/smart-commit feature-2` - Commits in feature-2 worktree

## Steps

0.  **Determine Worktree Context**

    If `$ARGUMENTS` contains a worktree name, find and switch to that worktree:

    ```bash
    # Parse optional worktree argument
    WORKTREE_NAME="$ARGUMENTS"

    if [ -n "$WORKTREE_NAME" ]; then
      # Find worktree path by name
      WORKTREE_PATH=$(git worktree list | grep "/$WORKTREE_NAME " | awk '{print $1}')

      if [ -z "$WORKTREE_PATH" ]; then
        echo "Error: Worktree '$WORKTREE_NAME' not found."
        echo ""
        echo "Available worktrees:"
        git worktree list
        exit 1
      fi

      # Change to worktree directory
      cd "$WORKTREE_PATH"
    fi

    # Report context
    echo "=== WORKTREE CONTEXT ==="
    echo "Path: $(git rev-parse --show-toplevel)"
    echo "Branch: $(git branch --show-current)"
    echo "========================"
    ```

    All subsequent git commands will run in the target worktree context.

1.  **Pre-Commit Check**
    - **Action**: Internal check - "Has the user run `/review` recently?" or "Are there critical issues pending?"
    - **Auto-Review**: Ideally, run a lightweight version of the `/review` workflow (e.g., just blocking issues).
    - _Condition_: If Critical/Blocking issues are found -> **ABORT** and report them. The user must fix them or explicitly override (with a reason).

2.  **Generate Commit Message**
    - **Context**: Read the `git diff --cached` (staged changes). If nothing staged, ask if user wants to stage all (`git add .`) or pick files.
    - **Format**: Use **Conventional Commits** standard (`<type>(<scope>): <subject>`).
      - **Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `build`, `ci`, `revert`.
    - **Body**: detailed explanation of _what_ changed and _why_.
    - **Footer**: "BREAKING CHANGE: ..." if applicable, or "Closes #123" if it fixes an issue.
    - **Draft**: Present the generated message to the user.

3.  **User Confirmation**
    - **Prompt**: "Here is the proposed commit message. Does this look good?"

      ```text
      feat(auth): implement jwt token rotation

      Added a new middleware to handle token expiration...
      ```

    - **Options**:
      - `Yes` -> Proceed.
      - `Edit` -> User provides feedback to refine the message.
      - `Cancel` -> Abort.

4.  **Execute Commit**
    - **Command**: `git commit -m "Generated Message"`
    - _Verification_: Check exit code.

5.  **Post-Commit (Optional)**
    - **Prompt**: "Would you like to push changes or create a PR?"
    - **Push**: `git push origin HEAD`
    - **PR**: `gh pr create --fill` (requires `gh` CLI).

## Usage

- Just run `/smart-commit`.
- Ensure you have staged your files, or be ready to stage them during the workflow.
