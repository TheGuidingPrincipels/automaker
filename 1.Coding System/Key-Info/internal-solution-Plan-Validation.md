# Solution: Plan Decomposition Process & Architect Workflow (OQ-4c)

## Metadata

- **Generated:** 2026-01-20
- **Session:** /Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-20-plan-decomposition-architect-workflow
- **Process.md:** /Users/ruben/.claude/profiles/Solution-Finder/ACE/Process.md
- **Question:** How should the Architect divide master plans into sub-plans, and can one agent handle the full workload?

---

## Executive Summary

**Direct Answer:** The Architect should use a **two-stage decomposition workflow** (Stage 1: rough division into 5-15 milestones, Stage 2: enrichment into dual outputs) with **verification checkpoints** between stages. **YES**, a single Architect agent can handle 20-30 documents, but **ONLY** with mandatory guardrails: staged processing, multi-signal context monitoring with adaptive batching (default 5, range 3-7), three-tier Scout integration, and deterministic Orchestrator control flow.

**Confidence Level:** HIGH (85%) based on convergent evidence from 28+ sources across technical research, production systems (Cursor, GitHub Copilot, Augment, Google ADK), and cutting-edge 2024-2025 frameworks.

**Key Recommendation:** Implement the "Staged Hierarchical Decomposition Architecture" with 6 strategies:

1. Two-Stage Decomposition (rough → enrich)
2. Verification Checkpoints (after Stage 1 + every batch)
3. Multi-Signal Context Monitoring with Adaptive Batching
4. Three-Tier Scout Integration (upfront + tools + escape hatch)
5. Single Architect with Deterministic Orchestrator
6. Passive Experience Logging for v2 Milestone Library

---

## Resolution Criteria Mapping

How this solution addresses each resolution criterion from Process.md:

| #    | Resolution Criterion                                    | How Addressed                                                                                                                                                                        | Evidence                                                                |
| ---- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| RC1  | Decomposition algorithm/methodology                     | **S1**: Two-stage (Stage 1: 5-15 milestones with title, objective, scope, dependencies; Stage 2: dual outputs per milestone in batches)                                              | AgentOrchestra, PlanGEN, HiPlan, Cursor, GitHub Copilot [21+ sources]   |
| RC2  | Architect architecture (single vs assistants vs staged) | **S5/S7**: Single Architect with staged processing + deterministic Orchestrator (SDK) handling all control flow                                                                      | 95% production consensus; LangChain, Anthropic, Google ADK patterns     |
| RC3  | Dependency graph construction                           | Stage 1 outputs include dependency mapping between milestones; execution order derived from DAG                                                                                      | Hierarchical planning patterns [Brave]                                  |
| RC4  | Context preservation strategy                           | **S3**: Multi-signal monitoring (resource >80%, quality drop >15%, edit loops >3, entropy collapse) with PostgreSQL Blackboard persistence (compressed summaries, never raw history) | Anthropic context engineering, Cursor internals, ACE Framework          |
| RC5  | Scout integration timing                                | **S4**: Three-tier (Tier 1: upfront before Stage 1; Tier 2: tool-based retrieval during Stage 2; Tier 3: exception-based escape hatch with checkpoint rollback)                      | Cursor, Google ADK, FAIR-RAG, SagaLLM [100% consensus on upfront value] |
| RC6  | Quality gates and re-decomposition triggers             | **S2**: Sub-Plan Verifier validates after Stage 1 (coverage, overlap, complexity) AND after every batch in Stage 2 (consistency, drift, constraints)                                 | PDCA framework (1-74% improvement), PlanGEN                             |
| RC7  | Maximum sub-plan count guidelines                       | 5-15 target validated; >15 sub-plans with high domain complexity triggers consideration of multi-Architect hierarchy                                                                 | Cognitive load research [all sources]                                   |
| RC8  | Decomposition examples                                  | Deferred to Process.md blueprint phase (patterns provided; ACE-specific examples to be created during implementation)                                                                | N/A                                                                     |
| RC9  | Single-pass vs staged workflow                          | **S1**: Staged WINS decisively (15-40% improvement over single-pass); single-pass explicitly rejected                                                                                | PlanGEN, SCOPE (56% vs 24%), PDCA validation                            |
| RC10 | Alignment validation during enrichment                  | **S2**: Verification checkpoints validate both Stage 1 structure AND Stage 2 enrichment batches; completion analysis per PDCA                                                        | InfoQ PDCA, Completion analysis checkpoints                             |
| RC11 | Research responsibility                                 | **S4**: Scout runs before Architect (Orchestrator triggers); Architect has tool-based access during Stage 2 but does NOT explicitly "call Scout"                                     | Research-before-planning universal [100% consensus]                     |

