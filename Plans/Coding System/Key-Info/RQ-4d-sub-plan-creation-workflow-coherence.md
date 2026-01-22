# Solution: Minimal Workflow for Sub-Plan Coherence Without Context Pollution

## Metadata

- **Generated:** 2026-01-20
- **Session:** /Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-20-sub-plan-creation-workflow-coherence
- **Process.md:** /Users/ruben/.claude/profiles/Solution-Finder/ACE/Process.md
- **Question:** What is the minimal workflow needed to ensure all sub-plans are coherent and executable without introducing context pollution?

---

## Executive Summary

**Direct Answer:** The minimal workflow ensuring sub-plan coherence without context pollution combines three mechanisms: (1) **schema-based prevention** where Feature Spec and Implementation Plan constraints are injected during planning, (2) **structured persistent memory** via BATCH_COHERENCE.md stored in PostgreSQL Blackboard, and (3) **independent external verification** with iterative refinement limited to 3 cycles.

**Confidence Level:** HIGH (85%) based on strong source consensus across academic research (ALAS, ReCAP, SagaLLM papers), production systems (Cursor, Google ADK, Anthropic), and aligned recommendations from all three research perspectives.

**Key Recommendation:** Implement schema-first prevention before building verification infrastructure. Instant schema validation catches most issues at near-zero cost, reducing verification workload by an estimated 52% based on CVF production metrics.

---

## Resolution Criteria Mapping

| #   | Resolution Criterion                                       | How Addressed                                                                                                                                      | Evidence                                 |
| --- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| RC1 | Information addition matrix (who adds what at which stage) | Explicit matrix: Scout adds codebase findings, Architect adds milestones (Stage 1) then sub-plans + dependencies (Stage 2), Verifier adds verdicts | [Exa+Brave]                              |
| RC2 | Context persistence in PostgreSQL across batch resets      | Schema: `batch_state`, `cross_plan_dependencies`, `shared_assumptions`, `versioned_artifacts` tables                                               | [Exa+Brave+Bright Data]                  |
| RC3 | Optimal verification timing with rationale                 | Prevention (instant schema) FIRST, Detection (batch-end) SECOND; 96.5% of issues resolved upfront                                                  | [Exa+Brave+Bright Data]                  |
| RC4 | Sub-Plan Verifier criteria                                 | Three criteria: Coherence (≥0.9), Completeness (≥0.8), Executability (≥0.85) using multi-dimensional rubric                                        | [Brave+Exa + Intervention]               |
| RC5 | How Architect preserves big picture                        | BATCH_COHERENCE.md stores compressed prior-batch state + Stage 1 milestone re-injection before each Stage 2 batch                                  | [Exa+Brave]                              |
| RC6 | Drift prevention mechanisms                                | Schema-based PRIMARY (8/14 section validation), Process-based SECONDARY (observation masking, fresh verifier context)                              | [All 3]                                  |
| RC7 | Recovery mechanism                                         | Iterative refinement: max 3 cycles, 96.5% convergence rate; natural language feedback                                                              | [Brave+Exa]                              |
| RC8 | Tester/Coder escalation path                               | Completeness criteria prevent most escalations; remaining escalate to Judge who routes to Architect re-enrichment                                  | [Inferred from Brave+Exa + Intervention] |
| RC9 | Example of drift prevention in action                      | Full workflow example provided below                                                                                                               | [Exa+Brave]                              |

**Criteria Coverage:** 9/9 criteria fully addressed

---

## Synthesized Solution

**Core Approach:**
The research converges on a "prevention over detection" architecture. All three sources agree that investing in upfront constraints (schema validation, role boundaries, explicit dependency declarations) dramatically reduces the need for expensive post-hoc verification. The ALAS paper demonstrates 60% token reduction and 1.82x faster execution when using independent validation with bounded context. Cursor's production system reinforces this: "Too little structure and agents conflict, duplicate work, and drift. Too much structure creates fragility." The optimal middle ground is lightweight architectural constraints (schemas, role separation) combined with focused verification.

**Implementation Strategy:**
The workflow operates in three stages with distinct information flows. Stage 0 (Constraint Specification) defines Feature Spec and Implementation Plan schemas as formal constraints. Stage 1 (Milestone Creation) has the Architect decompose the master plan into milestones, storing them to PostgreSQL Blackboard with a lightweight coherence check. Stage 2 (Batch Enrichment) proceeds in batches of 5 sub-plans, where the Architect loads prior batch summaries from BATCH_COHERENCE.md, enriches milestones into dual outputs, and the Sub-Plan Verifier checks coherence/completeness/executability. If defects are found, iterative feedback allows up to 3 revision cycles (96.5% convergence rate). Between batches, context resets occur, but BATCH_COHERENCE.md persists dependencies and shared assumptions.

