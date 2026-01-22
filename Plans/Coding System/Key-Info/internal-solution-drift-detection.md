# Solution: Validation and Drift Detection in ACE (OQ-3b)

## Metadata

- **Generated:** 2026-01-19
- **Session:** /Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-19-validation-drift-detection/
- **Process.md:** /Users/ruben/.claude/profiles/Solution-Finder/ACE/Process.md
- **Question:** How do we catch problems DURING and AFTER implementation? Who validates drift and when?

---

## Executive Summary

**Direct Answer:** Implement a layered drift detection architecture where **Judge agents own all drift detection** (tracking ASI metrics and validating semantically), while Coder agents focus purely on code implementation. Use a **three-tier escalation model** (Agent ≥90% confidence → Orchestrator with web research 60-89% → Human <60%). Run integration tests every 2 sub-plans on critical paths to prevent the 10%→40% cascade amplification. Trigger re-planning when ASI drops below 0.60 for 2 consecutive windows or when contract tests reveal assumption invalidation.

**Confidence Level:** HIGH (85%) based on strong source consensus across 3 research perspectives (Exa, Brave, Bright Data) with production evidence from Microsoft, Anthropic, IBM, Uber, Netflix, and Google.

**Key Recommendation:** Start with ASI-based continuous monitoring (S1) as the foundation—this enables all other strategies by providing the drift signals they need to act on. Judge owns drift detection to enable clean separation of concerns (maker-checker pattern).

---

## Resolution Criteria Mapping

How this solution addresses each resolution criterion from Process.md:

| #   | Resolution Criterion                  | How Addressed                                                                                                                                                 | Evidence                                                                                           |
| --- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| RC1 | Drift validation owner (A/B/C/D)      | **Option B (Judge)** — Judge owns all drift detection; Orchestrator runs programmatic FSM checks                                                              | Microsoft maker-checker pattern (L5), Anthropic external tracing (L5), IBM process validation (L5) |
| RC2 | Integration timing with rationale     | **Graduated**: Unit every SP, Integration every 2 SP, Regression every 3-5, E2E end only                                                                      | Google test pyramid (L4), Uber cascade data showing 40-60% amplification after 2 steps (L5)        |
| RC3 | Re-planning trigger conditions        | **Multi-condition**: ASI <0.60 for 2 windows, contract test failure, 2+ consecutive integration failures, circuit breaker opening                             | Agent Drift paper (L5) with quantified thresholds, RQ-3a severity classification integration       |
| RC4 | How Coder flags drift violations      | **Coder does NOT flag** — Judge detects drift from outputs; Coder may incidentally note violations during implementation but is not responsible for detection | Investigation Q2: Separation of concerns, cognitive load reduction                                 |
| RC5 | Drift detection before cascade damage | **Yes** — ASI detects drift at median 73 interactions, integration tests every 2 SP catch assumption breaks before 40% cascade                                | ArXiv 2601.04170 (L5), Uber production data (L5)                                                   |

**Criteria Coverage:** 5/5 criteria fully addressed

---

## Synthesized Solution

**Core Approach:**

The research converges on a hybrid validation architecture that distributes drift detection responsibility with clear accountability. The key insight from our investigations is that **Judge should own all drift detection** (departing from the original synthesis recommendation of Coder flags + Judge validates). This follows the production-proven maker-checker pattern from Microsoft, Anthropic, and financial services, where implementers focus solely on execution while separate validators handle quality monitoring.

Judge agents track the 12-dimensional Agent Stability Index (ASI) over rolling 50-interaction windows. When ASI drops below 0.75 for three consecutive windows, Judge validates the drift semantically using ground truth comparison, token-level hallucination detection, and system state verification. This prevents false positives where ASI fluctuations don't represent actual drift. Coder agents are freed from monitoring responsibilities, reducing cognitive load from 5 concurrent concerns to 3, and eliminating conflict of interest where an agent might rationalize its own drift.

**Implementation Strategy:**

The implementation proceeds in four phases following LAYERED relationships between strategies:

- **Phase 1 (Foundation)**: S1 (ASI Monitoring) + S4 (Graduated Testing) — Establish the metrics infrastructure and testing pyramid
- **Phase 2 (Detection)**: S6 (Statistical Drift Detection) + S5 (Contract Testing) — Add trend detection and assumption validation at sub-plan boundaries
- **Phase 3 (Response)**: S2 (Judge Detection) + S7 (Circuit Breakers) — Judge validates and detects drift; breakers contain cascade failures
- **Phase 4 (Recovery)**: S8 (Re-Planning Triggers) + S11 (Adaptive Behavioral Anchoring) — Enable graduated response and drift mitigation

