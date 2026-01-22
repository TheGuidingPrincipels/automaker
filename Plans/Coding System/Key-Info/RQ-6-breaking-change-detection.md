# Solution: Breaking-Change Detection and Escalation for Autonomous Agents

## Metadata

- **Generated:** 2026-01-21
- **Session:** /Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-21-breaking-change-detection
- **Process.md:** /Users/ruben/.claude/profiles/Solution-Finder/ACE/Process.md
- **Question:** How do agents detect and escalate potential breaking changes before implementation?
- **Confidence:** HIGH (85%)

---

## Executive Summary

**Direct Answer:** Agents detect breaking changes through a four-layer detection pipeline—AST-based static analysis, rule-based severity classification, API contract testing, and downstream impact analysis—with escalation thresholds that guarantee human approval for all critical changes. CRITICAL severity changes (API deletions, database schema modifications, external integration changes) automatically trigger <60% confidence and block execution until human approval. The system integrates with ACE's existing Sub-Plan Verifier as a mandatory pre-execution gate and feeds detection signals into Judge's ASI drift monitoring with 2x weighting.

**Confidence Level:** HIGH (85%) based on 3-source consensus across academic research (ICSE 2022, INRIA), industry production systems (AWS, Yelp, Microsoft), and alignment with ACE's existing three-tier escalation architecture.

**Key Recommendation:** Implement a Layered Breaking-Change Detection Architecture (LBCDA) with 9 strategies across 4 implementation phases. The detection pipeline runs in Sub-Plan Verifier before execution, with rule-based severity classification routing changes to appropriate escalation levels. Human notification uses structured payloads with approve/reject mechanisms, simplified by scheduling execution during human availability windows (6:45-21:00) to avoid complex timeout logic.

---

## Resolution Criteria Mapping

| #   | Resolution Criterion                         | How Addressed                                                                                                                                                                                                                                                                                       | Evidence                                                            |
| --- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| RC1 | Define "potential breaking change"           | **Strategy S7 (BC Taxonomy)** defines 7 categories: API Deletion (CRITICAL), Signature Change (HIGH), Contract Violation (HIGH), Schema Modification (CRITICAL), External Integration (CRITICAL), Behavioral Change (MEDIUM), Deprecation (LOW)                                                     | [Exa+Brave+Bright Data] 3-source consensus on categories            |
| RC2 | Define detection mechanism                   | **Four-layer pipeline**: S5 (AST Analysis) → S1 (Rule-Based Classification) → S2 (Contract Testing) → S9 (Impact Analysis). Static catches 60-70%, contract testing catches interface violations, impact analysis informs escalation                                                                | [Exa: BreakBot, TypeScript BC detector] [Brave: Pact, openapi-diff] |
| RC3 | Define escalation trigger thresholds         | **Strategy S3** maps BC severity to ACE's existing thresholds: CRITICAL → <60% (Human), HIGH → 60-89% (Orchestrator), MEDIUM → 60-89% (Orchestrator), LOW → ≥90% (Agent). Automatic human escalation for: API deletions, DB schema changes, external integration mods, >5 downstream files affected | [All sources] Universal agreement on human approval for high-risk   |
| RC4 | Define human notification mechanism          | **Strategy S6** specifies structured notification payload with: escalation_level, confidence_score, breaking_changes[], context (boundary, assumptions), resume_mechanism (approve/reject URLs). Channels: Slack + Dashboard (simplified—no PagerDuty needed due to daytime execution)              | [Exa: BreakBot PR comments] [Brave: AWS pipeline patterns]          |
| RC5 | Define execution resume after human response | **Strategy S6** defines resume flow: APPROVE → release block, Judge monitors with ELEVATED_ATTENTION; REJECT → return to Architect for revision; No timeout complexity needed (execution during 6:45-21:00 human availability)                                                                      | [Exa+Brave] Production patterns                                     |
| RC6 | Success indicator: no BC without approval    | **Blackboard constraint** (`execution_blocked_until_decision`) prevents query from returning blocked rows. Audit trail in `breaking_change_reports` table. 100% compliance target for CRITICAL/HIGH severity                                                                                        | [Architecture design] Database-enforced safety                      |

