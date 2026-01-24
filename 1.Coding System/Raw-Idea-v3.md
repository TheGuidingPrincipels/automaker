# Autonomous Coding Ecosystem (ACE): Raw Idea v3

## Version History

| Version | Date       | Changes                                                                                                                                                                                                                                                             |
| ------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1      | Initial    | Initial intake and structuring                                                                                                                                                                                                                                      |
| v2      | Session 1  | Integrated testing/validation insights, execution strategy details, tribunal consensus logic, Q&A orchestrator concept, agent configuration requirements                                                                                                            |
| v3      | Session 2+ | Complete architecture redesign based on resolved questions RQ-1 through RQ-4d. Reorganized by execution phases. Full schema definitions added. Agent roster finalized (7 core agents). Two-stage Architect workflow. Three-Mode Scout. Judge-based drift detection. |

---

## 1. Core Concept

The **Autonomous Coding Ecosystem (ACE)** is a highly automated software development factory that transforms high-level master plans into production-ready code with minimal human intervention.

### What ACE Does

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  DEVELOPER DEFINES WHAT                                                      │
│  • Features, behaviors, constraints                                          │
│  • Test criteria and acceptance conditions                                   │
│  • Architectural boundaries (Always/Ask/Never)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  AGENT SYSTEM DECIDES HOW                                                    │
│  • Technology choices and implementation patterns                            │
│  • Code structure and architecture decisions                                 │
│  • Testing implementation details                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  OUTPUT: PRODUCTION-READY CODE                                               │
│  • Secure, maintainable, efficient, reliable                                 │
│  • Edge cases covered                                                        │
│  • Verified through multi-layer validation                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Insight

> "Autonomy scales with feedback loop quality, not with giving agents more freedom."
>
> Organizations building successful agentic systems (Devin, Claude Code, Cursor, SWE-Agent) independently arrived at similar architecture: agents that can iterate on failing tests and see terminal output vastly outperform agents that must "get it right" on the first attempt.

This insight drives ACE's **TDD-first methodology**: tests are written before code, providing immediate feedback for iterative improvement.

### Design Principles

| Principle                         | Description                                                          |
| --------------------------------- | -------------------------------------------------------------------- |
| **WHAT vs HOW Separation**        | Developers define what to build; agents decide how to implement      |
| **Test Specifications in Plans**  | 94.3% success rate vs 68% when agents write their own specs (_RQ-1_) |
| **Tester Isolation**              | Tester never sees implementation code, preventing tautological tests |
| **Defense in Depth**              | Multiple validation layers catch different failure modes             |
| **Subscription-First Cost Model** | CLI tools for execution; APIs reserved for orchestration             |
| **Autonomy with Observability**   | System runs independently while humans retain full visibility        |
| **Never Break Production**        | Breaking changes require human approval before implementation        |

---

## 2. System Architecture Overview

ACE operates through five sequential phases, coordinated by a central SDK-based Orchestrator.

### High-Level Pipeline

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              ACE PIPELINE                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 1: PLAN CREATION                                                  │  │
│  │   Master Plan (external) → Scout → Architect → Sub-Plans               │  │
│  │   [RQ-4a, RQ-4b, RQ-4c]                                                 │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                        │
│                                      ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 2: PRE-IMPLEMENTATION                                             │  │
│  │   Sub-Plan Verifier validates all plans before execution               │  │
│  │   [RQ-3a, RQ-4d]                                                        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                        │
│                                      ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 3: EXECUTION (Per Sub-Plan, Sequential)                           │  │
│  │   Scout → Tester → Coder → Verifier → Judge                            │  │
│  │   [RQ-1, RQ-2, RQ-3b]                                                   │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                        │
│                                      ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 4: FINAL VALIDATION                                               │  │
│  │   Tribunal (3-model consensus) → E2E Testing (final gate)              │  │
│  │   [RQ-1, OQ-11, OQ-12]                                                  │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                        │
│                                      ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ PHASE 5: MERGE & SYNTHESIS                                              │  │
│  │   Conflict resolution → Documentation → Learning extraction → Merge    │  │
│  │   [OQ-9, OQ-13]                                                         │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Agent Roster Summary

| #   | Agent                 | Runtime           | Primary Responsibility                                                                                                     | Reference      |
| --- | --------------------- | ----------------- | -------------------------------------------------------------------------------------------------------------------------- | -------------- |
| 0   | **Orchestrator**      | Claude Code SDK   | Control unit: reads pipeline state, invokes agents, manages workflow. Does NOT write code.                                 | _RQ-2_         |
| 1   | **Scout**             | Claude CLI        | Three-Mode codebase exploration: Initial (before Architect) + On-demand (during planning) + Per-iteration (during Coder)   | _RQ-3a_        |
| 2   | **Architect**         | Claude CLI        | Two-stage strategic decomposition: master plan → 5-15 milestones → Feature Specs + Implementation Plans                    | _RQ-2, RQ-4c_  |
| 3   | **Sub-Plan Verifier** | Claude CLI        | External validation of Architect outputs before execution begins                                                           | _RQ-3a, RQ-4d_ |
| 4   | **Tester**            | Claude CLI        | TDD engine: writes failing tests from Feature Spec. CANNOT see implementation code (isolation prevents tautological tests) | _RQ-2, RQ-3a_  |
| 5   | **Coder**             | Codex/Claude CLI  | Implementation: writes minimal code to pass tests. Flags drift violations if reality conflicts with assumptions            | _RQ-2_         |
| 6   | **Verifier**          | Automated Tooling | Tiered quality gates: T1 <5s (lint) → T2 <60s (types/security) → T3 <300s (integration)                                    | _RQ-2_         |
| 7   | **Judge**             | Gemini/Claude CLI | Semantic review + drift detection via ASI monitoring. Decisions: ACCEPT / REQUEST_FIX / ESCALATE                           | _RQ-2, RQ-3b_  |

### Communication Architecture

All agents communicate through a **PostgreSQL Blackboard** (shared state), not direct agent-to-agent calls.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         POSTGRESQL BLACKBOARD                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ architect_state │  │ batch_state     │  │ agent_messages  │              │
│  │ (session info)  │  │ (coherence)     │  │ (handoff/Q&A)   │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ sub_plans       │  │ test_results    │  │ drift_markers   │              │
│  │ (Feature+Impl)  │  │ (per tier)      │  │ (assumptions)   │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
                                  ▲
                                  │ Read/Write via MCP
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
   ┌────┴────┐  ┌────────┐  ┌────┴────┐  ┌────────┐  ┌────┴────┐
   │ Scout   │  │Architect│  │ Tester  │  │ Coder  │  │ Judge   │
   └─────────┘  └────────┘  └─────────┘  └────────┘  └─────────┘
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  │
                                  ▼
                         ┌───────────────┐
                         │ ORCHESTRATOR  │
                         │ (SDK-based)   │
                         │ Controls flow │
                         └───────────────┘