**Integration Considerations:**

The strategies integrate through a shared ASI metrics infrastructure. The ASI score feeds into multiple consumers: Judge uses it for drift detection, Orchestrator uses it for FSM conformance state, circuit breakers use it for threshold monitoring, and Adaptive Behavioral Anchoring uses it to modulate exemplar injection strength. Contract testing (S5) validates assumptions at sub-plan boundaries—if SP-1 produces session-based auth but SP-4 expects JWT, the contract test fails immediately rather than at SP-4 execution.

**Trade-offs & Alternatives:**

The primary trade-off is computational overhead. Combined mitigation strategies add approximately 23% overhead, but this is offset by the 80-85% drift reduction (S8+S11+S5 combined) and prevention of cascade rework that would otherwise cost 40-60% more effort. We excluded FSM-Based Conformance (S3) due to 8/10 complexity with marginal value over S5+S8+S11, and recent research showing LLMs struggle with long FSM execution (50% accuracy degradation).

---

## Answers to Sub-Questions

| Sub-Question                           | Answer                                                                                                                                                                                                                                                                        | Confidence |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| **1. Drift Validation Responsibility** | **Option B (Judge owns all)**: Judge tracks ASI metrics and validates semantically. Coder focuses purely on implementation. Orchestrator runs FSM conformance and makes re-planning decisions.                                                                                | HIGH       |
| **2. Integration Pulse Timing**        | **Graduated**: Unit tests every sub-plan (<5s); Integration tests every 2 sub-plans (<60s); Regression every 3-5 sub-plans (<300s); E2E at end only.                                                                                                                          | HIGH       |
| **3. Re-Planning Triggers**            | **Multi-condition**: ASI <0.60 for 2 windows → block and re-plan; ASI <0.75 for 3 windows → Judge review; Contract test failure → re-plan dependent sub-plans; 2+ integration failures → halt, Architect re-evaluates; Circuit breaker opens → contain, isolated re-planning. | HIGH       |

---

## Three-Tier Escalation Model

Based on investigation findings, implement this confidence-based escalation:

| Tier             | Confidence Range  | Handler                        | Actions                                                                                    |
| ---------------- | ----------------- | ------------------------------ | ------------------------------------------------------------------------------------------ |
| **Agent**        | ≥90% (ASI ≥ 0.90) | Agent autonomously             | Execute without escalation                                                                 |
| **Orchestrator** | 60-89%            | Orchestrator with web research | Web search (Exa/Brave), knowledge base queries, specialized sub-agents, retry-with-context |
| **Human**        | <60%              | Human review                   | Full context package for resume-not-restart                                                |

**Confidence Calculation:**

- Model uncertainty: 40%
- Validation score: 30%
- Historical success rate: 20%
- Tool execution success: 10%

**Production Evidence:** UiPath, Galileo (100+ enterprises), AWS Strands, Anthropic's research system all use this tiered pattern.

---

## Evidence & Confidence

### Source Agreement Analysis

| Claim                                               | Exa | Brave | Bright Data | Consensus    |
| --------------------------------------------------- | --- | ----- | ----------- | ------------ |
| ASI as drift metric (12 dimensions, 0.75 threshold) | ✓   | ✓     | ✓           | **STRONG**   |
| Separation of concerns (maker-checker)              | ✓   | ✓     | ✓           | **STRONG**   |
| Cascade amplification 40-60% after 2 iterations     | ✓   | ✓     | —           | **STRONG**   |
| Combined mitigation achieves 81.5% reduction        | ✓   | ✓     | ✓           | **STRONG**   |
| Three-tier escalation pattern                       | —   | ✓     | ✓           | **MODERATE** |
| S11 (ABA) achieves 70.4% single-strategy reduction  | ✓   | ✓     | ✓           | **STRONG**   |

### Confidence Factors

**Strengthening factors:**

- All 3 perspectives agree on core architecture (Judge-based detection, ASI metrics, graduated testing)
- L5 sources from Microsoft, Anthropic, IBM, Uber, Netflix provide production validation
- January 2026 empirical research (ArXiv 2601.04170) quantifies drift reduction rates
- Maker-checker pattern proven at enterprise scale

**Weakening factors:**

- No production examples of multi-agent autonomous coding systems in public literature
- ASI threshold (0.75) is empirically chosen—may need domain-specific calibration
- Assumption extraction from plans remains partially manual

---

## Appendix A: Strategy Reference

**Strategy Set Name:** Layered Drift Detection and Cascade Prevention Architecture
**Strategies:** 8 included, 5 excluded (future considerations)