**Criteria Coverage:** 10/11 criteria fully addressed (RC8 deferred to implementation)

---

## Synthesized Solution

**Core Approach:**
The recommended approach is a **Staged Hierarchical Decomposition Architecture** where a single Architect agent operates in two distinct passes, coordinated by a deterministic SDK-based Orchestrator. In Stage 1, the Architect receives the master plan plus Scout findings and produces 5-15 milestone descriptions (rough sub-plan boundaries with titles, objectives, scope estimates, and dependency mappings). In Stage 2, the Architect enriches each milestone into dual outputs (Feature Spec for Tester, Implementation Plan for Coder), processing sub-plans in batches of 5 (adjustable to 3-7 based on complexity) with context resets between batches. This approach is grounded in convergent evidence from academic research (AgentOrchestra, HiPlan, PlanGEN) and production systems (Cursor, GitHub Copilot, Augment) showing 15-40% improvement over single-pass planning.

**Implementation Strategy:**
Implementation proceeds in phases. First, establish Scout-before-Architect sequencing: the Orchestrator triggers Scout (Initial) to conduct comprehensive codebase analysis, then passes compressed Scout findings to Architect. This prevents hallucinated architectures and aligns with universal industry practice. Second, implement the two-stage Architect workflow with explicit verification: Sub-Plan Verifier reviews Stage 1 output for coverage, overlap, and complexity balance before Stage 2 begins. Third, add multi-signal context monitoring: track resource utilization (>80%), quality degradation (>15% drop), behavioral signals (edit loops >3), and entropy collapse to trigger adaptive context resets. Fourth, implement three-tier Scout integration: Tier 1 provides the foundation (upfront), Tier 2 gives Architect search/read tools during enrichment (Production pattern), and Tier 3 offers fail-fast recovery for emergent complexity with checkpoint rollback.

**Integration Considerations:**
The strategies form a layered architecture where Scout provides the foundation, two-stage decomposition enables the algorithm, context management enables scale, and verification ensures quality. The SDK-based Orchestrator handles ALL deterministic work (routing, batching, validation triggers, state management, error paths) while CLI-based Architect and Verifier agents handle ONLY reasoning tasks (decomposition, enrichment, quality assessment). This separation, validated by 95% of production systems, provides debuggability, cost control, and operational reliability. The PostgreSQL Blackboard serves as the shared memory substrate with three core tables: architect_state (session-level constraints), architect_checkpoints (versioned snapshots for rollback), and context_bulletpoints (incremental delta updates).

**Trade-offs & Alternatives:**
The primary trade-off is implementation complexity: two-stage workflows with context resets require more infrastructure than naive single-pass approaches. However, all research perspectives agree that single-pass will fail at the 20-30 document scale. Alternative architectures considered include: (a) Multi-Architect hierarchy with Lead Architect doing decomposition and specialized Architects doing enrichment per domain—adds coordination overhead, recommended only for >15 sub-plans with high domain complexity; (b) Milestone Library for experience reuse—validated in research but cold-start problem makes it premature for v1, so implemented as passive logging only. The recommended single-Architect-with-guardrails approach balances capability against complexity for the typical 5-15 sub-plan range.

---

## Evidence & Confidence

### Source Agreement Analysis

| Claim                                             | Exa                  | Brave                     | Bright Data          | Investigation      | Consensus |
| ------------------------------------------------- | -------------------- | ------------------------- | -------------------- | ------------------ | --------- |
| Staged decomposition outperforms single-pass      | ✅ 15-40%            | ✅ PDCA                   | ✅ SCOPE 56% vs 24%  | —                  | **100%**  |
| Single-pass single-agent will fail at 20-30 docs  | ✅ Context rot       | ✅ MentorCruise           | ✅ (with guardrails) | —                  | **100%**  |
| Research-before-planning is mandatory             | ✅                   | ✅ Universal              | ✅                   | ✅ All tiers agree | **100%**  |
| Batch size should be 3-7 range                    | ✅ Adaptive          | ✅ Fixed 5                | ✅ Hybrid            | ✅ Validated       | **100%**  |
| Multi-signal context monitoring                   | ✅                   | ✅ Cursor                 | ✅ ACE Framework     | ✅ 6 signal types  | **100%**  |
| Workflow handles control, agents handle reasoning | —                    | —                         | —                    | ✅ 95% production  | **95%**   |
| Milestone Library viable for v1                   | ⚠️ Research positive | ⚠️ Production doesn't use | ⚠️ Cold-start        | ❌ Defer to v2     | **DEFER** |