**Criteria Coverage:** 6/6 fully addressed

---

## Synthesized Solution

### Core Approach

Breaking-change detection for autonomous agents requires moving beyond simple "test pass/fail" to proactive structural analysis that identifies potential impacts before code execution. The research consensus across academic (ICSE 2022, INRIA), industry (AWS, Yelp, Microsoft), and emerging sources is clear: static analysis catches 60-70% of breaking changes deterministically, while runtime validation through graduated testing catches edge cases that static analysis misses. For ACE's daytime autonomous operation, this means establishing detection gates that err on the side of caution—any change touching public APIs, database schemas, or external integrations (as enumerated in the master plan system prompt) should automatically escalate to human review rather than risk production breakage.

### Implementation Strategy

The architecture integrates detection at three points in ACE's existing workflow. First, the Coder agent's output passes through AST-based static analysis (Strategy S5) that identifies structural changes—deleted exports, modified signatures, type changes—using tools appropriate to the language (TypeScript BC detector, japicmp for Java, mypy for Python). Second, these changes are evaluated against rule-based severity classification (Strategy S1) inspired by Yelp's swagger-spec-compatibility, where rules like "REQ-E001: Added Required Property" map directly to specific escalation levels. Third, the Sub-Plan Verifier runs contract tests (Strategy S2) comparing generated code against OpenAPI/interface specifications from the master plan's integration inventory, catching interface violations that AST diff alone might miss.

### Integration with ACE Architecture

The detection system connects to ACE's existing components through several touchpoints. The PostgreSQL blackboard stores breaking-change reports in a new `breaking_change_reports` table with fields for BC type, severity, confidence score, affected files, downstream impact count, and human decision. The Judge's ASI monitoring incorporates BC detection as a weighted drift signal—breaking changes receive 2x penalty in drift calculation, ensuring they surface prominently. The Three-Tier Boundaries from master plans (Always/Ask/Never) map to BC handling: "Never" actions trigger immediate escalation if BC detected, "Ask First" boundaries apply to medium-severity changes, and "Always" safe operations proceed only if no breaking changes detected. Database schema changes (Strategy S10) receive specialized handling with expand-contract pattern enforcement.

### Simplification: Daytime Execution Model

A key architectural simplification emerged from user context: by scheduling plan execution during human availability windows (6:45-21:00), the system eliminates complex timeout logic entirely. If an escalation occurs at 20:30 and the human doesn't respond before ending their day, execution naturally pauses until morning. This removes the need for AUTO_REJECT vs EMERGENCY_ESCALATION decisions, PagerDuty integration, and complex timeout state machines. The notification system simplifies to Slack + Dashboard, with escalations queued for morning review if they occur late in the day.

### Trade-offs Accepted

This architecture prioritizes determinism and debuggability over semantic sophistication. The primary trade-off is accepting that rule-based detection will miss some behavioral changes that preserve signatures but alter semantics—these are caught by the graduated testing already defined in RQ-3b rather than pre-commit gates. Emerging approaches (SemGuard real-time semantic supervision, Code Property Graphs) offer deeper semantic understanding but remain experimental with limited production evidence. The recommendation is to start with the proven rule-based stack and evaluate emerging approaches at the 6-month mark when ACE has accumulated execution data.

---

## Evidence & Confidence

### Source Agreement Analysis

| Claim                                        | Exa | Brave | Bright Data | Consensus |
| -------------------------------------------- | --- | ----- | ----------- | --------- |
| Multi-layered detection essential            | ✅  | ✅    | ✅          | HIGH      |
| Rule-based severity classification works     | ✅  | ✅    | ✅          | HIGH      |
| API/Contract testing is industry standard    | ✅  | ✅    | ✅          | HIGH      |
| Human approval required for CRITICAL changes | ✅  | ✅    | ✅          | HIGH      |
| Static analysis catches 60-70% of BCs        | ✅  | ✅    | —           | HIGH      |
| AST-based detection is foundational          | ✅  | ✅    | ✅          | HIGH      |
| ML-based detection requires training data    | —   | ✅    | ✅          | MEDIUM    |