```

---

## 3. Phase 1: Plan Creation

### 3.1 Master Plan Input

The master plan is created **outside** the ACE system using external LLM tools (Gemini Gems, Claude Desktop Projects, Custom GPTs). It defines **WHAT** to build, not **HOW**.

**Reference**: _RQ-4a: Master Plan Structure & Content_

#### Master Plan Template (8 Required Sections)

```yaml
# MASTER PLAN TEMPLATE
# Focus: WHAT and WHY only. Omit technology choices and implementation patterns.
# Authoring time: 45-120 minutes

1_vision_and_goals:
  description: 'User story, success criteria (quantifiable), constraints'
  content:
    user_story: 'As a [role], I want [feature] so that [benefit]'
    success_criteria:
      - 'Metric 1: [quantifiable target]'
      - 'Metric 2: [quantifiable target]'
    constraints:
      - 'Must complete within [timeframe]'
      - 'Must integrate with [existing system]'

2_core_commands:
  description: 'Build, test, lint, deploy commands with flags'
  content:
    build: 'npm run build'
    test: 'npm test'
    lint: 'npm run lint'
    deploy: 'npm run deploy:staging'

3_testing_strategy:
  description: 'Test types required, coverage expectations, key scenarios (WHAT not HOW)'
  content:
    required_test_types:
      - 'Unit tests for business logic'
      - 'Integration tests for API endpoints'
      - 'E2E tests for critical user flows'
    coverage_expectations:
      - 'Minimum 80% line coverage'
      - '100% coverage for authentication flows'
    key_scenarios:
      - 'User registration with valid data'
      - 'User registration with duplicate email'
      - 'Password reset flow'

4_architectural_boundaries:
  description: 'Always/Ask First/Never actions (Three-Tier)'
  content:
    always:
      - 'Use parameterized queries for database access'
      - 'Validate all user inputs server-side'
      - 'Log all authentication attempts'
    ask_first:
      - 'Adding new database tables'
      - 'Modifying shared utility functions'
      - 'Changes to API response formats'
    never:
      - 'Store passwords in plain text'
      - 'Disable CSRF protection'
      - 'Delete production data'

5_domain_model:
  description: 'Entities, aggregates, business rules'
  content:
    entities:
      - name: 'User'
        attributes: ['id', 'email', 'passwordHash', 'createdAt']
        rules: ['Email must be unique', 'Password minimum 8 characters']
      - name: 'Session'
        attributes: ['id', 'userId', 'token', 'expiresAt']
        rules: ['Expires after 24 hours of inactivity']

6_integration_points:
  description: 'External APIs, shared services, event streams'
  content:
    external_apis:
      - name: 'SendGrid'
        purpose: 'Email delivery'
        auth: 'API key in environment variable'
    shared_services:
      - name: 'AuthService'
        purpose: 'Shared authentication logic'
        location: 'src/services/auth'

7_success_definition:
  description: 'Functional requirements, NFRs, acceptance criteria'
  content:
    functional:
      - 'Users can register with email and password'
      - 'Users receive confirmation email within 5 minutes'
    non_functional:
      - 'API response time < 200ms (p95)'
      - 'System handles 1000 concurrent users'
    acceptance_criteria:
      - 'Given valid credentials, when user logs in, then session token is returned'
      - 'Given invalid password, when user logs in, then error 401 is returned'

8_out_of_scope:
  description: 'Excluded features, future enhancements'
  content:
    excluded:
      - 'Social login (OAuth)'
      - 'Two-factor authentication'
      - 'Password complexity rules beyond minimum length'
    future:
      - 'Account recovery via phone number'
      - 'Biometric authentication'

9_referenced_learnings: # Optional
  description: 'Query Learning MCP for relevant patterns'
  timeout: '5 seconds'
  fallback: 'Proceed without learnings if timeout'
  scope: 'architectural + anti-patterns only'
```

#### Technical Depth Guidelines

| Include (HIGH Specificity)  | Omit (LOW Specificity - Agents Decide) |
| --------------------------- | -------------------------------------- |
| Architectural boundaries    | Technology stack choices               |
| Test criteria and coverage  | Implementation patterns                |
| Non-functional requirements | Project structure                      |
| Integration points          | Code style preferences                 |
| Anti-patterns to avoid      | Git workflow details                   |

#### Learning MCP Integration (3-Tier Access)

| Tier | When                  | Scope                         | Volume              | Timeout |
| ---- | --------------------- | ----------------------------- | ------------------- | ------- |
| 1    | Master plan authoring | Architectural + anti-patterns | 3-5 strategic       | 5s      |
| 2    | Sub-plan enrichment   | Tactical + bug-fixes          | 10-20 comprehensive | 10s     |
| 3    | Code execution        | Just-in-time queries          | As needed           | 3s      |

---

### 3.2 Scout Agent (Three-Mode Codebase Exploration)

**Reference**: _RQ-3a: Pre-Implementation Architecture_

The Scout agent provides codebase context at three critical points:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         THREE-MODE SCOUT                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  MODE 1: INITIAL (Before Architect Stage 1)                                  │
│  ├─ Triggered: ALWAYS, automatically by Orchestrator                         │
│  ├─ Scope: Comprehensive codebase analysis                                   │
│  ├─ Output: Findings compressed to PostgreSQL Blackboard                     │
│  └─ Purpose: Inform milestone decomposition                                  │
│                                                                              │
│  MODE 2: ON-DEMAND (During Architect Stage 2)                                │
│  ├─ Triggered: Architect requests via search/read tools                      │
│  ├─ Scope: Targeted queries for specific files/patterns                      │
│  ├─ Output: Direct response to Architect                                     │
│  └─ Purpose: Enrich sub-plan details                                         │
│                                                                              │
│  MODE 3: PER-ITERATION (During Coder execution)                              │
│  ├─ Triggered: Coder encounters emergent complexity                          │
│  ├─ Scope: Focused exploration of specific components                        │
│  ├─ Output: Ranked file/function locations                                   │
│  └─ Purpose: Resolve unexpected implementation blockers                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Scout Output Schema

```yaml
scout_findings:
  metadata:
    timestamp: 'ISO-8601'
    mode: 'initial | on-demand | per-iteration'
    master_plan_id: 'uuid'

  codebase_structure:
    root_directories:
      - path: 'src/'
        purpose: 'Application source code'
        key_patterns: ['MVC', 'service layer']
      - path: 'tests/'
        purpose: 'Test files'
        framework: 'pytest'

  relevant_files:
    - path: 'src/services/auth.py'
      relevance_score: 0.95
      summary: 'Authentication service with JWT handling'
      modification_risk: 'high' # Many dependents

  integration_points:
    - name: 'DatabaseConnection'
      location: 'src/db/connection.py'
      consumers: ['auth', 'users', 'sessions']

  potential_conflicts:
    - description: 'Auth service uses deprecated token format'
      files_affected: ['src/services/auth.py', 'src/middleware/jwt.py']
      recommendation: 'Coordinate migration in single sub-plan'