### Confidence Factors

**Strengthening factors:**

- 28+ unique sources across L4-L5 authority levels
- Production validation from Cursor internals, LangGraph docs, Anthropic/Google ADK engineering blogs
- 95% industry consensus on workflow-agent separation pattern
- Multiple independent research streams converging on same patterns
- Deep-dive investigation validated context reset and Scout timing recommendations

**Weakening factors:**

- Exact batch size thresholds (3 vs 5 vs 7) extrapolated, need ACE-specific tuning
- Context collapse detection tuned for GPT-4.1/Claude 4, not Opus 4.5 specifically
- RC8 (decomposition examples) deferred—patterns clear but ACE-specific instances TBD
- Milestone Library ROI assumptions based on projections, not measured data

---

## Appendix A: Strategy Reference

**Strategy Set Name:** Staged Hierarchical Decomposition Architecture
**Strategies:** 6 total (5 HIGH confidence + 1 with caveats)

### Included Strategies

| #   | Strategy                                               | Confidence | Score | Role                  |
| --- | ------------------------------------------------------ | ---------- | ----- | --------------------- |
| S1  | Two-Stage Decomposition (Rough then Enrich)            | HIGH       | 9.3   | Core algorithm        |
| S2  | Verification Checkpoints Between Stages                | HIGH       | 9.1   | Quality control       |
| S3  | Multi-Signal Context Monitoring + Adaptive Batching    | HIGH       | 8.5   | Scale enabler         |
| S4  | Three-Tier Scout Integration                           | HIGH       | 9.2   | Context foundation    |
| S7  | Single Architect with Deterministic Orchestrator       | HIGH       | 8.0   | Architecture decision |
| S6  | Passive Experience Logging (v2 Milestone Library prep) | CAVEATS    | 6.6   | Future optimization   |

### Implementation Roadmap

| Phase | Strategy                            | Dependencies        | Notes                                         |
| ----- | ----------------------------------- | ------------------- | --------------------------------------------- |
| 1     | S4: Three-Tier Scout Integration    | None                | Foundation—establishes research-first pattern |
| 2     | S1: Two-Stage Decomposition         | Requires S4         | Core algorithm—rough then enrich              |
| 2     | S3: Multi-Signal Context Monitoring | Requires S4         | Parallel—enables scale                        |
| 2     | S2: Verification Checkpoints        | Requires S4         | Parallel—quality control                      |
| 3     | S7: Single Architect + Orchestrator | Requires S1, S2, S3 | Architecture—validated by prior strategies    |
| 4     | S6: Passive Experience Logging      | Requires S2         | Optional v1—only verified plans logged        |

### Strategy Relationships

```
S4 (Three-Tier Scout) ─────┐
                           ├──> S1 (Two-Stage Decomp) ──> S7 (Architect + Orchestrator)
S3 (Context Monitoring) ───┘                                     ^
                                                                 |
S2 (Verification) ────────────────────────── COMPLEMENTARY ──────┘
                                                                 |
S6 (Experience Logging) ────────────────────── DEFERRED ─────────┘
```

### Excluded Strategies

| #         | Strategy                    | Reason                                                                                   |
| --------- | --------------------------- | ---------------------------------------------------------------------------------------- |
| (none)    | Multi-Architect Hierarchy   | Reserve for >15 sub-plans with high domain complexity; not needed for typical 5-15 range |
| S6 (full) | Milestone Library Retrieval | Deferred to v2; cold-start problem, -97% ROI for v1                                      |

### Key Trade-offs Accepted

- **Implementation complexity** for reliability: Two-stage with context resets requires more infrastructure than single-pass, but single-pass will fail at scale
- **Orchestrator overhead** for debuggability: SDK-based workflow control adds code but enables deterministic testing and cost control
- **Conservative batch default** for safety: Starting with fixed 5 before enabling full adaptive logic reduces risk during initial deployment
- **Passive logging** over full library: Defer Milestone Library retrieval to v2, but capture data from day one for future activation

---

## Appendix B: Research Session

### Research Files

- Exa findings: `exa-findings.md`
- Brave findings: `brave-findings.md`
- Brightdata findings: `brightdata-findings.md`
- Synthesis: `synthesis.md`

### Intervention Files

- Technical investigation: `interventions/q1-context-scout-technical.md`
- Production investigation: `interventions/q1-context-scout-production.md`
- Emerging investigation: `interventions/q1-context-scout-emerging.md`
- Workflow boundaries: `interventions/q1-workflow-boundaries.md`
- Intervention synthesis: `interventions/q1-synthesis.md`

