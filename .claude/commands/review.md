# Code Review Command

Comprehensive code review using multiple deep dive agents to analyze changes for correctness, security, code quality, and tech stack compliance, followed by automated fixes using deepcode agents.

## Usage

This command analyzes changes and verifies:

1. **Invalid code based on tech stack** (HIGHEST PRIORITY)
2. Security vulnerabilities
3. Code quality issues (dirty code)
4. Implementation correctness

Then automatically fixes any issues found (or defers severe+uncertain issues to user).

### Arguments

This command supports two optional arguments via `$ARGUMENTS`:

- **Worktree selector**: `1` for feature-1, `2` for feature-2, or full worktree name
- **Target branch**: Branch name to compare against (e.g., `develop`, `main`)

**Examples:**

| Command             | Review Mode       | Scope                                     |
| ------------------- | ----------------- | ----------------------------------------- |
| `/review`           | Working directory | Uncommitted changes in current worktree   |
| `/review 1`         | Working directory | Uncommitted changes in feature-1 worktree |
| `/review main`      | Branch comparison | Current branch vs main                    |
| `/review develop`   | Branch comparison | Current branch vs develop                 |
| `/review 1 develop` | Branch comparison | feature-1 branch vs develop               |

**Argument Detection Logic:**

1. If argument matches a known worktree name → use as worktree
2. If argument matches a branch name → use as target branch
3. If two arguments → first is worktree, second is target branch

**Review Modes:**

- **Working directory mode** (default): Reviews uncommitted changes (`git diff HEAD`)
- **Branch comparison mode**: Reviews all changes between branches (`git diff $TARGET_REF...HEAD`)

## Instructions

### Phase 0: Parse Arguments and Determine Context

1. **Parse `$ARGUMENTS`** (may contain worktree name, target branch, or both)

   ```bash
   # Split arguments
   ARG1=$(echo "$ARGUMENTS" | awk '{print $1}')
   ARG2=$(echo "$ARGUMENTS" | awk '{print $2}')

   # Initialize variables
   WORKTREE_NAME=""
   TARGET_BRANCH=""
   REVIEW_MODE="working"  # Default: working directory review

   # Get list of worktree names
   WORKTREE_NAMES=$(git worktree list | awk '{print $1}' | xargs -I{} basename {})

   # Check if ARG1 is a worktree name or branch
   if echo "$WORKTREE_NAMES" | grep -qx "$ARG1" 2>/dev/null; then
     WORKTREE_NAME="$ARG1"
     # ARG2 might be target branch
     if [ -n "$ARG2" ]; then
       TARGET_BRANCH="$ARG2"
       REVIEW_MODE="branch"
     fi
   elif [ -n "$ARG1" ]; then
     # ARG1 is likely a branch name
     TARGET_BRANCH="$ARG1"
     REVIEW_MODE="branch"
   fi
   ```

2. **Switch to worktree if specified**

   ```bash
   if [ -n "$WORKTREE_NAME" ]; then
     # Find worktree path
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
     echo "Switched to worktree: $WORKTREE_PATH"
   fi
   ```

3. **Validate target branch (if branch mode)**

   ```bash
   if [ "$REVIEW_MODE" = "branch" ]; then
     # Verify target branch exists
     if ! git show-ref --verify --quiet refs/heads/$TARGET_BRANCH && \
        ! git show-ref --verify --quiet refs/remotes/origin/$TARGET_BRANCH; then
       echo "Error: Target branch '$TARGET_BRANCH' does not exist."
       echo ""
       echo "Available branches:"
       git branch -a | head -20
       exit 1
     fi

     # Determine ref to use (local or remote)
     if git show-ref --verify --quiet refs/heads/$TARGET_BRANCH; then
       TARGET_REF=$TARGET_BRANCH
     else
       TARGET_REF=origin/$TARGET_BRANCH
     fi
   fi
   ```