### Confidence Factors

**Strengthening factors:**

- 3-source consensus on core architecture (detection pipeline, severity classification, escalation mapping)
- Production evidence from major companies (AWS, Yelp, Microsoft, Discover Financial)
- Direct alignment with ACE's existing three-tier escalation thresholds (90%/60%)
- User-provided context simplifies architecture (daytime execution, integration inventory in master plan)

**Weakening factors:**

- Behavioral changes with same signature may slip through static analysis (mitigated by graduated testing)
- Rule-based detection requires maintenance as codebase evolves
- No ACE-specific production data yet to validate thresholds

---

## Appendix A: Strategy Reference

**Strategy Set Name:** Layered Breaking-Change Detection Architecture (LBCDA)

**Strategies:** 9 included (7 HIGH, 2 MEDIUM) + 1 deferred + 4 skipped

### Included Strategies

| #   | Strategy                              | Confidence | Score | Role                                    |
| --- | ------------------------------------- | ---------- | ----- | --------------------------------------- |
| S1  | Rule-Based BC Severity Classification | HIGH       | 8.8   | Classification layer                    |
| S2  | API/Contract Testing (Pact/OpenAPI)   | HIGH       | 8.8   | Detection layer                         |
| S3  | Three-Tier Escalation Mapping         | HIGH       | 8.7   | Routing layer                           |
| S4  | Multi-Stage Detection Pipeline        | HIGH       | 8.5   | Orchestration                           |
| S5  | AST-Based Static Analysis             | HIGH       | 8.5   | Foundation layer                        |
| S6  | Human Notification + Resume Mechanism | HIGH       | 8.3   | Execution layer                         |
| S7  | Breaking Change Taxonomy              | HIGH       | 8.3   | Definition layer                        |
| S9  | Downstream Impact Analysis            | MEDIUM     | 7.5   | Enhancement (user has integration data) |
| S10 | Database Migration Safety Gates       | MEDIUM     | 7.5   | Enhancement (ACE modifies DB schemas)   |

### Implementation Roadmap

| Phase              | Strategy                   | Dependencies | Notes                                  |
| ------------------ | -------------------------- | ------------ | -------------------------------------- |
| 1 - Foundation     | S5 (AST Analysis)          | None         | Week 1-2; language-specific tooling    |
| 1 - Foundation     | S2 (Contract Testing)      | None         | Week 1-2; OpenAPI/Pact setup           |
| 1 - Foundation     | S7 (BC Taxonomy)           | None         | Week 1-2; define 7 categories          |
| 2 - Classification | S1 (Rule-Based Severity)   | Phase 1      | Week 3-4; implement Yelp-style rules   |
| 2 - Classification | S10 (DB Migration Safety)  | Phase 1      | Week 3-4; expand-contract rules        |
| 3 - Routing        | S3 (Escalation Mapping)    | Phase 2      | Week 5; map severity → confidence      |
| 3 - Routing        | S4 (Detection Pipeline)    | Phase 2      | Week 5-6; orchestrate layers           |
| 3 - Routing        | S9 (Impact Analysis)       | Phase 2      | Week 5-6; use master plan integrations |
| 4 - Execution      | S6 (Notification + Resume) | Phase 3      | Week 7-8; Slack + Dashboard            |
| 5 - Enhancement    | S11 (Feature Flags)        | Phase 4      | Month 3+; when infrastructure ready    |

### Strategy Relationships

| From                    | To                      | Type          | Notes                                       |
| ----------------------- | ----------------------- | ------------- | ------------------------------------------- |
| S5 (AST Analysis)       | S1 (Rule-Based BC)      | LAYERED       | AST diff provides input for rule evaluation |
| S2 (Contract Testing)   | S1 (Rule-Based BC)      | LAYERED       | Contract violations inform severity         |
| S7 (BC Taxonomy)        | S1 (Rule-Based BC)      | LAYERED       | Taxonomy defines what rules detect          |
| S1 (Rule-Based BC)      | S3 (Escalation Mapping) | LAYERED       | Severity determines escalation level        |
| S4 (Detection Pipeline) | S6 (Human Notification) | LAYERED       | Pipeline triggers notification              |
| S9 (Downstream Impact)  | S3 (Escalation Mapping) | COMPLEMENTARY | Impact informs escalation decision          |
| S10 (DB Migration)      | S1 (Rule-Based BC)      | COMPLEMENTARY | Specialized rules for DB changes            |