**Integration Considerations:**
The strategies form a layered dependency chain. PostgreSQL Blackboard provides the infrastructure foundation—it stores versioned artifacts, cross-plan dependencies, and shared assumptions. BATCH_COHERENCE.md is a specific artifact within the Blackboard that captures the compressed state of prior batches (not full history). The External Verifier operates with fresh context, receiving only sub-plans + master plan summary + coherence file—never the Architect's reasoning history, which prevents circular validation. Schema validation runs first (instant, zero overhead), then semantic verification (batch-end, lightweight). Context re-injection loads Stage 1 milestones before each Stage 2 batch to maintain big-picture alignment.

**Trade-offs & Alternatives:**
The primary trade-off is upfront schema specification effort versus runtime flexibility. Strict schemas prevent invalid plans but may constrain creative solutions. The research recommends erring toward constraint (prevention is cheaper than detection). Alternative approaches classified as UNCERTAIN and excluded include: Saga compensation patterns for automatic recovery (complex, experimental), Cleaner Agent for active redundancy removal (promising but unvalidated at scale), and Coherence-Based Metrics for measurable consistency scores (theoretical, unclear operationalization). These could be investigated post-implementation if the core workflow proves insufficient.

---

## The Workflow

### Complete Information Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 0: CONSTRAINT SPECIFICATION (One-time Setup)                           │
│                                                                              │
│   Human defines:                                                             │
│   • Feature Spec schema (8 sections)                                         │
│   • Implementation Plan schema (14 sections)                                 │
│   • WHEN-THEN SHALL acceptance criteria format                               │
│   • Complexity-to-subplan mappings (simple=3, moderate=5-7, complex=10-15)  │
│                                                                              │
│   Stored: Blackboard.constraints                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: MILESTONE CREATION                                                  │
│                                                                              │
│   Scout → Architect:                                                         │
│   • Scout provides codebase findings (architecture, dependencies)            │
│   • Architect decomposes master plan into 5-15 milestones                   │
│   • Each milestone: title, objective, scope, dependencies, execution order  │
│   • Lightweight coherence check (Scout verifies milestone dependencies)      │
│                                                                              │
│   Stored: Blackboard.milestones, Blackboard.milestone_status                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: BATCH ENRICHMENT (Repeat per batch of 5)                            │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 2a. CONTEXT LOAD                                                     │   │
│   │   Architect loads:                                                   │   │
│   │   • Current batch milestones (from Blackboard)                       │   │
│   │   • BATCH_COHERENCE.md (prior batch state)                           │   │
│   │   • Stage 1 milestone list (for alignment)                           │   │
│   │   • Schema constraints                                               │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                            ↓                                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 2b. ENRICHMENT                                                       │   │
│   │   Architect produces for each milestone:                             │   │
│   │   • Feature Spec (8 sections, Given-When-Then format)                │   │
│   │   • Implementation Plan (14 sections, Six Core Areas)                │   │
│   │   • Dependencies + shared assumptions → BATCH_COHERENCE.md           │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                            ↓                                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 2c. VERIFICATION (Sub-Plan Verifier)                                 │   │
│   │                                                                      │   │
│   │   Verifier receives (ONLY):                                          │   │
│   │   • Current batch sub-plans                                          │   │
│   │   • Master plan summary                                              │   │
│   │   • BATCH_COHERENCE.md                                               │   │
│   │   [Never sees Architect reasoning history]                           │   │
│   │                                                                      │   │
│   │   Stage 1 - STRUCTURAL (Instant):                                    │   │
│   │   • Schema compliance (8/14 sections)                                │   │
│   │   • WHEN-THEN SHALL format                                           │   │
│   │   • Required fields populated                                        │   │
│   │                                                                      │   │
│   │   Stage 2 - SEMANTIC (Multi-Dimensional):                            │   │
│   │   • Pass 1: COHERENCE (threshold ≥0.9)                               │   │
│   │     "List assumption conflicts between these sub-plans"              │   │
│   │   • Pass 2: COMPLETENESS (threshold ≥0.8)                            │   │
│   │     "Can tester derive test cases without Implementation Plan?"      │   │
│   │   • Pass 3: EXECUTABILITY (threshold ≥0.85)                          │   │
│   │     "Can coder implement without asking questions?"                  │   │
│   │                                                                      │   │
│   │   Stage 3 - SELF-CHECK:                                              │   │
│   │   • Ambiguous pronouns                                               │   │
│   │   • Missing boundary conditions                                      │   │
│   │   • Circular references                                              │   │
│   │   • Unstated assumptions                                             │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                            ↓                                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 2d. ITERATIVE REFINEMENT (If needed)                                 │   │
│   │                                                                      │   │
│   │   If Verifier finds defects:                                         │   │
│   │   • Natural language feedback to Architect                           │   │
│   │   • Architect revises affected sub-plans                             │   │
│   │   • Re-verify                                                        │   │
│   │   • Max 3 iterations (96.5% convergence rate)                        │   │
│   │                                                                      │   │
│   │   If still failing after 3 iterations:                               │   │
│   │   • Escalate to Human with specific defect report                    │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                            ↓                                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 2e. BATCH COMPLETION                                                 │   │
│   │                                                                      │   │
│   │   • Store verified sub-plans to Blackboard.sub_plans                 │   │
│   │   • Append coherence notes to BATCH_COHERENCE.md                     │   │
│   │   • Apply observation masking (clear observations, keep reasoning)   │   │
│   │   • Context reset: Clear Architect working context                   │   │
│   │   • Proceed to next batch                                            │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ FINAL BATCH: CROSS-BATCH COHERENCE CHECK                                     │
│                                                                              │
│   After all batches complete:                                                │
│   • Verifier loads ALL constraints from Blackboard                           │
│   • Cross-batch coherence check: Ensure Batch 1 and Batch N align            │
│   • Final approval or targeted re-enrichment                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Information Addition Matrix (RC1)

