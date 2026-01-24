# Solution: Pre-Implementation Architecture for ACE

## Metadata

- **Generated:** 2026-01-19
- **Session:** /Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-19-pre-implementation-architecture
- **Process.md:** /Users/ruben/.claude/profiles/Solution-Finder/ACE/Process.md
- **Question:** What happens BEFORE the Tester starts in a TDD-first multi-agent coding system? How should codebase exploration and plan output work?

---

## Executive Summary

**Direct Answer:** The pre-implementation phase requires a **Three-Mode Scout Architecture** separate from the Architect, with the Architect producing **two distinct outputs** (Feature Specification for Testing Agent, Implementation Plan for Coding Agent), followed by a **mandatory Sub-Plan Verification step** before execution. Codebase exploration happens in three modes: (1) Initial Scout before Architect for context gathering, (2) On-demand Scout during planning for targeted queries, and (3) Per-iteration Scout during Coder execution for dynamic discovery. Sub-plans must be sized to fit within **70% of 220k token contexts** (~154k per agent) using **hybrid format** (typed code skeletons + natural language).

**Confidence Level:** HIGH (85%) based on strong source consensus across 38 L3-L5 sources from technical research, production systems (Devin, Cursor), and emerging patterns.

**Key Recommendation:** Implement the complete architecture as specified, with dual-stage verification (offline policy synthesis + online runtime monitoring), 4-dimension severity classification, and ASK/REFUSE/UNKNOWN escalation contracts.

---

## Resolution Criteria Mapping

How this solution addresses each resolution criterion from Process.md (OQ-3a):

| #   | Resolution Criterion                                                | How Addressed                                                                                                                                                           | Evidence                                                                        |
| --- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| RC1 | Must decide: Scout timing (A/B/C/D) with rationale                  | **HYBRID: (A) Initial Scout BEFORE Architect + (D) Per-iteration Scout during Coder**. Option C (Integrated) rejected due to cognitive overload.                        | MSARL research (L5), Devin production pattern, Cursor Dynamic Context Discovery |
| RC2 | Must decide: Skeleton generation (A/B/C) with rationale             | **CONTEXT-DEPENDENT: (B) Skeleton per sub-plan for well-defined tasks, (C) No skeleton for complex/architectural tasks**. Option A rejected as too rigid.               | Blueprint2Code 96.3% HumanEval vs HumanLayer/TDFlow 88-94% for complex tasks    |
| RC3 | Must define: Complete Tester input specification                    | **Feature Specification Schema** (30k tokens): Acceptance criteria, test boundaries, safety specs, executable test templates. Tester isolated from implementation code. | TDFlow 94.3% success with human-written specs                                   |
| RC4 | Must define: Architect output specification                         | **Two outputs**: Feature Specification (for Tester + Coder) + Implementation Plan (for Coder only). Hybrid format with typed skeletons + natural language.              | Production systems, CodeAgents ablation study                                   |
| RC5 | Success indicator: Clear handoff from Architect → [Scout?] → Tester | **Full flow defined**: Master Plan → Initial Scout → Architect → Sub-Plan Verifier → Tester + Coder → Verifier → Judge                                                  | All 3 research perspectives converge                                            |

**Criteria Coverage:** 5/5 criteria fully addressed

---

## Synthesized Solution

**Core Approach:**
The recommended architecture separates codebase exploration from task decomposition to prevent cognitive overload. Initial Scout runs BEFORE Architect with read-only tools (F1-optimized file selection), producing 5-15 curated files with relevance justifications. The Architect then focuses solely on decomposing the 500-1500 line Master Plan into 5-15 sequenced sub-plans, each containing a Feature Specification (for Testing Agent) and an Implementation Plan (for Coding Agent). This separation is validated by MSARL research showing that "single-agent paradigms that interleave long-horizon reasoning with tool operations lead to cognitive-load interference" and by Devin's production architecture using a specialized planning-mode subagent.

**Implementation Strategy:**
Each sub-plan must fit within the 70% token budget (~154k tokens) for both Testing Agent and Coding Agent independently. Token allocation follows: 30k for specifications (Feature Spec or Implementation Plan), 40-90k for working memory, and 24-34k safety buffer. Complexity is capped at ≤5 files, ≤10 functions, ≤300 LOC per sub-plan—beyond these limits, success rates drop below 45% and the task should be decomposed further. The hybrid format (typed code skeletons + natural language annotations) achieves 55-87% token reduction compared to pure natural language while constraining hallucination.