### Deferred Strategies

| #   | Strategy                   | Reason                       | Timeline           |
| --- | -------------------------- | ---------------------------- | ------------------ |
| S11 | Feature Flags for Rollback | Requires flag infrastructure | Phase 5 (Month 3+) |

### Excluded Strategies

| #   | Strategy                     | Reason                                          |
| --- | ---------------------------- | ----------------------------------------------- |
| S8  | Graduated Testing            | Already decided in RQ-3b                        |
| S12 | Zero-Tolerance Bug Loops     | Covered by RQ-2 (3-iteration fix cycle)         |
| S13 | SemGuard Real-Time Semantic  | Experimental (ASE 2025), no production evidence |
| S14 | Code Property Graph Analysis | High computational cost, unproven at scale      |
| S15 | Semantic Mutation Testing    | Academic stage, expensive                       |
| S16 | ML-Based BC Prediction       | Requires 6+ months training data                |

---

## Appendix B: Breaking Change Taxonomy

| Category             | Severity | Default Escalation    | Examples                                            |
| -------------------- | -------- | --------------------- | --------------------------------------------------- |
| API Deletion         | CRITICAL | Human (<60%)          | Endpoint removed, public method deleted             |
| Schema Modification  | CRITICAL | Human (<60%)          | DB column dropped, type changed, constraint added   |
| External Integration | CRITICAL | Human (<60%)          | Third-party API modified, auth changes              |
| Signature Change     | HIGH     | Orchestrator (60-89%) | Parameter added/removed, return type changed        |
| Contract Violation   | HIGH     | Orchestrator (60-89%) | Required field added to request, enum value removed |
| Access Modifier      | HIGH     | Orchestrator (60-89%) | Public to private, protected to private             |
| Behavioral Change    | MEDIUM   | Orchestrator (60-89%) | Logic altered with same signature                   |
| Deprecation          | LOW      | Agent (≥90%)          | @Deprecated annotation added                        |

### Automatic Human Escalation Triggers

These always force <60% confidence regardless of other factors:

- Any API endpoint deletion
- Database schema non-additive changes
- External integration modifications (per master plan inventory)
- > 5 downstream files affected
- Security/authentication changes
- Changes to "Never" boundary categories (from Three-Tier Boundaries)

---

## Appendix C: Technical Specifications

### Detection Pipeline Flow

```
Coder Agent Output
        │
        ▼
┌───────────────────────────────────────┐
│ Layer 1: AST-Based Static Analysis    │
│ • Parse code changes into AST         │
│ • Compare declarations (exports,      │
│   types, signatures)                  │
│ • Identify structural modifications   │
│ • Tools: TS BC detector, japicmp      │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│ Layer 2: Rule-Based Pattern Matching  │
│ • Apply severity rules to Layer 1     │
│ • Classify by BC category             │
│ • Check DB migration patterns         │
│ • Tools: Yelp-style rule engine       │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│ Layer 3: Contract Verification        │
│ • Compare against OpenAPI specs       │
│ • Validate against integration        │
│   inventory from master plan          │
│ • Tools: Pact, openapi-diff, Spectral │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│ Layer 4: Downstream Impact Analysis   │
│ • Analyze affected files/services     │
│ • Calculate blast radius              │
│ • Inform escalation decision          │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│ Escalation Decision                   │
│ • Map severity → confidence threshold │
│ • Route to Agent/Orchestrator/Human   │
│ • Block if CRITICAL or <60%           │
└───────────────────────────────────────┘
```

### Blackboard Schema