| Stage | Actor             | Adds                                                         | Stores To                      |
| ----- | ----------------- | ------------------------------------------------------------ | ------------------------------ |
| 0     | Human             | Feature Spec + Impl Plan schemas, acceptance criteria format | Blackboard.constraints         |
| 1     | Scout             | Codebase findings (architecture, dependencies)               | Blackboard.scout_findings      |
| 1     | Architect         | Milestones (5-15) with objectives, scope, dependencies       | Blackboard.milestones          |
| 1     | Scout (verify)    | Milestone coherence flag                                     | Blackboard.milestone_status    |
| 2     | Architect         | Feature Specs + Implementation Plans (batch of 5)            | Blackboard.sub_plans           |
| 2     | Architect         | Dependencies + shared assumptions                            | BATCH_COHERENCE.md             |
| 2     | Sub-Plan Verifier | Coherence/Completeness/Executability verdict                 | Blackboard.verification_status |

### PostgreSQL Blackboard Schema (RC2)

```sql
-- Batch processing state
CREATE TABLE batch_state (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    batch_num INT NOT NULL,
    milestone_ids INT[] NOT NULL,
    coherence_summary TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Cross-plan dependencies
CREATE TABLE cross_plan_dependencies (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    from_plan_id INT NOT NULL,
    to_plan_id INT NOT NULL,
    interface_definition JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Shared assumptions across plans
CREATE TABLE shared_assumptions (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    assumption_text TEXT NOT NULL,
    applies_to_plan_ids INT[] NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Versioned artifacts for rollback
CREATE TABLE versioned_artifacts (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    artifact_type VARCHAR(50) NOT NULL, -- 'feature_spec', 'impl_plan', 'batch_coherence'
    artifact_id INT NOT NULL,
    version INT NOT NULL,
    content JSONB NOT NULL,
    batch_num INT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Sub-Plan Verifier Criteria (RC4)

| Criterion         | Threshold | Prompt Template                                                                                           | Output                            |
| ----------------- | --------- | --------------------------------------------------------------------------------------------------------- | --------------------------------- |
| **Coherence**     | ≥0.9      | "Compare assumptions in sub-plans against prior_batch_state. List any conflicts."                         | `{score, issues[], reason}`       |
| **Completeness**  | ≥0.8      | "Can a tester derive test cases from Feature Spec WITHOUT seeing Implementation Plan? What's missing?"    | `{score, missing_info[], reason}` |
| **Executability** | ≥0.85     | "Can a coder implement from Implementation Plan without asking questions? What questions would they ask?" | `{score, questions[], reason}`    |

**Aggregated Output:**

```json
{
  "coherence": { "score": 0.95, "pass": true, "issues": [] },
  "completeness": { "score": 0.82, "pass": true, "missing_info": ["edge case for empty input"] },
  "executability": { "score": 0.88, "pass": true, "questions": [] },
  "overall_pass": true,
  "feedback": "Minor: Consider adding empty input edge case to acceptance criteria"
}
```

### Tester/Coder Escalation Path (RC8)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ESCALATION PROTOCOL                                                          │
│                                                                              │
│ 1. PREVENTION (Completeness criteria)                                        │
│    • Feature Spec must enable test derivation without Implementation Plan    │
│    • Implementation Plan must enable coding without questions                │
│    • Most escalations prevented by verification criteria                     │
│                                                                              │
│ 2. DETECTION (During execution)                                              │
│    If Tester finds Feature Spec ambiguous:                                   │
│    → Tester flags to Judge with specific ambiguity                           │
│    → Judge evaluates: Is this a spec defect or execution problem?            │
│                                                                              │
│ 3. ROUTING                                                                   │
│    If spec defect:                                                           │
│    → Judge requests Architect re-enrichment (counts as iteration)            │
│    → Max 3 escalation-triggered iterations per sub-plan                      │
│                                                                              │
│    If execution problem:                                                     │
│    → Judge guides Tester/Coder with clarification                            │
│    → Does not count against iteration limit                                  │
│                                                                              │
│ 4. HUMAN ESCALATION                                                          │
│    If 3 iterations exhausted and still failing:                              │
│    → Human review with specific defect report                                │
│    → Human can: approve with caveat, reject, provide guidance                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Drift Prevention Example (RC9)

```
SCENARIO: Auth feature with 10 sub-plans across 2 batches