**Integration Considerations:**
A mandatory Sub-Plan Verification step (external agent, NOT Architect self-review) validates completeness before Testing/Coding Agents execute. Research demonstrates that self-verification causes "significant performance collapse" while external verification yields performance gains. The Verifier checks: (1) Feature Spec completeness for Tester, (2) Implementation Plan traceability to acceptance criteria, (3) Complexity within hard limits, (4) Safety specifications translated. Production data shows 46% of AI agent POCs fail without a verification gate.

**Trade-offs & Alternatives:**
The main trade-off is efficiency vs. quality. Three-mode Scout adds coordination overhead but prevents the 40-80% uncoordinated failure rate documented in pure multi-agent systems. The alternative of Integrated Scout-Architect (original S2) was rejected based on production evidence of Architect cognitive overload with large inputs. For skeleton generation, the context-dependent approach (skeletons for well-defined tasks, specs-only for complex tasks) balances the Blueprint2Code pattern (96.3% HumanEval for single-function problems) with HumanLayer evidence (specs-only works better for repository-scale changes).

---

## Answers to Sub-Questions

| Sub-Question                                | Answer                                                                                                                                                                                                                                                     | Confidence |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| 1. When should codebase exploration happen? | **THREE MODES**: (1) Initial Scout BEFORE Architect for context gathering (F1-optimized), (2) On-demand Scout during planning for targeted queries (optional), (3) Per-iteration Scout during Coder execution for dynamic discovery.                       | HIGH       |
| 2. Should Architect output code structure?  | **CONTEXT-DEPENDENT**: For well-defined, single-function sub-plans: YES, output interface skeletons with typed signatures. For repository-scale or architectural sub-plans: NO, output specifications only. Hybrid format (skeletons + NL) for all.        | HIGH       |
| 3. What exactly should Tester receive?      | **Feature Specification** (30k tokens): Acceptance criteria (Given-When-Then), test boundaries (in-scope/out-scope), safety specifications, executable test templates, non-functional requirements. **NEVER** implementation code or algorithmic approach. | HIGH       |

---

## Evidence & Confidence

### Source Agreement Analysis

| Claim                            | Exa            | Brave            | Bright Data             | Consensus |
| -------------------------------- | -------------- | ---------------- | ----------------------- | --------- |
| Separate Scout from Architect    | ✓ (MSARL)      | ✓ (Devin)        | ✓ (Google)              | STRONG    |
| Sub-Plan Verification mandatory  | ✓ (VeriMAP)    | ✓ (46% failure)  | ✓ (Generator-Critic)    | STRONG    |
| Per-iteration Scout during Coder | ✓ (TDFlow)     | ✓ (Devin Search) | ✓ (Cursor)              | STRONG    |
| Hybrid format optimal            | ✓ (CodeAgents) | ✓ (Industry std) | ✓ (56% time reduction)  | STRONG    |
| 70% context budget               | ✓ (Technical)  | ✓ (Production)   | ✓ (Emerging)            | STRONG    |
| ≤5 files, ≤300 LOC limits        | ✓ (ablation)   | ✓ (30-40k tasks) | ✓ (45% threshold)       | STRONG    |
| External verification required   | ✓              | ✓ (Ralph Loop)   | ✓ (self-critique fails) | STRONG    |

### Confidence Factors

**Strengthening factors:**

- Zero significant disagreements across 3 research perspectives
- Production validation from Devin, Cursor, GitHub Copilot
- Quantitative metrics: 94.3% TDFlow success, 46.9% token reduction, 45% capability threshold (p<0.001)
- Recent research (2025-2026) with peer-reviewed sources (ACL, ICLR, ICML)

**Weakening factors:**

- No direct validation of ACE-specific architecture (patterns adapted from related systems)
- Severity thresholds (LOW <2.0, MEDIUM <3.5, HIGH ≥3.5) not empirically validated for autonomous coding agents specifically
- Token budget split (30k+30k) based on Technical perspective alone (others support concept but not exact numbers)

---