4. **Report context**

   ```bash
   echo "=== REVIEW CONTEXT ==="
   echo "Path: $(git rev-parse --show-toplevel)"
   echo "Branch: $(git branch --show-current)"
   echo "Mode: $REVIEW_MODE"

   if [ "$REVIEW_MODE" = "branch" ]; then
     echo "Target: $TARGET_BRANCH"

     # Show branch relationship
     AHEAD=$(git rev-list --count $TARGET_REF..HEAD 2>/dev/null || echo "?")
     BEHIND=$(git rev-list --count HEAD..$TARGET_REF 2>/dev/null || echo "?")
     echo "Commits: $AHEAD ahead, $BEHIND behind $TARGET_BRANCH"
   fi

   # Show port configuration if .env exists
   if [ -f ".env" ]; then
     echo "Ports: UI=$(grep '^TEST_PORT=' .env | cut -d'=' -f2), Server=$(grep '^PORT=' .env | cut -d'=' -f2)"
   fi
   echo "======================="
   ```

### Phase 1: Collect Metadata (Lean Context)

**IMPORTANT**: This phase collects ONLY metadata. DO NOT read file contents - agents will read files themselves.

1. **Get diff statistics** (not full diff content)

   ```bash
   if [ "$REVIEW_MODE" = "branch" ]; then
     # Branch comparison stats
     git diff --stat $TARGET_REF...HEAD
   else
     # Working directory stats
     git diff --stat HEAD
     git diff --stat --cached
   fi
   ```

2. **Get list of changed files**

   ```bash
   if [ "$REVIEW_MODE" = "branch" ]; then
     # Files changed between branches
     git diff --name-only $TARGET_REF...HEAD

     # Plus any uncommitted changes on top
     git diff --name-only HEAD
     git diff --name-only --cached
   else
     # Modified files (working directory)
     git diff --name-only HEAD

     # Staged files
     git diff --name-only --cached
   fi
   ```

3. **Get untracked files** (new files not yet added to git)

   ```bash
   git ls-files --others --exclude-standard
   ```

   **DO NOT read untracked file contents** - agents will read them.

4. **Get commit log (branch mode only)**

   ```bash
   if [ "$REVIEW_MODE" = "branch" ]; then
     # Show commits that will be reviewed
     git log --oneline $TARGET_REF..HEAD
   fi
   ```

5. **Categorize all changes** (metadata only)

   Create a summary table:

   | Category                   | Count | Files         |
   | -------------------------- | ----- | ------------- |
   | Branch changes (committed) | X     | list files... |
   | Modified (uncommitted)     | X     | list files... |
   | Staged                     | X     | list files... |
   | Untracked (new)            | X     | list files... |
   | **Total unique files**     | X     |               |

6. **Identify file types** for agent routing

   Categorize files by domain:
   - **Frontend**: `apps/ui/**`, `*.tsx`, `*.css`
   - **Backend**: `apps/server/**`, routes, services
   - **Shared**: `libs/**`
   - **Config**: `*.json`, `*.config.*`, `.env*`
   - **Tests**: `*.test.ts`, `*.spec.ts`

7. **Note the tech stack** (agents will verify against this):
   - **Node.js**: >=22.0.0 <23.0.0
   - **TypeScript**: 5.9.3
   - **React**: 19.2.3
   - **Express**: 5.2.1
   - **Electron**: 39.2.7
   - **Vite**: 7.3.0
   - **Vitest**: 4.0.16

### Phase 2: Deep Dive Analysis (5 Agents)

Launch 5 separate deep dive agents, each with a specific focus area. Each agent should be invoked with the `@deepdive` agent.

**IMPORTANT: Delegated File Reading Architecture**

To avoid context bloat in the main session, agents read files themselves:

1. **Main session provides ONLY**:
   - List of file paths to analyze (from Phase 1)
   - Diff statistics (lines changed per file)
   - File categorization (frontend/backend/shared/tests)
   - Tech stack versions to validate against
   - **Review mode** (working or branch) and target ref if applicable

2. **Each agent MUST**:
   - Read the files assigned to them using the Read tool
   - Run appropriate git diff command to see specific changes:
     - **Working mode**: `git diff HEAD -- <file>`
     - **Branch mode**: `git diff $TARGET_REF...HEAD -- <file>`
   - Read related files as needed for context
   - Focus on their specific domain

3. **Agent file reading strategy**:
   - For MODIFIED files: Run appropriate `git diff` to see changes
   - For UNTRACKED files: Read full file content (no diff exists)
   - For CONTEXT: Read imports/related files as needed

**Benefits of this approach**:

- Main session stays lean (~5-10k tokens)
- Each agent has fresh context for their files
- Agents can read additional context files as needed
- Scales to any number of changed files

#### Agent 1: Tech Stack Validation (HIGHEST PRIORITY)