### Included Strategies

| #   | Strategy                                 | Confidence | Score | Role                                                         |
| --- | ---------------------------------------- | ---------- | ----- | ------------------------------------------------------------ |
| S1  | ASI-Based Continuous Drift Monitoring    | HIGH       | 8.7   | Foundation — provides drift signals for all other strategies |
| S2  | Judge Owns Drift Detection               | HIGH       | 8.7   | Detection — Judge tracks ASI and validates; Coder implements |
| S4  | Graduated Testing Timing                 | HIGH       | 9.0   | Validation — test pyramid prevents error propagation         |
| S5  | Contract Testing for Assumptions         | MEDIUM     | 7.6   | Validation — catches coordination drift at boundaries        |
| S6  | Statistical Drift Detection              | HIGH       | 8.0   | Detection — trend analysis with adaptive thresholds          |
| S7  | Circuit Breakers for Cascade Containment | HIGH       | 8.7   | Response — contains failures before cascade amplification    |
| S8  | Re-Planning Triggers (Multi-Condition)   | HIGH (↑)   | 8.3   | Recovery — graduated response based on severity              |
| S11 | Adaptive Behavioral Anchoring            | HIGH (↑)   | 8.5   | Mitigation — 70.4% drift reduction via prompt anchoring      |

### Implementation Roadmap

| Phase | Strategy                           | Dependencies | Notes                                            |
| ----- | ---------------------------------- | ------------ | ------------------------------------------------ |
| 1     | S1: ASI Monitoring                 | None         | Foundation — all other strategies depend on this |
| 1     | S4: Graduated Testing              | None         | Foundation — testing infrastructure              |
| 2     | S6: Statistical Detection          | S1           | Trend detection layer                            |
| 2     | S5: Contract Testing               | S4           | Assumption validation (parallel with S6)         |
| 3     | S2: Judge Drift Detection          | S1, S6       | Uses detection signals                           |
| 3     | S7: Circuit Breakers               | S1, S4       | Uses monitoring + testing data                   |
| 4     | S8: Re-Planning Triggers           | S1, S6, S7   | Uses all detection signals                       |
| 4     | S11: Adaptive Behavioral Anchoring | S1           | Enhancement (parallel with S8)                   |

### Strategy Relationships

- S1 → S2: Judge validates based on ASI metrics (LAYERED)
- S1 → S7: Circuit breakers need ASI input for thresholds (LAYERED)
- S1 → S8: ASI thresholds define re-planning triggers (LAYERED)
- S4 → S7: Test results inform breaker thresholds (LAYERED)
- S6 → S8: Statistical thresholds define trend-based re-planning (LAYERED)
- S2 ↔ S6: Process validation + trend detection (COMPLEMENTARY)
- S4 ↔ S5: Tests verify impl; contracts verify assumptions (COMPLEMENTARY)
- S7 ↔ S8: Breakers contain; re-planning recovers (COMPLEMENTARY)
- S11 ↔ S1: ABA uses drift metrics to modulate anchoring (COMPLEMENTARY)

### Excluded Strategies

| #   | Strategy                          | Reason                                                                  |
| --- | --------------------------------- | ----------------------------------------------------------------------- |
| S3  | FSM-Based Conformance Engine      | 8/10 complexity, marginal value over S5+S8+S11, LLM FSM accuracy issues |
| S9  | Episodic Memory Consolidation     | 51.9% reduction but 23% overhead; information loss risk                 |
| S10 | Drift-Aware Routing               | 63% reduction but requires agent redundancy                             |
| S12 | AgentSpec Runtime Constraints     | 90%+ unsafe prevention but DSL learning curve, early maturity           |
| S13 | Counterfactual Causality Analysis | Single source, distributed systems domain, limited agent evidence       |

### Key Trade-offs Accepted

- 23% computational overhead for 80-85% drift reduction (acceptable per user priority: quality over speed)
- Judge-based detection adds latency vs Coder self-monitoring, but gains cognitive load reduction and cleaner separation
- Excluding FSM (S3) loses formal verification capability, but complexity-to-value ratio not justified for current phase
- Three-tier escalation adds orchestrator complexity but enables autonomous recovery before human intervention

---

## Appendix B: Future Considerations

These strategies were excluded from the current solution but documented for future investigation and potential addition:

### S3: FSM-Based Conformance Engine

**Score:** 7.4 | **Complexity:** 8/10

**Description:** State-machine validation of expected behavior sequences from MI9 framework. Formally verifies that agent execution follows prescribed state transitions.

**Why Excluded:**