## Complete Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    MASTER PLAN (500-1500 lines)                         │
│         Contains: WHAT to build (no WHERE - no codebase access)        │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    MODE 1: INITIAL SCOUT                                │
│  • Read-only tools: read_file, grep, codebase_search                   │
│  • F1-optimized file selection (0.790 F1 vs 0.697 baseline)            │
│  • Output: 5-15 curated files with relevance justifications            │
│  • Prevents context pollution for Architect                             │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        ARCHITECT                                        │
│  • Focus: Decomposition ONLY (no exploration)                          │
│  • Input: Master Plan + Scout's curated context                        │
│  • Output: 5-15 sequenced sub-plans                                    │
│  • Can invoke MODE 2: On-Demand Scout for targeted queries             │
├─────────────────────────────────────────────────────────────────────────┤
│  OUTPUTS PER SUB-PLAN:                                                  │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐      │
│  │ FEATURE SPECIFICATION       │  │ IMPLEMENTATION PLAN         │      │
│  │ (30k tokens)                │  │ (30k tokens)                │      │
│  │ → Testing Agent + Coder     │  │ → Coding Agent ONLY         │      │
│  │ • Acceptance criteria       │  │ • File manifest             │      │
│  │ • Test boundaries           │  │ • Function skeletons        │      │
│  │ • Safety specifications     │  │ • Algorithm approach        │      │
│  │ • Executable test templates │  │ • Verification checkpoints  │      │
│  └─────────────────────────────┘  └─────────────────────────────┘      │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    SUB-PLAN VERIFIER (MANDATORY)                        │
│  • Separate agent (NOT Architect self-review)                          │
│  • Generator-Critic pattern                                            │
│  • Validates:                                                           │
│    ✓ Feature Spec completeness for Tester                              │
│    ✓ Implementation Plan traceability                                  │
│    ✓ Complexity within limits (≤5 files, ≤300 LOC)                     │
│    ✓ Safety specifications translated                                  │
│  • Feedback loop if issues found                                        │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
          ┌─────────────────────┴─────────────────────┐
          │                                           │
          ▼                                           ▼
┌─────────────────────────┐             ┌─────────────────────────┐
│    TESTING AGENT        │             │    CODING AGENT         │
│  (220k tokens, 70%)     │             │  (220k tokens, 70%)     │
│                         │             │                         │
│  INPUT:                 │             │  INPUT:                 │
│  • Feature Spec (30k)   │             │  • Implementation Plan  │
│                         │             │  • Code files (40k)     │
│  WORKING: 90k           │             │  • Test assertions (10k)│
│  BUFFER: 34k            │             │  WORKING: 50k           │
│                         │             │  BUFFER: 24k            │
│  OUTPUT:                │             │                         │
│  • Test suite           │             │  MODE 3: Per-Iteration  │
│                         │             │  Scout for uncertainty  │
│  ISOLATED from impl     │             │                         │
└───────────────────────┬─┘             │  OUTPUT:                │
                        │               │  • Implementation code  │
                        │               └───────────┬─────────────┘
                        │                           │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           VERIFIER                                      │
│  • Runs tests against implementation                                    │
│  • Runtime monitoring (loop detection, token consumption)              │
│  • 5 failure modes: Transient, Deterministic, Planning Gap,            │
│                     State Loss, Hallucinated Success                   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            JUDGE                                        │
│  • Severity Classification (4 dimensions):                              │
│    Impact × Reversibility × Detectability × Blast Radius               │
│  • Thresholds:                                                          │
│    LOW (<2.0): Auto-approve                                            │
│    MEDIUM (2.0-3.5): Request self-correction (max 2 iterations)        │
│    HIGH (≥3.5): ESCALATE TO HUMAN                                      │
│  • ASK/REFUSE/UNKNOWN escalation contract                              │
│  • Decision: ACCEPT | REQUEST_FIX | ESCALATE                           │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
              ACCEPT                  FIX (max 3)
                    │                       │
                    ▼                       │
        Next Sub-Plan ◄─────────────────────┘