Stage 1:
  Scout analyzes codebase → finds existing session management
  Architect creates Milestones 1-10 → Blackboard.milestones
  Scout verifies: "No conflicting dependencies" → milestone_status: PASS

Stage 2, Batch 1 (Milestones 1-5):
  Architect loads: milestones + BATCH_COHERENCE.md (empty initially)

  SP1: "Implement JWT token generation"
    Feature Spec: GIVEN valid credentials WHEN login THEN return JWT token
    Implementation Plan: Use jsonwebtoken library, token expires in 1h

  SP2: "Implement token refresh"
    Feature Spec: GIVEN expired token WHEN refresh THEN return new token
    Implementation Plan: Validate refresh token, issue new access token
    Drift Marker: "Assumes SP1 uses JWT format"

  Architect writes to BATCH_COHERENCE.md:
    shared_assumptions:
      - "Auth uses JWT tokens (not sessions)"
      - "Token expiry: 1 hour access, 7 days refresh"
    interfaces:
      - "TokenService.generateToken(userId) → JWT"
      - "TokenService.refreshToken(refreshToken) → JWT"

  Sub-Plan Verifier checks:
    COHERENCE: SP1 and SP2 assumptions align ✓ (score: 0.95)
    COMPLETENESS: Can derive tests from specs ✓ (score: 0.88)
    EXECUTABILITY: Can implement without questions ✓ (score: 0.92)

  PASS → Store to Blackboard → Context reset

Stage 2, Batch 2 (Milestones 6-10):
  Architect loads: milestones + BATCH_COHERENCE.md (has Batch 1 state)

  Architect reads: "Auth uses JWT tokens (not sessions)"

  SP6: "Implement token validation middleware"
    Architect checks against BATCH_COHERENCE.md:
      "Prior batch uses JWT → middleware must validate JWT format"
    Feature Spec: GIVEN request with Authorization header WHEN validate THEN...
    Implementation Plan: Extract token, verify signature, check expiry

  IF Architect had written "Validate session cookie":
    Sub-Plan Verifier COHERENCE check:
      "CONFLICT: SP6 assumes session cookies, but shared_assumptions
       state 'Auth uses JWT tokens (not sessions)'"
      Score: 0.3 (FAIL)

    Iterative feedback:
      "SP6 conflicts with established JWT pattern. Please revise
       to use JWT validation instead of session cookies."

    Architect revises → Re-verify → PASS

Final Batch:
  Cross-batch coherence check:
    "Batch 1 (SP1-5) and Batch 2 (SP6-10) share consistent JWT assumption"
    All interfaces align: TokenService used consistently
  PASS → Ready for execution