```sql
CREATE TABLE breaking_change_reports (
    id SERIAL PRIMARY KEY,
    sub_plan_id INTEGER REFERENCES sub_plans(id),
    bc_type VARCHAR(50),           -- API_DELETION, SIGNATURE_CHANGE, etc.
    severity VARCHAR(20),          -- CRITICAL, HIGH, MEDIUM, LOW
    confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    affected_files TEXT[],
    downstream_impact_count INTEGER,
    rule_triggered VARCHAR(50),    -- MIS-E001, REQ-E001, etc.
    detection_layer INTEGER,       -- 1-4 (which layer detected)
    detection_timestamp TIMESTAMP DEFAULT NOW(),
    escalation_level VARCHAR(20),  -- AGENT, ORCHESTRATOR, HUMAN
    notification_sent_at TIMESTAMP,
    notification_channel VARCHAR(20), -- SLACK, DASHBOARD
    human_decision VARCHAR(20),    -- APPROVED, REJECTED, null (pending)
    human_decision_timestamp TIMESTAMP,
    human_notes TEXT,
    resume_with_elevated_attention BOOLEAN DEFAULT TRUE
);

-- Index for efficient queries
CREATE INDEX idx_bc_pending ON breaking_change_reports
    (sub_plan_id) WHERE human_decision IS NULL AND escalation_level = 'HUMAN';
```

### Human Notification Payload

```json
{
  "escalation_level": "HUMAN",
  "confidence": 0.45,
  "sub_plan_id": "SP-12345",
  "detection_timestamp": "2026-01-21T14:30:00Z",
  "breaking_changes": [
    {
      "type": "API_DELETION",
      "severity": "CRITICAL",
      "location": "src/api/user_service.py:deleteUser()",
      "rule_triggered": "MIS-E001",
      "downstream_impact": {
        "affected_files": 12,
        "affected_services": ["frontend-app", "mobile-app"]
      },
      "recommendation": "Consider deprecation path before removal"
    }
  ],
  "context": {
    "master_plan_boundary": "ASK_FIRST",
    "related_assumptions": ["User deletion API exists"],
    "integration_inventory_match": "users-service"
  },
  "actions": {
    "approve_url": "https://ace.internal/plans/12345/approve",
    "reject_url": "https://ace.internal/plans/12345/reject"
  }
}
```

### Resume Flow

```
Human receives Slack/Dashboard notification
                │
                ▼
Human reviews breaking changes + context
                │
        ┌───────┴───────┐
        │               │
        ▼               ▼
    APPROVE         REJECT
        │               │
        ▼               ▼
Decision recorded   Sub-plan marked
in blackboard       FAILED, returns
        │           to Architect
        ▼
Orchestrator releases block
        │
        ▼
Judge monitors with ELEVATED_ATTENTION
(lower drift thresholds for this sub-plan)
```

---

## Appendix D: Integration with Existing ACE Components

### Sub-Plan Verifier (RQ-3a)

BC detection is a **mandatory check** in Sub-Plan Verifier before execution begins. The Verifier:

1. Runs the four-layer detection pipeline
2. Records results in `breaking_change_reports` table
3. If CRITICAL/HIGH severity detected → blocks execution, triggers notification
4. If MEDIUM/LOW → logs and proceeds (or Orchestrator review for MEDIUM)

### Judge ASI Monitoring (RQ-3b)

Breaking change detection feeds into Judge's Assumption Stability Index with **2x weighting**:

- BC detected in sub-plan → ASI penalty doubled
- Accumulated BCs across sub-plans trigger re-planning consideration
- ELEVATED_ATTENTION flag after human-approved BC → lower drift thresholds

### Three-Tier Boundaries (RQ-4a)

Master plan boundaries map to BC handling:

- **"Never" actions**: If BC touches these → immediate Human escalation
- **"Ask First" actions**: MEDIUM severity BCs → Orchestrator review
- **"Always" actions**: Only proceed if no BC detected

### Drift Markers (RQ-4b)

BC detection results populate Implementation Plan drift markers:

- **Downstream**: Affected files/services from impact analysis
- **Impact**: Severity classification and blast radius