**Focus:** Verify code is valid for the tech stack

**Input:** List of files to analyze, tech stack versions, review mode

**Instructions for Agent 1:**

```
STEP 0: READ THE FILES (Required First Step)

For each file in your assigned list:
- MODIFIED files: Run `git diff HEAD -- <filepath>` (or `git diff $TARGET_REF...HEAD -- <filepath>` for branch mode)
- UNTRACKED files: Use Read tool to get full content
- Read any imported files if needed for type checking

Then analyze for invalid code based on the tech stack:

1. **TypeScript/JavaScript Syntax**
   - Check for valid TypeScript syntax (no invalid type annotations, correct import/export syntax)
   - Verify Node.js API usage is compatible with Node.js >=22.0.0 <23.0.0
   - Check for deprecated APIs or features not available in the Node.js version
   - Verify ES module syntax (type: "module" in package.json)

2. **React 19.2.3 Compatibility**
   - Check for deprecated React APIs or patterns
   - Verify hooks usage is correct for React 19
   - Check for invalid JSX syntax
   - Verify component patterns match React 19 conventions

3. **Express 5.2.1 Compatibility**
   - Check for deprecated Express APIs
   - Verify middleware usage is correct for Express 5
   - Check request/response handling patterns

4. **Type Safety**
   - Verify TypeScript types are correctly used
   - Check for `any` types that should be properly typed
   - Verify type imports/exports are correct
   - Check for missing type definitions

5. **Build System Compatibility**
   - Verify Vite-specific code (imports, config) is valid
   - Check Electron-specific APIs are used correctly
   - Verify module resolution paths are correct

6. **Package Dependencies**
   - Check for imports from packages not in package.json
   - Verify version compatibility between dependencies
   - Check for circular dependencies

7. **Untracked (New) Files** - CRITICAL
   - Verify new file exports are correctly structured
   - Check import paths work from existing files
   - Verify new files follow project module patterns
   - Ensure new files integrate with existing codebase

Provide a detailed report with:
- File paths and line numbers of invalid code
- Specific error description (what's wrong and why)
- Expected vs actual behavior
- Priority level (CRITICAL for build-breaking issues)
- **Mark issues in untracked files with [UNTRACKED]**
```

#### Agent 2: Security Vulnerability Scanner

**Focus:** Security issues and vulnerabilities

**Input:** List of files to analyze (prioritize routes, auth, API files), review mode

**Instructions for Agent 2:**

```
STEP 0: READ THE FILES (Required First Step)

For each file in your assigned list:
- MODIFIED files: Run appropriate `git diff` command to see changes
- UNTRACKED files: Use Read tool to get full content
- Prioritize: auth/*, routes/*, api/*, *.env*, config files

Then analyze for security vulnerabilities:

1. **Injection Vulnerabilities**
   - SQL injection (if applicable)
   - Command injection (exec, spawn, etc.)
   - Path traversal vulnerabilities
   - XSS vulnerabilities in React components

2. **Authentication & Authorization**
   - Missing authentication checks
   - Insecure token handling
   - Authorization bypasses
   - Session management issues

3. **Data Handling**
   - Unsafe deserialization
   - Insecure file operations
   - Missing input validation
   - Sensitive data exposure (secrets, tokens, passwords)

4. **Dependencies**
   - Known vulnerable packages
   - Insecure dependency versions
   - Missing security patches

5. **API Security**
   - Missing CORS configuration
   - Insecure API endpoints
   - Missing rate limiting
   - Insecure WebSocket connections

6. **Electron-Specific**
   - Insecure IPC communication
   - Missing context isolation checks
   - Insecure preload scripts
   - Missing CSP headers

7. **Untracked (New) Files** - FULL REVIEW REQUIRED
   - Review ENTIRE file for secrets, tokens, API keys
   - Check for hardcoded credentials in test fixtures
   - Scan for new attack surfaces introduced
   - Verify new files don't expose internal APIs unsafely
   - Check .env.example files for sensitive defaults

Provide a detailed report with:
- Vulnerability type and severity (CRITICAL, HIGH, MEDIUM, LOW)
- File paths and line numbers
- Attack vector description
- Recommended fix approach
- **Mark issues in untracked files with [UNTRACKED]**
```

#### Agent 3: Code Quality & Clean Code

**Focus:** Dirty code, code smells, and quality issues