```

---

## Appendix A: Strategy Reference

**Strategy Set Name:** ACE Pre-Implementation Architecture v1.0
**Strategies:** 17 total (10 HIGH, 7 MEDIUM)

### Included Strategies

| #   | Strategy                               | Confidence | Score | Role                                           |
| --- | -------------------------------------- | ---------- | ----- | ---------------------------------------------- |
| S8  | Isolated specifications to Tester      | HIGH       | 9.8   | Core isolation mechanism                       |
| NEW | Sub-Plan Verification (External)       | HIGH       | 9.2   | Mandatory quality gate                         |
| NEW | Separate Scout from Architect          | HIGH       | 9.0   | Prevents cognitive overload                    |
| NEW | Hybrid Format (Skeletons + NL)         | HIGH       | 9.0   | Token efficiency                               |
| S3  | Per-iteration Scout for Coder          | HIGH       | 8.8   | Dynamic context discovery                      |
| NEW | Three-Mode Scout Architecture          | HIGH       | 8.8   | Exploration flexibility                        |
| NEW | Dual-Stage Verification                | HIGH       | 8.8   | Offline + Online monitoring                    |
| NEW | ASK/REFUSE/UNKNOWN Escalation          | HIGH       | 8.7   | Clear behavioral contracts                     |
| S5  | Specification-only (complex)           | HIGH       | 8.5   | For architectural sub-plans                    |
| NEW | 4-Dimension Severity Classification    | HIGH       | 8.5   | Impact/Reversibility/Detectability/BlastRadius |
| NEW | Complexity Limits (≤5 files, ≤300 LOC) | MEDIUM     | 8.5   | Hard caps for agent success                    |
| S10 | Parallel test/code generation          | MEDIUM     | 8.3   | Within sub-plan efficiency                     |
| NEW | Token Budget (30k+30k specs)           | MEDIUM     | 8.0   | Context allocation                             |
| S1  | Sequential Scout (alternative)         | MEDIUM     | 8.8   | For unfamiliar codebases                       |
| S9  | Three-artifact enriched handoff        | MEDIUM     | 7.6   | Adds execution context                         |
| S6  | Skeleton for well-defined sub-plans    | MEDIUM     | 7.5   | Context-dependent                              |
| NEW | 45% Capability Threshold               | MEDIUM     | 7.5   | Decomposition trigger                          |

### Implementation Roadmap

| Phase | Strategy                      | Dependencies | Notes                                           |
| ----- | ----------------------------- | ------------ | ----------------------------------------------- |
| 1     | Three-Mode Scout Architecture | None         | Foundation - Scout runs before Architect        |
| 1     | Separate Scout from Architect | None         | Foundation - Architect focuses on decomposition |
| 2     | Hybrid Format                 | Phase 1      | Architect produces typed skeletons + NL         |
| 2     | Token Budget Allocation       | Phase 1      | 30k Feature Spec + 30k Implementation Plan      |
| 2     | Complexity Limits             | Phase 1      | ≤5 files, ≤10 functions, ≤300 LOC               |
| 3     | Sub-Plan Verification         | Phase 2      | External Verifier validates completeness        |
| 3     | Isolated specifications       | Phase 2      | Tester receives Feature Spec only               |
| 4     | Dual-Stage Verification       | Phase 3      | Offline + Online monitoring                     |
| 4     | 4-Dimension Severity          | Phase 3      | Classification framework                        |
| 4     | ASK/REFUSE/UNKNOWN            | Phase 3      | Escalation contracts                            |
| 5     | Per-iteration Scout (S3)      | Phase 4      | Dynamic discovery during Coder                  |
| 5     | Parallel test/code (S10)      | Phase 4      | Efficiency within sub-plan                      |

### Strategy Relationships

- Three-Mode Scout → Separate Scout from Architect: LAYERED (Scout provides context for Architect)
- Separate Scout → Hybrid Format: LAYERED (Scout context enables skeleton design)
- Hybrid Format → Token Budget: COMPLEMENTARY (format enables budget compliance)
- Token Budget → Complexity Limits: COMPLEMENTARY (both constrain sub-plan scope)
- Sub-Plan Verification → Isolated specs: LAYERED (verification enables safe isolation)
- Dual-Stage → Severity Classification: LAYERED (monitoring feeds classification)
- Severity → ASK/REFUSE/UNKNOWN: LAYERED (classification triggers escalation)

### Excluded Strategies

| #   | Strategy                          | Reason                                                   |
| --- | --------------------------------- | -------------------------------------------------------- |
| S2  | Integrated Scout-Architect        | REPLACED by Separate Scout (cognitive overload evidence) |
| S4  | Parallel Dynamic Scouts           | DEFERRED (single source, limited replication)            |
| S7  | Full skeleton upfront             | DEFERRED (may over-constrain Coder)                      |
| S11 | Run log for decision preservation | DEFERRED (novel pattern, unproven at scale)              |
| -   | Self-verification by Architect    | REJECTED (causes performance collapse)                   |

### Key Trade-offs Accepted

- **Coordination overhead for quality**: Three-mode Scout adds complexity but prevents 40-80% uncoordinated failure rate
- **Verification latency for reliability**: Sub-Plan Verifier adds 1-2 min per sub-plan but prevents 46% POC failure rate
- **Context-dependent skeletons**: No one-size-fits-all; requires per-sub-plan complexity assessment
- **70% context budget**: Leaves 30% unused for safety buffer (conservative but reliable)

---

## Appendix B: Research Session

### Research Files

- Exa findings: `exa-findings.md`
- Brave findings: `brave-findings.md`
- Brightdata findings: `brightdata-findings.md`
- Original synthesis: `synthesis.md`

### Intervention Files

- Q1 Investigation (Architect Overload): `interventions/q1-synthesis.md`
- Q2 Investigation (Sub-Plan Schema): `interventions/q2-synthesis.md`
- Intervention Log: `interventions/intervention-log.json`

### Consensus Points from Research

1. Codebase exploration precedes implementation [Exa+Brave+Bright Data]
2. Tester must be isolated from implementation code [Exa+Brave+Bright Data]
3. Structured artifact handoffs over conversations [Exa+Brave+Bright Data]
4. Interface contracts enable test writing [Exa+Brave+Bright Data]
5. Context engineering beats context maximization [All perspectives]
6. External verification required (self-critique fails) [Production+Emerging]
7. 70% context budget with active management [All perspectives]
8. Complexity limits prevent degradation [All perspectives]

### Conflicts Resolved

| Conflict                                            | Resolution                                                       |
| --------------------------------------------------- | ---------------------------------------------------------------- |
| Skeleton generation (production=no vs emerging=yes) | Context-dependent: specs for complex, skeletons for well-defined |
| Scout independence (separate vs integrated)         | Separate - cognitive overload evidence decisive                  |
| Parallel vs sequential test/code                    | Sequential sub-plans, but parallel WITHIN each sub-plan          |
| Exploration timing (upfront vs dynamic)             | Both: upfront for planning, dynamic for execution                |

---

## Appendix C: Context

### Original Question

What happens BEFORE the Tester starts in a TDD-first multi-agent coding system? How should codebase exploration and plan output work? Specifically:

1. Scout Agent Timing: When should codebase exploration happen?
2. Code Skeleton Generation: Should Architect output code structure?
3. Information Flow to Tester: What exactly should Tester receive?

### Goal Context (from Process.md)

ACE (Autonomous Coding Ecosystem) is a highly automated software development factory that transforms high-level master plans into production-ready code. The system operates through a four-layer pipeline (Plan Creation → Coding Execution → Verification & Quality → Merge & Synthesis) with minimal human intervention.

Core Design Goal: Developer defines WHAT (features, behavior, constraints) → Agent system decides HOW (implementation path) → Output must be production-ready.

Key Constraints:

- Testing Agent: 220k token context window, 70% budget (~154k)
- Coding Agent: 220k token context window, 70% budget (~154k)
- Independent context windows (no shared memory during execution)
- Master Plan created OUTSIDE codebase (no WHERE, only WHAT)
- TDD-first: Tests written BEFORE implementation
- Tester isolated from implementation code

### User Context (gathered during triage)

**System Constraints:** Large master plans (500-1500 lines), agents have independent 220k token context windows with 70% working budget
**Team Expertise:** Building automated coding system with Claude-based agents
**Priority:** Production-ready, scalable code with 100% success rates

---

## Appendix D: Intervention History

| #   | Question                                                               | Mode      | Result                                                     |
| --- | ---------------------------------------------------------------------- | --------- | ---------------------------------------------------------- |
| 1   | Should exploration be integrated into Architect or delegated to Scout? | deep-dive | Separate Scout validated; Sub-Plan Verification mandatory  |
| 2   | How to structure sub-plans for 220k/70% token budget?                  | deep-dive | Complete schemas, token allocation, verification framework |

---

## Appendix E: Complete Schemas

### Feature Specification Schema (Testing Agent Input)

See: `interventions/q2-synthesis.md` - Section "Feature Specification Schema"

Key sections:

- Task Suitability Assessment
- Functional Requirements (Given-When-Then)
- Non-Functional Requirements (Performance, Security, Compliance)
- Safety Specifications (STPA-Derived Hazards)
- Test Boundaries (In-Scope/Out-Scope)
- Executable Test Templates
- Context Management instructions

### Implementation Plan Schema (Coding Agent Input)

See: `interventions/q2-synthesis.md` - Section "Implementation Plan Schema"

Key sections:

- Goal and Success Criteria
- Architecture Overview with Component Diagram
- File Manifest (Create/Modify/Delete)
- Complexity Estimate
- Phase-based Implementation Approach
- Function Skeletons with Types
- Test Assertions to Satisfy
- Verification Strategy (Offline + Online)
- Rollback Plan

---

## Appendix F: Verification Framework

### Dual-Stage Verification

**Stage 1 (Offline - Before Execution):**

- Validate Feature Spec against Master Plan
- Validate Implementation Plan against Feature Spec
- Check complexity limits (≤5 files, ≤300 LOC)
- Verify safety specifications translated

**Stage 2 (Online - During Execution):**

- Monitor token consumption (circuit breaker at 90%)
- Checkpoint every 30k tokens
- Detect loops (No-Delta, Tool Thrashing, Budget Slope)
- Classify failures into 5 modes

### 5 Failure Mode Taxonomy

| Mode                 | Detection               | Handling           | Max Attempts |
| -------------------- | ----------------------- | ------------------ | ------------ |
| Transient            | Error 429, 503, timeout | Retry with backoff | 3            |
| Deterministic        | Same error 2+ times     | Structured repair  | 1            |
| Planning Gap         | Prerequisite missing    | Re-plan (escalate) | 1            |
| State Loss           | Re-asks answered Q      | Checkpoint/reload  | 1            |
| Hallucinated Success | External verify fails   | Fix cycle          | 3            |

### 4-Dimension Severity Classification

**Formula:** `0.30×Impact + 0.25×Reversibility + 0.20×Detectability + 0.25×BlastRadius`

**Thresholds:**

- LOW (<2.0): Auto-approve with logging
- MEDIUM (2.0-3.5): Request self-correction (max 2 iterations)
- HIGH (≥3.5): Escalate to human

### ASK/REFUSE/UNKNOWN Contract

| Type    | When                           | Agent Behavior                       |
| ------- | ------------------------------ | ------------------------------------ |
| ASK     | Missing info user can provide  | Stop, formulate specific question    |
| REFUSE  | Request violates policy/safety | Immediately reject, explain why      |
| UNKNOWN | Outside scope or capability    | Return unknown, suggest alternatives |

---

## Next Steps

To validate and finalize this solution:

```bash
# Switch to Solution-Validator profile
solv