- High implementation complexity (8/10)
- January 2026 research shows LLMs struggle with long FSM execution (50% accuracy degradation)
- Most value covered by S5 (Contract Testing) + S8 (Re-Planning Triggers) + S11 (ABA)
- Marginal additional benefit doesn't justify complexity

**When to Reconsider:**

- Regulatory compliance requires formal verification
- Safety-critical paths need mathematical guarantees
- FSM execution accuracy improves in future models

---

### S9: Episodic Memory Consolidation (EMC)

**Score:** 6.4 | **Complexity:** 6/10

**Description:** Periodic compression of interaction histories every 50 turns to maintain relevant context while reducing token burden.

**Why Excluded:**

- 51.9% drift reduction (good but not best single strategy)
- 23% computational overhead
- Information loss risk during summarization
- Redundant with S11 (ABA) which achieves 70.4% without memory overhead

**When to Reconsider:**

- Long-running sessions exceed context limits
- Need to maintain extended conversation history
- Compute budget increases allow overhead

---

### S10: Drift-Aware Routing

**Score:** 6.1 | **Complexity:** 7/10

**Description:** Route tasks to stable agents, reset drifting ones. Uses RL-tuned weights to prefer stable agents dynamically.

**Why Excluded:**

- 63% drift reduction (good)
- Requires agent redundancy (multiple agents capable of same tasks)
- Reset protocol complexity
- ACE currently uses specialized agents, not interchangeable ones

**When to Reconsider:**

- Move to parallel execution with multiple Coder instances
- Need redundancy for reliability
- Agent pool expands to allow routing choices

---

### S12: AgentSpec Runtime Constraints

**Score:** 6.5 | **Complexity:** 7/10

**Description:** DSL for specifying and enforcing runtime constraints. Prevents 90%+ of unsafe executions by validating actions against declarative policies.

**Why Excluded:**

- DSL learning curve for team
- Early maturity stage (2025 research)
- Contract Testing (S5) provides similar assumption validation with lower barrier

**When to Reconsider:**

- Team gains DSL experience
- AgentSpec tooling matures
- Need more formal constraint specification than contracts provide

---

### S13: Counterfactual Causality Analysis

**Score:** 5.8 | **Complexity:** 8/10

**Description:** CSnake-style fault propagation chain detection using counterfactual analysis to trace cascade failures to root causes.

**Why Excluded:**

- Single source from distributed systems domain
- Limited agent-specific evidence
- High complexity for uncertain benefit
- Circuit breakers (S7) + Re-planning (S8) handle most cascade scenarios

**When to Reconsider:**

- Need post-mortem analysis of complex failures
- Debugging cascade failures that escape circuit breakers
- More agent-specific research becomes available

---

## Appendix C: Context

### Original Question

How do we catch problems DURING and AFTER implementation? Who validates drift and when?

**Sub-questions:**

1. Drift Validation Responsibility: Who validates that implementation doesn't break future sub-plan assumptions?
2. Integration Pulse Timing: When should full regression suite run?
3. Re-Planning Triggers: What triggers re-planning of future sub-plans?

**The Cascade Problem:** 10% drift in SP-1 → potential 40% rework in SP-4

### Goal Context (from Process.md)

**System:** Autonomous Coding Ecosystem (ACE) — highly automated software development factory
**Core Purpose:** Transform high-level master plans into production-ready code through four-layer pipeline
**Pipeline:** Plan Creation → Coding Execution → Verification & Quality → Merge & Synthesis

**Key Agents:** Orchestrator (SDK), Architect, Scout, Tester, Coder, Verifier, Sub-Plan Verifier, Judge

**Constraints:**

- Sequential sub-plan execution (parallel deferred)
- 3-iteration fix cycle before escalation
- E2E testing is final gate before merge
- Git Worktrees for isolation

### User Context (gathered during triage)

**System Constraints:** Quality over speed — willing to accept overhead for better drift prevention

**Team Expertise:** AI-assisted execution with web research capabilities and other models (Codex, Gemini)

**Priority:** Combination of long-term maintainability, usability, easy improvements/changes, functional system that's not overly complex. Simple but effective solutions preferred, but most important is producing the best, most usable, effective, and efficient code.

---

## Appendix D: Intervention History

| #   | Question                                                                                                           | Mode      | Result                                                                            |
| --- | ------------------------------------------------------------------------------------------------------------------ | --------- | --------------------------------------------------------------------------------- |
| 1   | How do Coder and Judge detect drift, what happens after drift is detected, escalation model, and medium strategies | deep-dive | Drift mechanics clarified, three-tier escalation defined, S8+S11 upgraded to HIGH |
| 2   | Should Coder handle drift detection or should Judge own all drift detection?                                       | compare   | Judge should own all drift detection (unanimous consensus)                        |