**Input:** List of files to analyze, review mode

**Instructions for Agent 3:**

```
STEP 0: READ THE FILES (Required First Step)

For each file in your assigned list:
- MODIFIED files: Run appropriate `git diff` command to see changes
- UNTRACKED files: Use Read tool to get full content
- For long files, focus on changed sections

Then analyze for code quality issues:

1. **Code Smells**
   - Long functions/methods (>50 lines)
   - High cyclomatic complexity
   - Duplicate code
   - Dead code
   - Magic numbers/strings

2. **Best Practices**
   - Missing error handling
   - Inconsistent naming conventions
   - Poor separation of concerns
   - Tight coupling
   - Missing comments for complex logic

3. **Performance Issues**
   - Inefficient algorithms
   - Memory leaks (event listeners, subscriptions)
   - Unnecessary re-renders in React
   - Missing memoization where needed
   - Inefficient database queries (if applicable)

4. **Maintainability**
   - Hard-coded values
   - Missing type definitions
   - Inconsistent code style
   - Poor file organization
   - Missing tests for new code

5. **React-Specific**
   - Missing key props in lists
   - Direct state mutations
   - Missing cleanup in useEffect
   - Unnecessary useState/useEffect
   - Prop drilling issues

6. **Untracked (New) Files** - FULL REVIEW REQUIRED
   - Check if new file patterns match codebase conventions
   - Verify naming conventions followed
   - Check for code duplication with existing files
   - Ensure consistent coding style with project

Provide a detailed report with:
- Issue type and severity
- File paths and line numbers
- Description of the problem
- Impact on maintainability/performance
- Recommended refactoring approach
- **Mark issues in untracked files with [UNTRACKED]**
```

#### Agent 4: Implementation Correctness

**Focus:** Verify code implements requirements correctly

**Input:** List of files to analyze, review mode

**Instructions for Agent 4:**

```
STEP 0: READ THE FILES (Required First Step)

For each file in your assigned list:
- MODIFIED files: Run appropriate `git diff` command to see changes
- UNTRACKED files: Use Read tool to get full content
- Read test files alongside implementation files

Then analyze for implementation correctness:

1. **Logic Errors**
   - Incorrect conditional logic
   - Wrong variable usage
   - Off-by-one errors
   - Race conditions
   - Missing null/undefined checks

2. **Functional Requirements**
   - Missing features from requirements
   - Incorrect feature implementation
   - Edge cases not handled
   - Missing validation

3. **Integration Issues**
   - Incorrect API usage
   - Wrong data format handling
   - Missing error handling for external calls
   - Incorrect state management

4. **Type Errors**
   - Type mismatches
   - Missing type guards
   - Incorrect type assertions
   - Unsafe type operations

5. **Testing Gaps**
   - Missing unit tests
   - Missing integration tests
   - Tests don't cover edge cases
   - Tests are incorrect

6. **Untracked (New) Files** - COMPLETE LOGIC REVIEW
   - Review ENTIRE file logic (no diff to compare)
   - Check all function implementations for correctness
   - Verify all edge cases handled in new code
   - Check test files have valid assertions
   - Verify new fixtures are correctly structured

Provide a detailed report with:
- Issue description
- File paths and line numbers
- Expected vs actual behavior
- Steps to reproduce (if applicable)
- Recommended fix
- **Mark issues in untracked files with [UNTRACKED]**
```

#### Agent 5: Architecture & Design Patterns

**Focus:** Architectural issues and design pattern violations

**Input:** List of files to analyze, file categorization from Phase 1, review mode

**Instructions for Agent 5:**