### Strategy Investigation Files

- S6 investigation: `strategy-investigations/strategy-6-investigation.md`

### Consensus Points from Research

- Staged decomposition outperforms single-pass by 15-40%
- Research-before-planning is mandatory (prevents hallucinated architectures)
- Verification checkpoints are critical (1-74% improvement per PDCA)
- 5-15 sub-plan target is appropriate for single Architect
- Context management (resets, compaction) is essential for scale
- Single-pass single-agent will fail at 20-30 document scale
- 95% of production systems use workflow-agent separation pattern

### Conflicts Identified

**Key Tension RESOLVED:** Sources initially appeared to disagree on single-Architect capacity:

- Exa/Brave emphasized RISK (will fail without guardrails)
- Bright Data emphasized SOLUTION (feasible with staged processing)
- Resolution: Same underlying truth—single Architect works ONLY with mandatory guardrails

**Scout Timing RESOLVED:** Three-tier integration synthesized from:

- Technical: Strict upfront (clean separation)
- Production: Hybrid with tools (Cursor, Google ADK pattern)
- Emerging: Reactive augmentation (ProAgent, SagaLLM)
- Resolution: All three tiers serve different needs; combine them

---

## Appendix C: Context

### Original Question

How should the Architect divide master plans into sub-plans, and can one agent handle the full workload?

### Goal Context (from Process.md)

ACE (Autonomous Coding Ecosystem) is a highly automated software development factory that transforms high-level master plans into production-ready code. The Architect agent must decompose master plans into 5-15 sequenced sub-plans, producing dual outputs (Feature Spec + Implementation Plan) per sub-plan. Key constraints: token budget ~30k per spec, complexity limits ≤5 files/≤10 functions/≤300 LOC per sub-plan.

### User Context (gathered during triage)

- **System constraints**: Single Architect agent, PostgreSQL Blackboard, CLI-based execution
- **Team expertise**: Building from scratch, v1 development
- **Priority**: Quality over speed (user stated preference)

---

## Appendix D: Intervention History

| #   | Question                                                                                  | Mode                   | Result                                                        |
| --- | ----------------------------------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------- |
| 1   | Context Management & Workflow Design (Context Reset + Scout Timing + Workflow Boundaries) | DEEP-DIVE (3+1 agents) | Validated S3, refined S4, confirmed workflow-agent separation |

**Key Findings from Intervention:**

- Multi-signal context monitoring validated (6 signal types)
- Three-tier Scout integration synthesized (upfront + tools + escape hatch)
- 95% production consensus on workflow-agent separation
- PostgreSQL Blackboard schema defined (3 tables)
- Hybrid adaptive batch sizing validated (default 5, range 3-7)

---

## Appendix E: Blueprint Additions

### Architect Workflow Definition

```
STAGE 1: Rough Decomposition
├── Trigger: Orchestrator passes master plan + Scout (Initial) findings
├── Input: Master plan (~1,500 lines max) + Scout findings (~500-1k lines compressed)
├── Output: 5-15 milestone descriptions with:
│   ├── Title (identifier)
│   ├── Core objective (1-2 sentences)
│   ├── Estimated scope (files, functions, LOC estimate)
│   ├── Dependencies on other milestones
│   └── Execution order constraints
├── Token budget: ~10k
└── Verification: Sub-Plan Verifier reviews for coverage, overlap, complexity balance

STAGE 2: Enrichment (Batched)
├── Trigger: Sub-Plan Verifier approves Stage 1 output
├── Process: Batches of 5 milestones (adaptive 3-7)
│   ├── For each milestone: Generate Feature Spec + Implementation Plan
│   ├── After each batch: Context reset (multi-signal triggered)
│   ├── Persist: Key decisions, constraints, cross-cutting concerns → Blackboard
│   └── Reload: Milestone stubs + Blackboard + next batch
├── Token budget: ~30k per sub-plan (dual outputs)
└── Verification: Sub-Plan Verifier reviews every batch
```

### Three-Tier Scout Integration

```
TIER 1: Pre-Planning Research (ALWAYS)
├── Scout analyzes master plan + codebase
├── Comprehensive upfront context gathering
├── Findings compressed and stored in Blackboard
└── Trigger: Before Stage 1 (Architect milestone generation)

TIER 2: Tool-Based Retrieval (ON-DEMAND)
├── Architect has search/read tools during Stage 2
├── Tools backed by Scout capabilities (abstraction)
├── Autonomous retrieval when gaps discovered
└── Trigger: Architect detects uncertainty during enrichment

TIER 3: Exception-Based Escape Hatch (RARE)
├── Explicit fail-fast when critical context missed
├── Spawn targeted Scout run with narrow query
├── Rollback to last checkpoint, inject findings, resume
└── Trigger: Emergent complexity, cascading dependencies
```