Investigation files:

- `interventions/q1-drift-detection-mechanisms-technical.md`
- `interventions/q1-tiered-escalation-production.md`
- `interventions/q1-medium-strategies-analysis-emerging.md`
- `interventions/q1-synthesis.md`
- `interventions/q2-drift-detection-ownership-technical.md`
- `interventions/q2-drift-detection-responsibility-production.md`
- `interventions/q2-synthesis.md`
- `interventions/intervention-log.json`

---

## Appendix E: Research Session

### Research Files

- Exa findings: `/Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-19-validation-drift-detection/exa-findings.md`
- Brave findings: `/Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-19-validation-drift-detection/brave-findings.md`
- Brightdata findings: `/Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-19-validation-drift-detection/brightdata-findings.md`
- Synthesis: `/Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-19-validation-drift-detection/synthesis.md`

### Consensus Points from Research

- **Agent Stability Index (ASI) as drift metric** — 12 dimensions, threshold 0.75, rolling 50-interaction windows [Exa+Brave+Bright Data]
- **Combined mitigation achieves 81.5% drift reduction** vs 70.4% best single strategy [Exa+Brave+Bright Data]
- **Process validation catches drift earlier than output validation** (IBM case study) [Exa+Brave]
- **Cascade failures amplify 40-60% when undetected >2 iterations** (Uber production data) [Brave+Exa]
- **Separation of concerns (maker-checker) is production standard** [Microsoft, Anthropic, IBM]

### Conflicts Identified

- **Drift detection timing**: Behavioral drift at 73 interactions vs model drift from day one — _Need both detection modes_
- **Mitigation sufficiency**: Combined strategies required vs circuit breakers sufficient — _Different problem spaces, need both_
- **Testing frequency**: Heavy unit/sparse E2E vs more E2E with AI — _Sequential pipelines need frequent integration tests_

---

## Blueprint Addition for Process.md

```markdown
## RQ-3b: Validation & Drift Detection ✓

**Resolved:** 2026-01-19 | **Confidence:** 85%

**Question:** How do we catch problems DURING and AFTER implementation? Who validates drift and when?

### SOLUTION: Layered Drift Detection with Judge-Based Detection

**Architecture Overview:**

- **Judge owns all drift detection** (not Coder) — maker-checker separation
- **Three-tier escalation**: Agent (≥90%) → Orchestrator with web research (60-89%) → Human (<60%)
- **Graduated testing**: Unit (every SP) → Integration (every 2 SP) → Regression (every 3-5) → E2E (end only)
- **Multi-condition re-planning triggers**: ASI thresholds, contract failures, integration failures, circuit breakers

**Strategy Set (8 included):**
| # | Strategy | Score | Role |
|---|----------|-------|------|
| S1 | ASI-Based Continuous Drift Monitoring | 8.7 | Foundation |
| S2 | Judge Owns Drift Detection | 8.7 | Detection |
| S4 | Graduated Testing Timing | 9.0 | Validation |
| S5 | Contract Testing for Assumptions | 7.6 | Validation |
| S6 | Statistical Drift Detection | 8.0 | Detection |
| S7 | Circuit Breakers for Cascade Containment | 8.7 | Response |
| S8 | Re-Planning Triggers (Multi-Condition) | 8.3 | Recovery |
| S11 | Adaptive Behavioral Anchoring | 8.5 | Mitigation |

**Key Decisions:**
| Decision | Choice | Implication |
|----------|--------|-------------|
| Drift detection owner | Judge (not Coder) | Clean separation, reduced cognitive load |
| Escalation thresholds | 90% / 60% confidence | Orchestrator handles 60-89% with web research |
| Integration timing | Every 2 sub-plans | Prevents 40-60% cascade amplification |
| Re-planning trigger | ASI <0.60 for 2 windows | Based on empirical research |

**Dependencies:**

- **Unblocks:** OQ-6 (has drift detection integration), Judge prompt design, final validation flow
- **Integrates with:** Sub-Plan Verifier (RQ-3a), Severity Classification (RQ-3a)

**Full Specification:** `research/2026-01-19-validation-drift-detection/internal-solution.md`
```

---

## Next Steps

To validate and finalize this solution:

```bash
# Switch to Solution-Validator profile
solv

# Run validation
/validate-solution "/Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-19-validation-drift-detection/internal-solution.md"
```

If you have an external solution to compare:

```bash
/validate-solution "/Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-19-validation-drift-detection/internal-solution.md" "/path/to/external-solution.md"
```