```
STEP 0: READ THE FILES (Required First Step)

For each file in your assigned list:
- MODIFIED files: Run appropriate `git diff` command to see changes
- UNTRACKED files: Use Read tool to get full content
- Read CLAUDE.md and project docs for architecture patterns
- Check import/export relationships between files

Then analyze for architectural and design issues:

1. **Architecture Violations**
   - Violation of project structure patterns
   - Incorrect layer separation
   - Missing abstractions
   - Tight coupling between modules

2. **Design Patterns**
   - Incorrect pattern usage
   - Missing patterns where needed
   - Anti-patterns

3. **Project-Specific Patterns**
   - Check against project documentation (docs/ folder)
   - Verify route organization (server routes)
   - Check provider patterns (server providers)
   - Verify component organization (UI components)

4. **API Design**
   - RESTful API violations
   - Inconsistent response formats
   - Missing error handling
   - Incorrect status codes

5. **State Management**
   - Incorrect state management patterns
   - Missing state normalization
   - Inefficient state updates

6. **Untracked (New) Files** - VERIFY PLACEMENT & LAYERING
   - Verify new files are in correct directory locations
   - Check new files follow feature-first architecture
   - Ensure proper layer separation (routes, services, etc.)
   - Verify new files don't create incorrect dependencies
   - Check if new exports are properly organized in index files

Provide a detailed report with:
- Architectural issue description
- File paths and affected areas
- Impact on system design
- Recommended architectural changes
- **Mark issues in untracked files with [UNTRACKED]**
```

### Phase 3: Consolidate Findings

After all 5 deep dive agents complete their analysis:

1. **Collect all findings** from each agent
2. **Prioritize issues**:
   - CRITICAL: Tech stack invalid code (build-breaking)
   - HIGH: Security vulnerabilities, critical logic errors
   - MEDIUM: Code quality issues, architectural problems
   - LOW: Minor code smells, style issues

3. **Group by file** to understand impact per file
4. **Separate untracked file issues**:
   - List all issues marked with [UNTRACKED]
   - Note dependencies between tracked and untracked files
   - Flag untracked files that may need `git add` before commit
5. **Create a master report** summarizing all findings:

   | Source                     | Files Reviewed | Issues Found |
   | -------------------------- | -------------- | ------------ |
   | Branch changes (committed) | X              | Y            |
   | Modified (uncommitted)     | X              | Y            |
   | Staged                     | X              | Y            |
   | Untracked (new)            | X              | Y            |
   | **Total**                  | X              | Y            |

### Phase 4: Deepcode Fixes (5 Agents)

Launch 5 deepcode agents to fix the issues found. Each agent should be invoked with the `@deepcode` agent.

**IMPORTANT: File Reading for Fixes**

Deepcode agents must read files before fixing:

- Use Read tool to get current file content
- For context, run appropriate `git diff` to see what was changed
- Edit files using the Edit tool
- After all fixes are complete, recommend `git add <file>` for untracked files

**IMPORTANT: Issue Handling Strategy**

1. **Fix immediately** - Issues where Claude is confident in the fix
2. **Defer to user** - Issues that are BOTH:
   - Very severe (system-breaking, security vulnerabilities, significant impact)
   - Claude is uncertain how to fix correctly

   For deferred issues, STOP and present to user:
   - **Issue**: What is wrong
   - **Implications**: What this means for the codebase
   - **Risks**: What could happen if unfixed or fixed incorrectly
   - **Recommendations**: Possible fix approaches with pros/cons

   Wait for user decision, then execute via deepcode agent(s).

#### Deepcode Agent 1: Fix Tech Stack Invalid Code

**Priority:** CRITICAL - Fix first

**Instructions:**

```
Fix all invalid code based on tech stack issues identified by Agent 1.

Focus on:
1. Fixing TypeScript syntax errors
2. Updating deprecated Node.js APIs
3. Fixing React 19 compatibility issues
4. Correcting Express 5 API usage
5. Fixing type errors
6. Resolving build-breaking issues

After fixes, verify:
- Code compiles without errors
- TypeScript types are correct
- No deprecated API usage
```

#### Deepcode Agent 2: Fix Security Vulnerabilities

**Priority:** HIGH

**Instructions:**

```
Fix all security vulnerabilities identified by Agent 2.

Focus on:
1. Adding input validation
2. Fixing injection vulnerabilities
3. Securing authentication/authorization
4. Fixing insecure data handling
5. Updating vulnerable dependencies
6. Securing Electron IPC

After fixes, verify:
- Security vulnerabilities are addressed
- No sensitive data exposure
- Proper authentication/authorization
```

#### Deepcode Agent 3: Refactor Dirty Code

**Priority:** MEDIUM

**Instructions:**

```
Refactor code quality issues identified by Agent 3.

Focus on:
1. Extracting long functions
2. Reducing complexity
3. Removing duplicate code
4. Adding error handling
5. Improving React component structure
6. Adding missing comments

After fixes, verify:
- Code follows best practices
- No code smells remain
- Performance optimizations applied
```