# Run validation
/validate-solution "/Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-19-pre-implementation-architecture/internal-solution.md"
```

If you have an external solution to compare:

```bash
/validate-solution "/Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-19-pre-implementation-architecture/internal-solution.md" "/path/to/external-solution.md"
```

---

## Summary: Key Decisions Made

| Decision Point          | Choice                                           | Rationale                                                       |
| ----------------------- | ------------------------------------------------ | --------------------------------------------------------------- |
| Scout timing            | Three-Mode (Initial + On-demand + Per-iteration) | Prevents Architect cognitive overload; production-validated     |
| Skeleton generation     | Context-dependent (well-defined=yes, complex=no) | Balances Blueprint2Code (96.3%) vs HumanLayer (88-94%) evidence |
| Architect outputs       | Feature Spec + Implementation Plan (separate)    | Enables Tester isolation; hybrid format reduces tokens          |
| Sub-Plan Verification   | Mandatory, external agent                        | 46% POC failure without it; self-critique causes collapse       |
| Token budget            | 30k specs + 50-90k working + 24-34k buffer       | Empirically validated across perspectives                       |
| Complexity limits       | ≤5 files, ≤10 functions, ≤300 LOC                | Success drops below 45% beyond these                            |
| Verification approach   | Dual-stage (offline + online)                    | VeriGuard pattern provides formal guarantees                    |
| Severity classification | 4-dimension weighted scoring                     | Production-derived thresholds with clear escalation             |
| Escalation contract     | ASK/REFUSE/UNKNOWN                               | Prevents infinite loops and undefined behavior                  |

**This solution resolves OQ-3a and provides the foundation for OQ-3b (Validation & Drift Detection).**