```

---

### 3.3 Architect Agent (Two-Stage Decomposition)

**Reference**: _RQ-4c: Plan Decomposition Process & Architect Workflow_

The Architect transforms the master plan into executable sub-plans through a two-stage process.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARCHITECT TWO-STAGE WORKFLOW                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STAGE 1: MILESTONE DECOMPOSITION                                            │
│  ├─ Input: Master Plan + Scout Findings                                      │
│  ├─ Output: 5-15 Milestone Descriptions (~10k tokens total)                  │
│  ├─ Each milestone includes:                                                 │
│  │   • Title and objective                                                   │
│  │   • Scope boundaries                                                      │
│  │   • Dependencies on other milestones                                      │
│  │   • Execution order                                                       │
│  └─ Validation: Sub-Plan Verifier reviews before Stage 2                     │
│                                                                              │
│  ────────────────────────────────────────────────────────────────────────── │
│                                                                              │
│  STAGE 2: MILESTONE ENRICHMENT (Batches of 5)                                │
│  ├─ Input: One milestone + On-demand Scout access                            │
│  ├─ Output: Dual documents per milestone (~30k tokens each):                 │
│  │   • Feature Specification (for Tester) - 5-10k tokens                     │
│  │   • Implementation Plan (for Coder) - 15-20k tokens                       │
│  ├─ Context reset between batches                                            │
│  └─ Validation: Sub-Plan Verifier reviews every batch                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Dual Output: Why Two Documents?

The Architect produces **two separate documents** per sub-plan to enforce Tester isolation:

| Document                  | Recipient         | Content                                         | Purpose                     |
| ------------------------- | ----------------- | ----------------------------------------------- | --------------------------- |
| **Feature Specification** | Tester ONLY       | WHAT to test (behaviors, scenarios)             | Prevents tautological tests |
| **Implementation Plan**   | Coder (and Judge) | HOW to implement (files, patterns, pseudo-code) | Guides implementation       |

The Tester **never sees** the Implementation Plan. This isolation ensures tests verify behavior, not implementation details.

#### Granularity Triggers

| Trigger                                              | Action                           |
| ---------------------------------------------------- | -------------------------------- |
| >5 files OR >10 functions OR >300 LOC OR >25k tokens | **Split** into smaller sub-plans |
| <2 files AND <3 functions AND tightly coupled        | **Merge** into single sub-plan   |

#### Context Reset Protocol

The Architect's context is reset under these conditions to prevent quality degradation:

| Signal Type    | Trigger                              | Action                       |
| -------------- | ------------------------------------ | ---------------------------- |
| **Resource**   | Context window >80%                  | Reset with summary injection |
| **Quality**    | Performance drop >15% from baseline  | Rollback to checkpoint       |
| **Behavioral** | Edit loops >3 on same issue          | Escalate or reset            |
| **Structural** | Every 5 sub-plans (batch completion) | Mandatory reset              |
| **Entropy**    | Δtokens <-90% AND Δaccuracy <-10%    | Force reset                  |
| **Cost**       | Time-to-first-token growth >50%      | Reset                        |

---

### 3.4 Sub-Plan Schemas

**Reference**: _RQ-4b: Sub-Plan Schema Content_

#### Feature Specification Schema (8 Sections, for Tester)

```yaml
# FEATURE SPECIFICATION
# Recipient: Tester ONLY (isolated from implementation details)
# Format: Given-When-Then behavioral contracts
# Size: 5-10k tokens

metadata:
  spec_id: 'SP-001-FS'
  master_plan_id: 'MP-001'
  milestone: 1
  version: '1.0'
  created_at: 'ISO-8601'

overview:
  title: 'User Authentication Feature'
  objective: 'Enable users to register and login securely'
  scope_summary: 'Registration, login, session management'

acceptance_criteria: # Given-When-Then format
  - id: 'AC-001'
    given: 'A new user with valid email and password'
    when: 'They submit the registration form'
    then: 'Account is created and confirmation email is sent'

  - id: 'AC-002'
    given: 'A registered user with correct credentials'
    when: 'They submit the login form'
    then: 'Session token is returned with 24-hour expiry'

  - id: 'AC-003'
    given: 'A user with incorrect password'
    when: 'They submit the login form'
    then: 'Error 401 is returned and attempt is logged'

test_scenarios: # Gherkin-style
  - scenario: 'Successful Registration'
    steps:
      - 'Given the registration endpoint is available'
      - 'When I POST valid user data to /api/register'
      - 'Then I receive status 201'
      - 'And the response contains user ID'
      - 'And confirmation email is queued'

  - scenario: 'Duplicate Email Registration'
    steps:
      - "Given a user with email 'test@example.com' exists"
      - 'When I POST registration with same email'
      - 'Then I receive status 409'
      - 'And error message indicates duplicate'

concrete_examples: # Minimum 2 per feature
  - name: 'Valid Registration Request'
    input:
      email: 'newuser@example.com'
      password: 'SecurePass123!'
    expected_output:
      status: 201
      body:
        id: 'uuid-format'
        email: 'newuser@example.com'

  - name: 'Invalid Email Format'
    input:
      email: 'not-an-email'
      password: 'SecurePass123!'
    expected_output:
      status: 400
      body:
        error: 'Invalid email format'

out_of_scope:
  - 'Password reset functionality'
  - 'Social login (OAuth)'
  - 'Two-factor authentication'

domain_language:
  - term: 'Session Token'
    definition: 'JWT containing userId, issued at login, expires in 24 hours'
  - term: 'Password Hash'
    definition: 'bcrypt hash with cost factor 12'

verification_checklist: # Self-verification for Tester
  - '[ ] All acceptance criteria have corresponding test scenarios'
  - '[ ] Each scenario has concrete examples'
  - '[ ] Edge cases identified (empty input, max length, special chars)'
  - '[ ] Error conditions specified with expected responses'
  - '[ ] No implementation details leaked into specifications'
```

#### Implementation Plan Schema (14 Sections, for Coder)

```yaml
# IMPLEMENTATION PLAN
# Recipient: Coder (also visible to Judge for drift detection)
# Format: Six Core Areas framework with pseudo-code
# Size: 15-20k tokens

metadata:
  plan_id: 'SP-001-IP'
  feature_spec_id: 'SP-001-FS' # Links to corresponding Feature Spec
  master_plan_id: 'MP-001'
  milestone: 1
  version: '1.0'
  created_at: 'ISO-8601'

task_overview:
  title: 'Implement User Authentication'
  objective: 'Create registration and login endpoints with secure session handling'
  estimated_complexity: 'medium'
  estimated_loc: 200