#### Deepcode Agent 4: Fix Implementation Errors

**Priority:** HIGH

**Instructions:**

```
Fix implementation correctness issues identified by Agent 4.

Focus on:
1. Fixing logic errors
2. Adding missing features
3. Handling edge cases
4. Fixing type errors
5. Adding missing tests

After fixes, verify:
- Logic is correct
- Edge cases handled
- Tests pass
```

#### Deepcode Agent 5: Fix Architectural Issues

**Priority:** MEDIUM

**Instructions:**

```
Fix architectural issues identified by Agent 5.

Focus on:
1. Correcting architecture violations
2. Applying proper design patterns
3. Fixing API design issues
4. Improving state management
5. Following project patterns

After fixes, verify:
- Architecture is sound
- Patterns are correctly applied
- Code follows project structure
```

### Phase 5: Verification

After all fixes are complete:

1. **Run TypeScript compilation check**

   ```bash
   npm run build:packages
   ```

2. **Run linting**

   ```bash
   npm run lint
   ```

3. **Run tests** (if applicable)

   ```bash
   npm run test:server
   npm run test
   ```

4. **Verify git diff** shows only intended changes

   ```bash
   git diff HEAD
   ```

5. **Verify untracked files are still present and not broken**

   ```bash
   git ls-files --others --exclude-standard
   ```

   Confirm untracked files:
   - Are still listed (not accidentally deleted)
   - Can be imported/used by tracked files
   - Build succeeds with untracked files included

6. **Recommend staging new files** (if appropriate)

   ```bash
   # List files that should be added
   git status --short
   ```

   Provide recommendations:
   - Which untracked files should be staged
   - Which might be intentionally untracked (e.g., local config)

7. **Create summary report**:
   - Review mode used (working directory or branch comparison)
   - Target branch (if branch mode)
   - Issues found by each agent (tracked vs untracked)
   - Issues fixed by each agent
   - Issues deferred to user (if any)
   - Remaining issues (if any)
   - Verification results
   - Untracked files recommendations

## Workflow Summary

1. Parse arguments (worktree, target branch) and determine review mode
2. Collect metadata only (file lists, diff stats) - NO file content reading
3. Categorize files by domain (frontend/backend/shared/tests)
4. Launch 5 deep dive agents with file lists (agents read files themselves)
5. Consolidate findings and prioritize (track untracked issues)
6. Launch 5 deepcode agents (sequential fixes, priority order)
7. Verify fixes with build/lint/test
8. Verify untracked files and recommend staging
9. Report summary with tracked vs untracked breakdown

## Notes

- **DO NOT CREATE A COMMIT** - This review process ends with verification and reporting only. The user will decide when to commit.
- **DELEGATED FILE READING** - Main session collects only metadata. Agents read files themselves to avoid context bloat.
- **FIX ALL ISSUES CLAUDE IS CONFIDENT ABOUT** - Every issue where Claude knows how to fix it MUST be fixed immediately by the deepcode agents. Do not skip or defer these.
- **DEFER ONLY SEVERE + UNCERTAIN ISSUES** - For issues that are both:
  1. Very severe (could break the system, introduce security vulnerabilities, or have significant impact)
  2. Claude is uncertain how to fix correctly

  For these deferred issues, Claude MUST:
  1. **Communicate explicitly** to the user that this issue is being deferred
  2. **Explain the issue** - What exactly is wrong
  3. **Explain implications** - What this issue means for the codebase
  4. **Explain risks** - What problems it could introduce if left unfixed or fixed incorrectly
  5. **Provide recommendations** - Possible approaches to fix with pros/cons

  After the user reviews and decides, execute their decision via deepcode agent(s).

- **Tech stack validation is HIGHEST PRIORITY** - invalid code must be fixed first
- **Agents read their own files** - Each agent uses Read tool and `git diff` to fetch file content
- **Untracked files** - Agents read full content since no diff exists
- **Review modes**:
  - Working directory mode: Reviews uncommitted changes (`git diff HEAD`)
  - Branch comparison mode: Reviews all branch changes (`git diff $TARGET_REF...HEAD`)
- Each deep dive agent should work independently and provide comprehensive analysis
- Deepcode agents should fix issues in priority order
- All fixes should maintain existing functionality
- If an agent finds no issues in their domain, they should report "No issues found"
- If fixes introduce new issues, they should be caught in verification phase
