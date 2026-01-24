# Code Review Command

Comprehensive code review using multiple deep dive agents to analyze git diff for correctness, security, code quality, and tech stack compliance, followed by automated fixes using deepcode agents.

## Usage

This command analyzes all changes in the git diff and verifies:

1. **Invalid code based on tech stack** (HIGHEST PRIORITY)
2. Security vulnerabilities
3. Code quality issues (dirty code)
4. Implementation correctness

Then automatically fixes any issues found.

## Instructions

### Phase 1: Get Git Diff

1. **Get the current git diff**

   ```bash
   git diff HEAD
   ```

   If you need staged changes instead:

   ```bash
   git diff --cached
   ```

   Or for a specific commit range:

   ```bash
   git diff <base-branch>
   ```

2. **Get list of changed files**

   ```bash
   git diff --name-only HEAD
   ```

3. **Get untracked files** (new files not yet added to git)

   ```bash
   git ls-files --others --exclude-standard
   ```

   This captures NEW files that `git diff` misses.

4. **Read full content of untracked files**

   For each untracked file from step 3, read the FULL file content (no diff exists for new files).

   Format each untracked file as:

   ```
   ### NEW FILE: path/to/file.ts (UNTRACKED)
   Lines: <line count>

   <full file content>
   ```

5. **Categorize all changes**

   Create a summary table:

   | Category           | Count | Files         |
   | ------------------ | ----- | ------------- |
   | Modified (tracked) | X     | list files... |
   | Staged             | X     | list files... |
   | Untracked (new)    | X     | list files... |
   | **Total**          | X     |               |

6. **Find related files** (import/export dependencies)

   For changed/untracked files, use grep to find:
   - Files that import from the changed files
   - Files that the changed files import from

   This provides context for architectural review.

7. **Understand the tech stack** (for validation):
   - **Node.js**: >=22.0.0 <23.0.0
   - **TypeScript**: 5.9.3
   - **React**: 19.2.3
   - **Express**: 5.2.1
   - **Electron**: 39.2.7
   - **Vite**: 7.3.0
   - **Vitest**: 4.0.16
   - Check `package.json` files for exact versions

### Phase 2: Deep Dive Analysis (5 Agents)

Launch 5 separate deep dive agents, each with a specific focus area. Each agent should be invoked with the `@deepdive` agent and given the git diff along with their specific instructions.

**IMPORTANT: Input Format for All Agents**

Provide each agent with:

1. **Git Diff** - Changes to tracked files (from `git diff HEAD`)
2. **Full File Content** - For NEW untracked files (entire file, no diff markers)
3. **Related Files** - Files that import from / are imported by changed files

Each agent must understand:

- Untracked files have NO diff markers (`+`/`-`) - review the FULL content
- New files need complete analysis, not just incremental review
- Consider how new files integrate with existing codebase

#### Agent 1: Tech Stack Validation (HIGHEST PRIORITY)

**Focus:** Verify code is valid for the tech stack

**Instructions for Agent 1:**

```
Analyze the git diff for invalid code based on the tech stack:

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

**Instructions for Agent 2:**

```
Analyze the git diff for security vulnerabilities:

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

**Instructions for Agent 3:**

```
Analyze the git diff for code quality issues:

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

**Instructions for Agent 4:**

```
Analyze the git diff for implementation correctness:

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

**Instructions for Agent 5:**

```
Analyze the git diff for architectural and design issues:

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

   | Source             | Files Reviewed | Issues Found |
   | ------------------ | -------------- | ------------ |
   | Modified (tracked) | X              | Y            |
   | Staged             | X              | Y            |
   | Untracked (new)    | X              | Y            |
   | **Total**          | X              | Y            |

### Phase 4: Deepcode Fixes (5 Agents)

Launch 5 deepcode agents to fix the issues found. Each agent should be invoked with the `@deepcode` agent.

**IMPORTANT: Untracked Files Context**

When fixing issues in untracked files:

- Edit the files normally using the Edit tool
- Untracked files can be modified just like tracked files
- After all fixes are complete, recommend `git add <file>` for untracked files
- Issues marked [UNTRACKED] require reading the full file, not diff

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
   - Issues found by each agent (tracked vs untracked)
   - Issues fixed by each agent
   - Remaining issues (if any)
   - Verification results
   - Untracked files recommendations

## Workflow Summary

1. ✅ Get git diff + untracked files + related files
2. ✅ Read full content of untracked files
3. ✅ Categorize all changes (modified/staged/untracked)
4. ✅ Launch 5 deep dive agents (parallel analysis, all file types)
5. ✅ Consolidate findings and prioritize (track untracked issues)
6. ✅ Launch 5 deepcode agents (sequential fixes, priority order)
7. ✅ Verify fixes with build/lint/test
8. ✅ Verify untracked files and recommend staging
9. ✅ Report summary with tracked vs untracked breakdown

## Notes

- **DO NOT CREATE A COMMIT** - This review process ends with verification and reporting only. The user will decide when to commit.
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
- **Untracked files require FULL content review** - no diff exists, so entire file must be analyzed
- Each deep dive agent should work independently and provide comprehensive analysis
- Deepcode agents should fix issues in priority order
- All fixes should maintain existing functionality
- If an agent finds no issues in their domain, they should report "No issues found"
- If fixes introduce new issues, they should be caught in verification phase
- Untracked files often include: new test files, fixtures, utilities, documentation, and configuration examples