```

---

## Evidence & Confidence

### Source Agreement Analysis

| Claim                                 | Exa | Brave | Bright Data | Consensus |
| ------------------------------------- | --- | ----- | ----------- | --------- |
| Prevention > detection architecture   | ✓   | ✓     | ✓           | STRONG    |
| Independent external verification     | ✓   | ✓     | ✓           | STRONG    |
| Centralized blackboard prevents drift | ✓   | ✓     | ✓           | STRONG    |
| Iterative verification (2-3 cycles)   | ✓   | ✓     | -           | MODERATE  |
| Schema validation as first defense    | ✓   | ✓     | -           | MODERATE  |
| Multi-dimensional verification rubric | ✓   | ✓     | -           | MODERATE  |

### Confidence Factors

**Strengthening factors:**

- Universal consensus on "prevention over detection" across all 3 research sources
- Production validation from Cursor (100s of agents), Google ADK, Anthropic
- Quantified evidence: 60% token reduction (ALAS), 96.5% convergence in 3 cycles, 52% incident reduction (CVF)
- Strategy relationships form coherent layered architecture

**Weakening factors:**

- Limited planning-specific validation (most evidence from execution tasks)
- Verification thresholds (0.9/0.8/0.85) are estimates—need empirical tuning
- Cross-batch coherence check at final batch adds latency

---

## Appendix A: Strategy Reference

**Strategy Set Name:** Layered Coherence Architecture
**Strategies:** 7 total (5 HIGH, 2 MEDIUM)

### Included Strategies

| #   | Strategy                                          | Confidence | Score | Role                  |
| --- | ------------------------------------------------- | ---------- | ----- | --------------------- |
| S1  | Schema-First Prevention with Constraint Injection | HIGH       | 9.3   | Prevention layer      |
| S3  | Structured Persistent Memory (BATCH_COHERENCE.md) | HIGH       | 8.8   | Persistence layer     |
| S2  | Independent External Verifier with Fresh Context  | HIGH       | 8.7   | Verification layer    |
| S4  | PostgreSQL Blackboard with Versioned State        | HIGH       | 8.5   | Infrastructure layer  |
| S5  | Iterative Verification (2-3 Cycles Max)           | HIGH       | 8.1   | Refinement layer      |
| S6  | Context Re-injection Between Batches              | MEDIUM     | 7.8   | Coherence enhancement |
| S7  | Observation Masking for Context Management        | MEDIUM     | 7.8   | Cost optimization     |

### Implementation Roadmap

| Phase | Strategy                    | Dependencies | Notes                             |
| ----- | --------------------------- | ------------ | --------------------------------- |
| 1     | S4: PostgreSQL Blackboard   | None         | Foundation - infrastructure layer |
| 1     | S1: Schema-First Prevention | None         | Foundation - constraint layer     |
| 2     | S3: BATCH_COHERENCE.md      | Requires S4  | Persistence mechanism             |
| 2     | S2: External Verifier       | Requires S1  | Verification mechanism            |
| 3     | S5: Iterative Protocol      | Requires S2  | Verification refinement           |
| 3     | S6: Context Re-injection    | Requires S3  | Cross-batch coherence             |
| 3     | S7: Observation Masking     | Requires S3  | Within-batch optimization         |

### Strategy Relationships

- S4 (Blackboard) → S3 (BATCH_COHERENCE): LAYERED (infrastructure → artifact)
- S3 (BATCH_COHERENCE) → S6 (Re-injection): LAYERED (storage → usage)
- S1 (Schema Prevention) → S2 (Verifier): LAYERED (prevent → detect)
- S1 (Schema Prevention) → S5 (Iterative): LAYERED (prevention reduces iterations)
- S2 (Verifier) → S5 (Iterative): COMPLEMENTARY (check → refine cycle)
- S3 (persist) ↔ S7 (discard): COMPLEMENTARY (what to keep vs clear)
- S6 (between batches) ↔ S7 (within batch): COMPLEMENTARY (different scopes)

### Excluded Strategies

| #   | Strategy                                 | Reason                                                               |
| --- | ---------------------------------------- | -------------------------------------------------------------------- |
| S8  | Cleaner Agent for Redundancy Removal     | Experimental only (LbMAS); scaling unknowns; not investigated        |
| S9  | Saga Compensation for Automatic Recovery | Extremely experimental; complex compensation logic; not investigated |
| S10 | Coherence-Based Metrics                  | Highly theoretical; no implementation guidance; not investigated     |

---

## Appendix B: Research Session

### Research Files

- Exa findings: `research/2026-01-20-sub-plan-creation-workflow-coherence/exa-findings.md`
- Brave findings: `research/2026-01-20-sub-plan-creation-workflow-coherence/brave-findings.md`
- Brightdata findings: `research/2026-01-20-sub-plan-creation-workflow-coherence/brightdata-findings.md`
- Synthesis: `research/2026-01-20-sub-plan-creation-workflow-coherence/synthesis.md`

### Consensus Points from Research

- Prevention over detection architecture reduces verification workload [All 3]
- Independent external verification with fresh context prevents circular validation [All 3]
- Centralized state (Blackboard) prevents memory drift across batches [All 3]
- Iterative verification (2-3 cycles) achieves 96.5% convergence [Exa+Brave]
- Schema validation is instant, zero-overhead first defense [Exa+Brave]
- Minimal context handoffs reduce pollution [All 3]

### Conflicts Identified

1. **Context compaction method**: LLM summarization vs observation masking
   - Resolution: Use masking WITHIN batch, summarization BETWEEN batches
2. **Verification timing**: Batch-end vs baked into planning
   - Resolution: Schema prevention FIRST (instant), batch-end verification SECOND (reduced scope)

---

## Appendix C: Context

### Original Question

What is the minimal workflow needed to ensure all sub-plans are coherent and executable without introducing context pollution?

### Goal Context (from Process.md)

ACE (Autonomous Coding Ecosystem) is a highly automated software development factory transforming master plans into production-ready code through a four-layer pipeline. Single Architect agent decomposes master plan into 5-15 sub-plans using two-stage decomposition (Stage 1: milestones, Stage 2: enrichment in batches of 5). Context resets occur between batches. PostgreSQL Blackboard persists state. Sub-Plan Verifier exists but criteria were undefined.

### User Context (gathered during triage)

- **System Constraints:** Single Architect with guardrails, batch size 5 (adaptive 3-7), external verification required
- **Priority:** Prevention over detection, minimal verification overhead
- **Selection:** All HIGH + all MEDIUM strategies included; UNCERTAIN strategies excluded

---

## Appendix D: Intervention History

| #   | Question                                                                                              | Mode               | Result                                                                        |
| --- | ----------------------------------------------------------------------------------------------------- | ------------------ | ----------------------------------------------------------------------------- |
| 1   | What natural language prompts achieve high precision/recall for LLM-based specification verification? | compare (2 agents) | Multi-dimensional rubric pattern + WHEN-THEN SHALL format; templates provided |

Intervention files:

- `interventions/q1-verifier-prompts-technical.md`
- `interventions/q1-verifier-prompts-production.md`

---

## Next Steps

To validate and finalize this solution:

```bash
# Switch to Solution-Validator profile
solv