architecture_context:
  patterns_in_use: ['Service Layer', 'Repository Pattern']
  relevant_decisions: 'Authentication uses JWT with RS256 signing'
  dependencies: ['bcrypt', 'jsonwebtoken', 'express-validator']

files:
  create:
    - path: 'src/services/auth.service.ts'
      purpose: 'Authentication business logic'
    - path: 'src/controllers/auth.controller.ts'
      purpose: 'HTTP request handling'
    - path: 'src/routes/auth.routes.ts'
      purpose: 'Route definitions'

  modify:
    - path: 'src/middleware/index.ts'
      change: 'Add authentication middleware export'
      lines_affected: '5-10'

  read_only: # Context files, do not modify
    - path: 'src/config/database.ts'
    - path: 'src/models/user.model.ts'

component_specifications:
  - name: 'AuthService.register'
    purpose: 'Handle user registration logic'
    inputs:
      - name: 'email'
        type: 'string'
        validation: 'Valid email format'
      - name: 'password'
        type: 'string'
        validation: 'Minimum 8 characters'
    outputs:
      - name: 'user'
        type: 'User'
        description: 'Created user without password hash'
    pseudo_code: |
      function register(email, password):
        if userRepository.findByEmail(email):
          throw DuplicateEmailError
        
        hashedPassword = bcrypt.hash(password, 12)
        user = userRepository.create({
          email: email,
          passwordHash: hashedPassword
        })
        
        emailService.sendConfirmation(user.email)
        return user.withoutPassword()

  - name: 'AuthService.login'
    purpose: 'Authenticate user and issue token'
    inputs:
      - name: 'email'
        type: 'string'
      - name: 'password'
        type: 'string'
    outputs:
      - name: 'token'
        type: 'string'
        description: 'JWT with 24-hour expiry'
    pseudo_code: |
      function login(email, password):
        user = userRepository.findByEmail(email)
        if not user:
          throw InvalidCredentialsError
        
        if not bcrypt.compare(password, user.passwordHash):
          auditLog.record('failed_login', email)
          throw InvalidCredentialsError
        
        token = jwt.sign(
          { userId: user.id },
          privateKey,
          { algorithm: 'RS256', expiresIn: '24h' }
        )
        return token

data_structures:
  - name: 'RegisterRequest'
    fields:
      - name: 'email'
        type: 'string'
        required: true
      - name: 'password'
        type: 'string'
        required: true

  - name: 'LoginResponse'
    fields:
      - name: 'token'
        type: 'string'
      - name: 'expiresAt'
        type: 'ISO-8601 datetime'

integration_points:
  - name: 'EmailService'
    method: 'sendConfirmation'
    expected_behavior: 'Queues email, returns immediately'
  - name: 'AuditLog'
    method: 'record'
    expected_behavior: 'Async logging, does not block'

commands: # Six Core Areas: Commands
  build: 'npm run build'
  test: "npm test -- --grep 'auth'"
  lint: 'npm run lint -- src/services/auth.service.ts'

code_style: # Six Core Areas: Style
  patterns:
    - 'Use async/await over callbacks'
    - 'Throw custom error classes, not generic Error'
  naming:
    - "Services: PascalCase with 'Service' suffix"
    - 'Methods: camelCase verbs (register, login, validate)'
  example: |
    // Correct error handling pattern
    if (!user) {
      throw new InvalidCredentialsError('User not found');
    }

boundaries: # Three-Tier: Always/Ask/Never
  always:
    - 'Use parameterized queries'
    - 'Hash passwords with bcrypt cost factor 12'
    - 'Validate all inputs before processing'
  ask_first:
    - 'Adding new dependencies'
    - 'Modifying shared middleware'
  never:
    - 'Log passwords or tokens'
    - 'Store plain text passwords'
    - 'Disable input validation'

implementation_sequence:
  - step: 1
    action: 'Create AuthService with register method'
    tests_to_pass: ['register.success', 'register.duplicate']
  - step: 2
    action: 'Add login method to AuthService'
    tests_to_pass: ['login.success', 'login.invalid']
  - step: 3
    action: 'Create AuthController'
    tests_to_pass: ['controller.register', 'controller.login']
  - step: 4
    action: 'Add routes and integrate'
    tests_to_pass: ['e2e.registration', 'e2e.login']

drift_markers: # Assumptions that must hold
  - assumption: "User model has 'email' and 'passwordHash' fields"
    downstream_plans: [2, 3]
    impact_if_false: 'Session management will fail'

  - assumption: 'JWT uses RS256 with keys in /config/keys/'
    downstream_plans: [3, 5]
    impact_if_false: 'Token verification will fail'

dependencies:
  upstream: [] # This is milestone 1
  downstream: [2, 3] # Session management, protected routes

success_criteria:
  functional:
    - 'All acceptance criteria tests pass'
    - 'No lint errors'
  non_functional:
    - 'Registration completes in <500ms'
    - 'Login completes in <200ms'
  coverage:
    - 'Minimum 80% line coverage for new code'
```

---

## 4. Phase 2: Pre-Implementation Verification

**Reference**: _RQ-3a: Pre-Implementation Architecture_, _RQ-4d: Sub-Plan Creation Workflow & Coherence_

Before any code execution begins, the Sub-Plan Verifier validates all Architect outputs.

### Sub-Plan Verifier Agent

The Sub-Plan Verifier is an **external agent** (not self-review by Architect) that applies the Generator-Critic pattern.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SUB-PLAN VERIFICATION                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INPUT: Feature Specification + Implementation Plan (per sub-plan)           │
│                                                                              │
│  VERIFICATION CRITERIA:                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ Criterion    │ Threshold │ Evaluation Prompt                            │ │
│  ├─────────────────────────────────────────────────────────────────────────┤ │
│  │ Coherence    │ ≥0.9      │ "Compare assumptions against prior_batch_    │ │
│  │              │           │  state. List conflicts."                     │ │
│  ├─────────────────────────────────────────────────────────────────────────┤ │
│  │ Completeness │ ≥0.8      │ "Can Tester derive test cases from Feature   │ │
│  │              │           │  Spec WITHOUT Implementation Plan?"          │ │
│  ├─────────────────────────────────────────────────────────────────────────┤ │
│  │ Executability│ ≥0.85     │ "Can Coder implement without asking          │ │
│  │              │           │  questions?"                                 │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  OUTCOMES:                                                                   │
│  ├─ PASS: Proceed to execution                                               │
│  ├─ REVISE: Return to Architect with specific feedback (max 3 iterations)    │
│  └─ ESCALATE: Human review required                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Coherence Architecture

**Reference**: _RQ-4d_

To maintain coherence across sub-plans, the system uses:

1. **Schema-Based Prevention** (instant): Validates structure before content review
2. **BATCH_COHERENCE.md**: Persistent file storing cross-batch state
3. **PostgreSQL Tables**: Structured storage for dependencies and assumptions

#### PostgreSQL Coherence Schema

```sql
-- Batch state tracking
CREATE TABLE batch_state (
    session_id UUID PRIMARY KEY,
    batch_num INTEGER NOT NULL,
    milestone_ids UUID[] NOT NULL,
    coherence_summary TEXT,
    status VARCHAR(20) NOT NULL  -- 'pending', 'verified', 'failed'
);