### Context Reset Protocol

```
MULTI-SIGNAL MONITORING:
├── Resource: Context window utilization >80%
├── Quality: Performance degradation >15% from baseline
├── Behavioral: Edit loop iterations >3 on same issue
├── Structural: Batch completion (every 5 sub-plans default)
├── Entropy: Context collapse (Δtokens <-90% AND Δaccuracy <-10%)
└── Cost: Token/latency spike (time-to-first-token growth >50%)

ON RESET:
├── Clear agent context
├── Persist to Blackboard:
│   ├── Approved constraints and architectural decisions
│   ├── Cross-cutting concerns (error handling, naming conventions)
│   ├── Dependency graph updates
│   └── Batch summaries (compressed)
├── NEVER persist:
│   ├── Raw conversation history
│   ├── Intermediate reasoning chains
│   ├── Rejected alternatives
│   └── Verbose tool outputs
└── Reload for next batch:
    ├── Original milestone stubs (minimal)
    ├── Blackboard decisions and constraints
    └── Next batch of milestones for enrichment
```

### PostgreSQL Blackboard Schema

```sql
-- Core state table
CREATE TABLE architect_state (
    session_id UUID PRIMARY KEY,
    thread_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    master_plan_summary TEXT NOT NULL,
    architecture_constraints JSONB NOT NULL,
    cross_cutting_concerns TEXT[],
    current_batch_number INT DEFAULT 0,
    milestones_completed JSONB,
    scout_findings_summary TEXT,
    context_window_usage_pct DECIMAL,
    quality_baseline FLOAT
);

-- Checkpoint table for rollback
CREATE TABLE architect_checkpoints (
    checkpoint_id UUID PRIMARY KEY,
    session_id UUID REFERENCES architect_state(session_id),
    batch_number INT NOT NULL,
    checkpoint_type VARCHAR(20),
    snapshot JSONB NOT NULL,
    quality_metrics JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    parent_checkpoint_id UUID
);

-- Experience logging for v2 Milestone Library
CREATE TABLE experience_log (
    log_id UUID PRIMARY KEY,
    session_id UUID REFERENCES architect_state(session_id),
    task_summary TEXT NOT NULL,
    task_embedding VECTOR(1536),
    plan_summary JSONB NOT NULL,
    verification_result VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Orchestrator Separation (Workflow vs Agent)

```
SDK-BASED ORCHESTRATOR (Deterministic):
├── File routing ({session}/stage1/, {session}/stage2/batch_{n}/)
├── Validation triggers (after Stage 1, every batch)
├── Batch grouping (chunks of 5 milestones, adaptive 3-7)
├── Context resets (clear agent context between batches)
├── State persistence (Blackboard writes)
├── Sequential flow control (Stage 1 → Gate → Stage 2 → Loops)
├── Error handling (retry transient failures, escalate verification failures)
└── Token budget tracking

CLI-BASED AGENTS (Reasoning):
├── Architect: Master plan decomposition, milestone enrichment
├── Verifier: Quality assessment, gap detection, drift monitoring
└── Scout: Codebase research (via Tier 1/2/3 integration)
```

---

## Decision Summary

| Decision                            | Resolution                                                                                                                      | Confidence  |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| Single Architect vs Multi-Architect | Single Architect with staged processing (typical case); Multi-Architect hierarchy for >15 sub-plans with high domain complexity | HIGH        |
| Single-pass vs Staged               | Staged (two-stage with verification)                                                                                            | HIGH        |
| Scout timing                        | Three-tier integration (upfront + tools + escape hatch)                                                                         | HIGH        |
| Context reset triggers              | Multi-signal monitoring (6 signal types)                                                                                        | HIGH        |
| Batch size                          | Hybrid adaptive: default 5, range 3-7 based on complexity                                                                       | MEDIUM-HIGH |
| Orchestrator design                 | SDK handles workflow, CLI agents handle reasoning                                                                               | HIGH        |
| Milestone Library                   | Defer retrieval to v2; passive logging in v1 for data collection                                                                | MEDIUM-HIGH |

---

## Next Steps

To validate and finalize this solution:

```bash
# Switch to Solution-Validator profile
solv

# Run validation
/validate-solution "/Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-20-plan-decomposition-architect-workflow/internal-solution.md"
```

If you have an external solution to compare:

```bash
/validate-solution "/Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-20-plan-decomposition-architect-workflow/internal-solution.md" "/path/to/external-solution.md"
```