### Execution Window

Plans auto-start in morning (e.g., 07:00) to ensure execution during human availability (6:45-21:00). If escalation occurs late in day, execution naturally pauses until morning response.

---

## Appendix E: Research Session

### Research Files

- Exa findings: `research/2026-01-21-breaking-change-detection/exa-findings.md`
- Brave findings: `research/2026-01-21-breaking-change-detection/brave-findings.md`
- Brightdata findings: `research/2026-01-21-breaking-change-detection/brightdata-findings.md`
- Synthesis: `research/2026-01-21-breaking-change-detection/synthesis.md`

### Key Sources

**Academic/Technical (Exa):**

- BreakBot (ICSE 2022) - GitHub bot with AST analysis, per-client impact reports
- INRIA ChangeDistiller (ICSM 2013) - AST pattern-based detection framework
- TypeScript Breaking Change Detector - 5 BC categories via structural analysis

**Production/Industry (Brave):**

- AWS Builders Library - Code review as last manual gate
- Yelp swagger-spec-compatibility - 8 detection rules with severity
- Pact contract testing - 60-70% integration test reduction

**Emerging (Bright Data):**

- SemGuard (ASE 2025) - Real-time semantic supervision (experimental)
- Code Property Graphs - Deep behavioral analysis (high cost)

### Consensus Points

- Multi-layered detection essential (static catches 60-70%, runtime catches rest)
- Rule-based severity classification maps to escalation tiers
- Human approval required for CRITICAL/HIGH severity changes
- API/Contract testing is industry standard

---

## Appendix F: User Context

### System Constraints

- Execution during human availability: 6:45-21:00 local time
- Plans auto-start in morning to complete during day
- No complex timeout logic needed (natural pause overnight)

### Integration Inventory

- External dependencies provided in master plan system prompt
- Detection can reference explicit dependency list
- No dynamic discovery required

### Database Work

- ACE will modify database schemas
- S10 (Database Migration Safety Gates) included
- Expand-contract pattern enforcement

---

## Next Steps

To validate and finalize this solution:

```bash
# Switch to Solution-Validator profile
solv

# Run validation
/validate-solution "/Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-21-breaking-change-detection/internal-solution.md"
```

---

## Blueprint Addition for Process.md

When this solution is accepted, add to Process.md:

```markdown
## RQ-6: Breaking-Change Detection ✓

**Resolved**: 2026-01-21 | **Confidence**: 85%

**Question**: How do agents detect and escalate potential breaking changes before implementation?

### SOLUTION: Layered Breaking-Change Detection Architecture (LBCDA)

Four-layer detection pipeline (AST analysis → Rule-based severity → Contract testing → Impact analysis) integrated with Sub-Plan Verifier as mandatory pre-execution gate. CRITICAL severity changes (API deletions, DB schema mods, external integration changes) automatically trigger <60% confidence and human escalation. Simplified by daytime execution model (6:45-21:00) eliminating complex timeout logic.

**Key Decisions** (for future alignment):
| Decision | Choice | Implication |
|----------|--------|-------------|
| Detection approach | Four-layer pipeline (AST → Rules → Contracts → Impact) | Sub-Plan Verifier runs all layers before execution |
| Severity classification | 7 categories: CRITICAL/HIGH/MEDIUM/LOW | Maps directly to 90%/60% escalation thresholds |
| Human escalation triggers | API deletion, DB schema, external integration, >5 files | Always <60% regardless of other factors |
| Execution timing | Daytime only (6:45-21:00) | No timeout complexity; natural pause overnight |
| Integration inventory | Provided in master plan system prompt | Detection references explicit dependency list |

**Strategy Set**: 9 strategies (S1-S7 + S9 + S10)

**Dependencies**:

- **Integrates with**: Sub-Plan Verifier (RQ-3a), Judge ASI (RQ-3b), Three-Tier Boundaries (RQ-4a), Drift Markers (RQ-4b)
- **Unblocks**: Execution safety, overnight autonomous operation capability

**Full Specification**: `research/2026-01-21-breaking-change-detection/internal-solution.md`
```