-- Cross-plan dependency tracking
CREATE TABLE cross_plan_dependencies (
    id SERIAL PRIMARY KEY,
    from_plan_id UUID NOT NULL,
    to_plan_id UUID NOT NULL,
    interface_definition JSONB NOT NULL,
    verified BOOLEAN DEFAULT FALSE
);

-- Shared assumptions across plans
CREATE TABLE shared_assumptions (
    id SERIAL PRIMARY KEY,
    assumption_text TEXT NOT NULL,
    applies_to_plan_ids UUID[] NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    verification_result TEXT
);

-- Versioned artifacts for rollback
CREATE TABLE versioned_artifacts (
    id SERIAL PRIMARY KEY,
    artifact_type VARCHAR(50) NOT NULL,  -- 'feature_spec', 'impl_plan'
    artifact_id UUID NOT NULL,
    version INTEGER NOT NULL,
    content JSONB NOT NULL,
    batch_num INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 5. Phase 3: Execution (TDD Cycle)

**Reference**: _RQ-1: Testing & Validation Strategy_, _RQ-2: Execution Strategy_, _RQ-3b: Validation & Drift Detection_

For each verified sub-plan, the system executes a TDD cycle:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TDD EXECUTION CYCLE (Per Sub-Plan)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ SCOUT (Mode 3: Per-Iteration, if needed)                                │ │
│  │   Localize WHERE to change when Coder encounters complexity             │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                        │
│                                      ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ TESTER: Write Failing Tests (RED State)                                 │ │
│  │   Input: Feature Specification ONLY (no Implementation Plan)            │ │
│  │   Output: Test files that currently fail                                │ │
│  │   Isolation: Cannot see implementation code                             │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                        │
│                                      ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ CODER: Implement to Pass Tests (GREEN State)                            │ │
│  │   Input: Failing tests + Implementation Plan + Drift markers            │ │
│  │   Output: Minimal code to pass tests                                    │ │
│  │   Flags: Drift violations if reality conflicts with assumptions         │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                        │
│                                      ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ VERIFIER: Automated Quality Gates                                       │ │
│  │   T1 (<5s): Linters, formatters                                         │ │
│  │   T2 (<60s): Type checking, security scanning                           │ │
│  │   T3 (<300s): Integration tests, coverage measurement                   │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                        │
│                                      ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ JUDGE: Semantic Review + Drift Detection                                │ │
│  │   Evaluates: Code quality, test quality, maintainability               │ │
│  │   Monitors: ASI (Assumption Stability Index) for drift                  │ │
│  │   Decision: ACCEPT | REQUEST_FIX | ESCALATE                             │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                        │
│           ┌──────────────────────────┼──────────────────────────┐            │
│           │                          │                          │            │
│           ▼                          ▼                          ▼            │
│      [ACCEPT]                  [REQUEST_FIX]              [ESCALATE]         │
│      Next sub-plan             Fix cycle (max 3)          Human review       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.1 Tester Agent

**Key Property**: Tester **CANNOT** see implementation code. This isolation prevents tautological tests (tests that merely mirror the code).

**Input**: Feature Specification only
**Output**: Failing tests that verify behavior

```
Tester receives:
├── Feature Specification (WHAT to test)
├── Interface signatures (function names, parameters, return types)
└── Domain language definitions

Tester does NOT receive:
├── Implementation Plan
├── Actual source code
├── Pseudo-code from Architect
└── File paths (beyond test file location)
```

### 5.2 Coder Agent

**Key Property**: Writes minimal code to pass tests. Reports drift violations.

**Input**: Failing tests + Implementation Plan + Drift markers
**Output**: Implementation code + Drift violation flags (if any)

### 5.3 Verifier (Automated Tooling)

**Reference**: _RQ-1_

Three-tier quality gates with strict time budgets:

| Tier | Time Budget  | Checks                             | Failure Action              |
| ---- | ------------ | ---------------------------------- | --------------------------- |
| T1   | <5 seconds   | Linters, formatters, syntax        | Immediate feedback to Coder |
| T2   | <60 seconds  | Type checking, security scanning   | Block until fixed           |
| T3   | <300 seconds | Integration tests, coverage (≥80%) | Detailed report to Judge    |

### 5.4 Judge Agent (Semantic Review + Drift Detection)

**Reference**: _RQ-3b: Validation & Drift Detection_

The Judge owns **all drift detection** (not Coder), providing clean separation of concerns.

#### ASI (Assumption Stability Index) Monitoring

```
ASI = (Stable Assumptions / Total Assumptions) over sliding window

Thresholds:
├── ASI ≥ 0.90: No drift, continue normally
├── ASI 0.60-0.89: Minor drift, log and monitor
├── ASI < 0.60 for 2 consecutive windows: TRIGGER RE-PLANNING
```

#### Three-Tier Escalation

**Reference**: _RQ-3b_

| Tier | Actor        | Confidence Range | Action                                     |
| ---- | ------------ | ---------------- | ------------------------------------------ |
| 1    | Agent (self) | ≥90%             | Proceed with best-guess decision           |
| 2    | Orchestrator | 60-89%           | Research via web search, codebase analysis |
| 3    | Human        | <60%             | Pause, notify user, await response         |

#### Judge Decision Matrix

| Condition                                 | Decision        | Action                             |
| ----------------------------------------- | --------------- | ---------------------------------- |
| All tests pass + T1/T2/T3 pass + No drift | **ACCEPT**      | Proceed to next sub-plan           |
| Tests fail OR quality gate fails          | **REQUEST_FIX** | Return to Coder (max 3 iterations) |
| 3 fix iterations exhausted                | **ESCALATE**    | Human review required              |
| ASI < 0.60 (drift detected)               | **ESCALATE**    | Re-planning required               |
| Breaking change detected                  | **ESCALATE**    | Human approval required            |

### 5.5 Graduated Testing Timing

**Reference**: _RQ-3b_

Not all tests run after every sub-plan. Testing frequency is graduated:

| Test Type         | Frequency           | Rationale                    |
| ----------------- | ------------------- | ---------------------------- |
| Unit tests        | Every sub-plan      | Fast, immediate feedback     |
| Integration tests | Every 2 sub-plans   | Catch interface issues early |
| Regression tests  | Every 3-5 sub-plans | Ensure no breakage           |
| E2E tests         | End only (Phase 4)  | Expensive, final validation  |

### 5.6 Fix Cycle (3-Iteration Limit)

**Reference**: _RQ-2_

When Judge returns REQUEST_FIX:

```
Iteration 1: Coder attempts fix based on Judge feedback
    │
    ▼
Iteration 2: If still failing, provide additional context
    │
    ▼
Iteration 3: Final attempt with comprehensive guidance
    │
    ▼
[If still failing] → ESCALATE to human
```

---

## 6. Phase 4: Final Validation

After **ALL** sub-plans are implemented and individually verified, the complete feature undergoes final validation.

### 6.1 Tribunal (Multi-Model Consensus)

**Reference**: _RQ-1, RQ-2_

The Tribunal is a 3-model consensus mechanism that runs after all sub-plans complete.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRIBUNAL VALIDATION                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  TIMING: After ALL sub-plans complete (not per sub-plan)                     │
│                                                                              │
│  MODELS: 3 independent reviewers                                             │
│  ├── DeepSeek (API)                                                          │
│  ├── Gemini (CLI)                                                            │
│  └── Codex (CLI)                                                             │
│                                                                              │
│  REVIEW DIMENSIONS:                                                          │
│  ├── Security: Vulnerabilities, injection risks, auth flaws                  │
│  ├── Functionality: Correctness, edge cases, error handling                  │
│  ├── Performance: Efficiency, resource usage, scalability                    │
│  ├── Maintainability: Code clarity, documentation, modularity                │
│  └── Test Quality: Coverage, meaningfulness, edge case coverage              │
│                                                                              │
│  CONSENSUS LOGIC:                                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ Models Flagging │ Certainty    │ Action                                 │ │
│  ├─────────────────────────────────────────────────────────────────────────┤ │
│  │ 1 of 3          │ Uncertain    │ Investigate, may be false positive     │ │
│  │ 2 of 3          │ More certain │ Likely real issue, consider auto-fix   │ │
│  │ 3 of 3          │ High         │ Definite issue, prioritize fix         │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  FINDINGS STORAGE: Markdown files OR MCP memory entries (per model)          │
│                                                                              │
│  ANALYSIS AGENT: Reads tribunal outputs and decides:                         │
│  ├── Auto-fix: Spawn fixing agent for clear issues                           │
│  ├── Human Review: Flag for manual inspection                                │
│  └── Proceed: No significant issues found                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 E2E Testing (Final Gate)

**Reference**: _RQ-1_

E2E testing is the **absolute final gate** before merge. No code merges without passing E2E.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         E2E TESTING (FINAL GATE)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  PURPOSE: Ensure feature is usable by real users in real scenarios           │
│                                                                              │
│  TESTING TYPES:                                                              │
│  ├── Visual Verification: UI/UX via browser automation (Playwright/Cypress) │
│  ├── Functional Testing: Complete user flows work as expected                │
│  ├── Edge Case Coverage: Boundary conditions and error states                │
│  └── Cross-Browser: Major browsers (Chrome, Firefox, Safari)                 │
│                                                                              │
│  OUTCOMES:                                                                   │
│  ├── PASS: Proceed to Phase 5 (Merge)                                        │
│  └── FAIL: Return to Phase 3 for fixes (specific sub-plan or full cycle)     │
│                                                                              │
│  PRINCIPLE: "Don't invest tokens in polish until E2E confirms feature works" │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Open Question**: _OQ-11: E2E Testing System_ defines specific implementation details.

---

## 7. Phase 5: Merge & Synthesis

After E2E passes, verified code integrates into the main branch.

### Key Activities

| Activity                     | Description                                                                | Open Question |
| ---------------------------- | -------------------------------------------------------------------------- | ------------- |
| **Conflict Prevention**      | Proactive analysis to identify potential merge conflicts before they occur | —             |
| **Conflict Resolution**      | Automated handling with Easy vs. Complex classification                    | —             |
| **Documentation Generation** | Creating/updating docs for implemented features                            | _OQ-9_        |
| **Learning Extraction**      | Identifying patterns, storing to Long-term Memory                          | _OQ-8_        |
| **CI/CD Integration**        | Pipeline validation and deployment readiness                               | _OQ-13_       |

### Git Workflow

- **Git Worktrees**: Each feature develops in isolated worktree, preventing main branch pollution
- **Merge Strategy**: Squash merge with comprehensive commit message
- **Rollback Capability**: Tagged commits enable quick reversion if issues discovered post-merge

---

## 8. Memory Architecture

ACE uses two memory tiers with distinct purposes.

### 8.1 PostgreSQL Blackboard (Session State)

**Purpose**: Track current execution session, enable agent coordination and handoffs.

**Reference**: _RQ-4c, RQ-4d_

```sql
-- Architect workflow state
CREATE TABLE architect_state (
    session_id UUID PRIMARY KEY,
    master_plan_summary TEXT,
    architecture_constraints JSONB,
    cross_cutting_concerns JSONB,
    current_batch_number INTEGER,
    scout_findings_summary TEXT
);

-- Checkpoint for rollback
CREATE TABLE architect_checkpoints (
    checkpoint_id UUID PRIMARY KEY,
    session_id UUID REFERENCES architect_state(session_id),
    batch_number INTEGER,
    snapshot JSONB,
    quality_metrics JSONB,
    parent_checkpoint_id UUID,  -- For rollback chain
    created_at TIMESTAMP DEFAULT NOW()
);

-- Agent communication
CREATE TABLE agent_messages (
    id SERIAL PRIMARY KEY,
    session_id UUID,
    from_agent VARCHAR(50),
    to_agent VARCHAR(50),
    message_type VARCHAR(20),  -- 'handoff', 'question', 'escalation'
    content JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 8.2 Long-term Learning Memory (Vector DB)

**Purpose**: Persistent storage of patterns, fixes, and learnings that inform future work.

**Reference**: _OQ-7, OQ-8_ (implementation details pending)

**Content Types**:

- Successful code patterns and architectural decisions
- Bug fixes with context (what went wrong, how resolved)
- Quality and security improvement patterns
- Anti-patterns to avoid

**Access Pattern**: Semantic (vector) search based on current task context.

### 8.3 Experience Log (Milestone Library)

**Reference**: _RQ-4c_

```sql
-- Passive logging for future retrieval optimization
CREATE TABLE experience_log (
    log_id UUID PRIMARY KEY,
    task_summary TEXT,
    task_embedding VECTOR(1536),  -- For similarity search
    plan_summary TEXT,
    verification_result JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Phase 1** (current): Passive logging only
**Phase 2** (future): Retrieval-augmented planning

---

## 9. Infrastructure Components

### 9.1 Orchestrator (SDK-Based Control Unit)

**Reference**: _RQ-2, RQ-4c_

The Orchestrator is the **only SDK-based component**. All other agents run via CLI.

**Responsibilities**:

- Read pipeline state from PostgreSQL Blackboard
- Invoke CLI agents via subprocess with MCP-scoped permissions
- Manage workflow sequencing and batching
- Handle context resets between batches
- Route escalations to humans

**What Orchestrator Does NOT Do**:

- Write code
- Make implementation decisions
- Perform semantic review

```python
# Conceptual Orchestrator Loop
while not complete:
    state = read_blackboard()

    if state.phase == "PLANNING":
        if not state.scout_complete:
            invoke_cli("scout", mode="initial")
        elif not state.architect_stage1_complete:
            invoke_cli("architect", stage=1)
        elif not state.verification_complete:
            invoke_cli("sub_plan_verifier")
        else:
            state.phase = "EXECUTION"

    elif state.phase == "EXECUTION":
        current_subplan = state.next_subplan()
        if current_subplan:
            run_tdd_cycle(current_subplan)
        else:
            state.phase = "FINAL_VALIDATION"

    elif state.phase == "FINAL_VALIDATION":
        run_tribunal()
        run_e2e_tests()
        state.phase = "MERGE"
```

### 9.2 Supervisor (Termination Detection)

**Reference**: _OQ-15_ (implementation details pending)

**Purpose**: Monitor CLI-based agent execution and determine next actions.

**Termination States to Detect**:
| State | Meaning | Action |
|-------|---------|--------|
| SUCCESS | Task completed | Mark complete, proceed |
| CONTEXT_LIMIT | 70% threshold reached | Serialize state, spawn continuation |
| ERROR | Unrecoverable error | Log, escalate |
| BLOCKER | Uncertainty requiring escalation | Route to Q&A Orchestrator |
| QUESTION | Agent submitted question | Queue for Q&A Orchestrator |

### 9.3 Q&A Orchestrator

**Reference**: _OQ-16_ (implementation details pending)

**Purpose**: Answer agent questions, perform web research, escalate to humans.

**Mechanism**:

1. Agents submit questions to database queue
2. Q&A Orchestrator monitors queue
3. Orchestrator answers using web research or codebase analysis
4. If cannot resolve: escalate to human
5. Response delivered back to waiting agent

---

## 10. Layered Validation Architecture

**Reference**: _RQ-1: Testing & Validation Strategy_

ACE implements a 6-layer defense-in-depth validation system.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LAYERED VALIDATION ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LAYER 0: PROPERTY DEFINITION (Master Plan)                                  │
│    Test STRATEGY defined by developer: risk priorities, properties           │
│    Example: "Auth flows 95% covered", "API response < 200ms"                 │
│                                                                              │
│  LAYER 1: TEST SPECIFICATIONS (Sub-Plans)                                    │
│    Acceptance criteria, edge cases, behavioral contracts                     │
│    Human/Architect defines WHAT; NOT execution agent                         │
│    94.3% success rate vs 68% for agent-autonomous specs                      │
│                                                                              │
│  LAYER 2: TDD MICRO-ITERATION (Tester + Coder)                               │
│    Agent implements HOW to test                                              │
│    Red → Green → Refactor cycle                                              │
│    Commit on green, revert on red                                            │
│                                                                              │
│  LAYER 3: JUDGE AGENT (Per-Cycle Evaluation)                                 │
│    Evaluate: continue | escalate | complete                                  │
│    Detects tautological tests                                                │
│    Property validation + objective completion criteria                       │
│                                                                              │
│  LAYER 4: MULTI-STAGE QUALITY GATES (Verifier)                               │
│    Gate A: Static analysis (<5s)                                             │
│    Gate B: Property + unit tests (seconds-minutes)                           │
│    Gate C: Integration tests + coverage (≥80%)                               │
│    Mutation testing >70% kill rate                                           │
│                                                                              │
│  LAYER 5: TRIBUNAL + E2E (Final Gate)                                        │
│    3-model consensus on semantic correctness                                 │
│    E2E tests as ultimate pass/fail                                           │
│    Human review for security-critical paths                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 11. System Boundaries

### In Scope

- Transforming master plans into production-ready code
- Multi-model cross-validation for quality assurance
- TDD-first automated testing and verification
- E2E testing as final gate before merge
- Merge conflict prevention and resolution
- Documentation generation
- Pattern learning and knowledge accumulation
- Real-time observability and human oversight
- Git worktree isolation and management
- CI/CD pipeline integration

### Out of Scope

- **Master plan creation** (handled externally: Gemini Gems, Claude Projects, Custom GPTs)
- Market analysis or product decisions
- Infrastructure provisioning beyond initial setup
- User authentication for ACE system itself
- Direct production deployment (outputs deployment-ready code, not deployment itself)

---

## 12. Open Questions Summary

### Resolved Questions

| ID    | Question                        | Resolution Reference                                          |
| ----- | ------------------------------- | ------------------------------------------------------------- |
| RQ-1  | Testing & Validation Strategy   | Layered Validation Architecture (6 layers)                    |
| RQ-2  | Execution Strategy              | ACE Combined Architecture v2.0 (7 agents)                     |
| RQ-3a | Pre-Implementation Architecture | Three-Mode Scout + Dual-Output Architect                      |
| RQ-3b | Validation & Drift Detection    | Judge-Based Detection + Graduated Testing                     |
| RQ-4a | Master Plan Structure           | 8-Section Template + Three-Tier Boundaries                    |
| RQ-4b | Sub-Plan Schema Content         | Feature Spec (8 sections) + Implementation Plan (14 sections) |
| RQ-4c | Plan Decomposition Process      | Two-Stage Architect Workflow                                  |
| RQ-4d | Sub-Plan Creation Workflow      | Layered Coherence Architecture                                |

### Open Questions (Pending Research)

| ID    | Question                      | Priority                 | Blocks               |
| ----- | ----------------------------- | ------------------------ | -------------------- |
| OQ-6  | Breaking-Change Detection     | HIGH                     | Execution safety     |
| OQ-7  | Memory Layer Implementation   | MEDIUM                   | Learning system      |
| OQ-8  | Learning Integration Points   | MEDIUM                   | Plan quality         |
| OQ-9  | Documentation Strategy        | MEDIUM                   | Phase 5              |
| OQ-10 | Sub-plan Review Necessity     | RESOLVED via RQ-3a/RQ-4d | —                    |
| OQ-11 | E2E Testing System            | MEDIUM                   | Final gate           |
| OQ-12 | Cross-Validation Consensus    | MEDIUM                   | Tribunal             |
| OQ-13 | CI/CD Pipeline Strategy       | MEDIUM                   | Deployment           |
| OQ-14 | CLI-Based Orchestration       | HIGH                     | All CLI execution    |
| OQ-15 | Agent Termination Detection   | HIGH                     | Autonomous operation |
| OQ-16 | Q&A Orchestrator Architecture | MEDIUM                   | Agent guidance       |

---

## 13. Cost Model

### Subscription-First Approach

| Execution Method                       | Use Cases                               | Cost Model         |
| -------------------------------------- | --------------------------------------- | ------------------ |
| CLI Tools (Claude Code, Codex, Gemini) | Primary agent execution                 | Subscription-based |
| Claude SDK                             | Orchestrator only                       | API (minimal)      |
| DeepSeek, GLM, KimiK2 APIs             | Tribunal validation, cheap verification | API (low-cost)     |

### Token Budget Guidelines

| Component             | Budget | Notes                    |
| --------------------- | ------ | ------------------------ |
| Scout findings        | 10-15k | Compressed to Blackboard |
| Feature Specification | 5-10k  | Per sub-plan             |
| Implementation Plan   | 15-20k | Per sub-plan             |
| Working context       | 50-90k | Active reasoning         |
| Buffer                | 30%    | Safety margin            |

---

## 14. Observability UI

**Purpose**: Real-time visibility into agent operations without requiring constant intervention.

### Features

| Feature                 | Description                                                         |
| ----------------------- | ------------------------------------------------------------------- |
| **Live Agent Feed**     | Real-time streaming of agent thoughts, tool usage, terminal outputs |
| **Progress Board**      | Kanban-style view: Backlog → In Progress → Review → Done            |
| **Control Interface**   | Modify agent prompts, add/remove tools, edit memory entries         |
| **Notification System** | Alerts when human input required                                    |

### Technical Implementation

- WebSocket connection for real-time streaming
- Aggregated progress across all active agents
- Full audit log of all agent actions and decisions

---

## Appendix A: Complete PostgreSQL Schema

```sql
-- ============================================================================
-- ARCHITECT WORKFLOW
-- ============================================================================

CREATE TABLE architect_state (
    session_id UUID PRIMARY KEY,
    master_plan_summary TEXT NOT NULL,
    architecture_constraints JSONB,
    cross_cutting_concerns JSONB,
    current_batch_number INTEGER DEFAULT 0,
    scout_findings_summary TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE architect_checkpoints (
    checkpoint_id UUID PRIMARY KEY,
    session_id UUID REFERENCES architect_state(session_id),
    batch_number INTEGER NOT NULL,
    snapshot JSONB NOT NULL,
    quality_metrics JSONB,
    parent_checkpoint_id UUID REFERENCES architect_checkpoints(checkpoint_id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- COHERENCE TRACKING
-- ============================================================================

CREATE TABLE batch_state (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES architect_state(session_id),
    batch_num INTEGER NOT NULL,
    milestone_ids UUID[] NOT NULL,
    coherence_summary TEXT,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'verified', 'failed')),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE cross_plan_dependencies (
    id SERIAL PRIMARY KEY,
    from_plan_id UUID NOT NULL,
    to_plan_id UUID NOT NULL,
    interface_definition JSONB NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE shared_assumptions (
    id SERIAL PRIMARY KEY,
    assumption_text TEXT NOT NULL,
    applies_to_plan_ids UUID[] NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    verification_result TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE versioned_artifacts (
    id SERIAL PRIMARY KEY,
    artifact_type VARCHAR(50) NOT NULL CHECK (artifact_type IN ('feature_spec', 'impl_plan', 'milestone')),
    artifact_id UUID NOT NULL,
    version INTEGER NOT NULL,
    content JSONB NOT NULL,
    batch_num INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- AGENT COMMUNICATION
-- ============================================================================

CREATE TABLE agent_messages (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES architect_state(session_id),
    from_agent VARCHAR(50) NOT NULL,
    to_agent VARCHAR(50) NOT NULL,
    message_type VARCHAR(20) NOT NULL CHECK (message_type IN ('handoff', 'question', 'escalation', 'response')),
    content JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'resolved')),
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

-- ============================================================================
-- EXPERIENCE LOGGING (FOR FUTURE OPTIMIZATION)
-- ============================================================================

CREATE TABLE experience_log (
    log_id UUID PRIMARY KEY,
    task_summary TEXT NOT NULL,
    task_embedding VECTOR(1536),  -- Requires pgvector extension
    plan_summary TEXT,
    verification_result JSONB,
    session_id UUID REFERENCES architect_state(session_id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX idx_checkpoints_session ON architect_checkpoints(session_id);
CREATE INDEX idx_batch_state_session ON batch_state(session_id);
CREATE INDEX idx_messages_session ON agent_messages(session_id);
CREATE INDEX idx_messages_status ON agent_messages(status) WHERE status = 'pending';
CREATE INDEX idx_experience_embedding ON experience_log USING ivfflat (task_embedding vector_cosine_ops);
```

---

## Appendix B: Agent Context Flow

| Agent                 | Receives                                              | Outputs                                                            |
| --------------------- | ----------------------------------------------------- | ------------------------------------------------------------------ |
| **Orchestrator**      | Pipeline state, agent signals                         | Agent invocations, state updates                                   |
| **Scout**             | Master plan (M1) OR sub-plan (M2/M3), codebase access | Ranked file/function locations, structure analysis                 |
| **Architect**         | Master plan, Scout findings                           | Milestones (Stage 1), Feature Spec + Implementation Plan (Stage 2) |
| **Sub-Plan Verifier** | Feature Spec, Implementation Plan, batch context      | Verification result (pass/revise/escalate), specific feedback      |
| **Tester**            | Feature Specification ONLY (no Implementation Plan)   | Failing tests, test rationale                                      |
| **Coder**             | Failing tests, Implementation Plan, drift markers     | Implementation code, drift violation flags                         |
| **Verifier**          | Code diff, tests                                      | Pass/fail per tier (T1/T2/T3), metrics                             |
| **Judge**             | Implementation, tests, requirements, ASI metrics      | Accept/Fix/Escalate decision, drift report                         |

---

## Appendix C: Key Metrics and Thresholds

| Metric                           | Threshold           | Source  |
| -------------------------------- | ------------------- | ------- |
| Test coverage                    | ≥80% baseline       | _RQ-1_  |
| Mutation testing kill rate       | >70%                | _RQ-1_  |
| Sub-Plan Verifier: Coherence     | ≥0.9                | _RQ-4d_ |
| Sub-Plan Verifier: Completeness  | ≥0.8                | _RQ-4d_ |
| Sub-Plan Verifier: Executability | ≥0.85               | _RQ-4d_ |
| ASI drift trigger                | <0.60 for 2 windows | _RQ-3b_ |
| Context window safety            | 70% max utilization | _RQ-2_  |
| Fix cycle limit                  | 3 iterations        | _RQ-2_  |
| Verification batch size          | 5 (adaptive 3-7)    | _RQ-4c_ |

---

_Version: v3_
_Status: Ready for OQ-6 research and implementation planning_
_Previous Version: v2_