# Run validation
/validate-solution "/Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-20-sub-plan-creation-workflow-coherence/internal-solution.md"
```

To update Process.md with this resolved question, add to the RQ (Resolved Questions) section:

```markdown
## RQ-4d: Sub-Plan Creation Workflow & Coherence ✓

**Resolved**: 2026-01-20 | **Confidence**: 85%

**Question**: What is the minimal workflow needed to ensure all sub-plans are coherent and executable without introducing context pollution?

### SOLUTION: Layered Coherence Architecture (7 Strategies)

Three-mechanism minimal workflow: (1) Schema-based prevention with constraint injection, (2) Structured persistent memory via BATCH_COHERENCE.md in PostgreSQL Blackboard, (3) Independent external verification with max 3 iterative cycles.

**Key Decisions** (for future alignment):
| Decision | Choice | Implication |
|----------|--------|-------------|
| Verification timing | Prevention FIRST (instant schema), Detection SECOND (batch-end) | Reduces 52% of verification workload |
| Verifier criteria | Coherence ≥0.9, Completeness ≥0.8, Executability ≥0.85 | Multi-dimensional rubric with thresholds |
| Context persistence | BATCH_COHERENCE.md + 4 PostgreSQL tables | Enables rollback and cross-batch coherence |
| Escalation protocol | Tester/Coder → Judge → Architect re-enrichment (max 3 iterations) | Clear ownership and limits |
| Context management | Observation masking WITHIN batch, summarization BETWEEN batches | Hybrid approach for different scopes |

**Dependencies**:

- **Unblocks**: Sub-Plan Verifier prompt design, Architect Stage 2 workflow, full pipeline implementation
- **Constrains**: OQ-6 (must integrate with Verifier patterns), OQ-10 (Verifier criteria now defined), OQ-14 (must support context re-injection)

**Full Specification**: `research/2026-01-20-sub-plan-creation-workflow-coherence/internal-solution.md`
```
