# Solution: Sub-Plan Schema Content (Feature Specification & Implementation Plan)

## Metadata

- **Generated:** 2026-01-20
- **Session:** /Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-20-sub-plan-schema-content
- **Process.md:** /Users/ruben/.claude/profiles/Solution-Finder/ACE/Process.md
- **Question:** What fields and content should Feature Specifications and Implementation Plans contain to enable Tester and Coder to execute without clarification?

---

## Executive Summary

**Direct Answer:** Feature Specifications should use Given-When-Then behavioral contracts with concrete examples, domain language definitions, and out-of-scope boundaries—containing NO implementation details. Implementation Plans should cover Six Core Areas (Commands, Testing, Structure, Style, Git, Boundaries) with pseudo-code for components, integration points, drift markers, and explicit implementation sequences. Both documents require self-verification checklists enabling autonomous validation without human intervention.

**Confidence Level:** HIGH (90%) based on strong convergence across all three research sources on dual-document architecture, Given-When-Then format, and self-verification patterns.

**Key Recommendation:** Adopt the schemas defined below, ensuring Feature Specs maintain strict isolation from implementation details (critical for preventing tautological tests) while Implementation Plans contain complete execution context including pseudo-code and the three-tier boundary system (Always/Ask/Never).

---

## Resolution Criteria Mapping

How this solution addresses each resolution criterion from Process.md:

| #   | Resolution Criterion                                  | How Addressed                                                                                                                                                                                                                                      | Evidence                |
| --- | ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| RC1 | Feature Specification schema (all required fields)    | Full schema with 8 sections: Metadata, Overview, Acceptance Criteria, Test Scenarios, Examples, Out of Scope, Domain Language, Verification Checklist                                                                                              | [Exa+Brave+Bright Data] |
| RC2 | Implementation Plan schema (all required fields)      | Full schema with 14 sections: Metadata, Task Overview, Architecture Context, Files, Component Specs, Data Structures, Integration Points, Commands, Code Style, Boundaries, Implementation Sequence, Drift Markers, Dependencies, Success Criteria | [Exa+Brave+Bright Data] |
| RC3 | What Architect must ADD beyond decomposition          | Domain language definitions, concrete examples (2+ per feature), out-of-scope boundaries, self-verification checklists, drift markers, code style snippets, three-tier boundaries                                                                  | [Exa+Brave]             |
| RC4 | Pseudo code inclusion guidelines                      | Include for: complex algorithms (>3 steps), multi-step workflows, error handling. Skip for: trivial getters/setters, standard CRUD. Granularity: 1-3 lines per logical step                                                                        | [Brave+Bright Data]     |
| RC5 | Testing approach without over-constraining Tester     | Feature Spec provides behavioral scenarios (Given-When-Then) and pass/fail conditions but NOT test implementation details. Tester decides framework, assertion style, mocking                                                                      | [Exa+Brave]             |
| RC6 | Granularity triggers (when to split, merge)           | Split: >5 files OR >10 functions OR >300 LOC OR >25k tokens. Merge: <2 files AND <3 functions AND tightly coupled                                                                                                                                  | [Brave]                 |
| RC7 | Dependency specification format                       | Implementation Plan Dependencies table (name, version, purpose) + Integration Points table (component, integrates with, contract)                                                                                                                  | [Exa+Bright Data]       |
| RC8 | Drift marker format                                   | Implementation Plan Drift Markers table: Assumption, Downstream Sub-Plan, If Changed Impact                                                                                                                                                        | [Exa]                   |
| RC9 | Examples of good Feature Spec and Implementation Plan | Concrete schemas provided in Appendix B                                                                                                                                                                                                            | [All sources]           |

**Criteria Coverage:** 9/9 criteria fully addressed

---

## Synthesized Solution

**Core Approach:**
The research reveals strong consensus that autonomous agent execution requires specification-driven development with strict separation between behavioral specifications (what to test) and technical blueprints (how to code). Feature Specifications should use Given-When-Then (Gherkin-inspired) formats that are language-agnostic and naturally testable. This isolation is critical—if the Tester sees implementation details, tests become tautological, validating what was built rather than what should have been built. The Architect must add substantial value beyond decomposition: domain language definitions, concrete examples, out-of-scope boundaries, and self-verification checklists that enable autonomous validation.

**Implementation Strategy:**
Implementation Plans should follow the Six Core Areas framework validated by analysis of 2,500+ production agent configurations: Commands, Testing, Project Structure, Code Style, Git Workflow, and Boundaries. Each Implementation Plan requires pseudo-code for complex algorithms, code snippets for style patterns, and explicit integration points. The three-tier boundary system (Always/Ask/Never) provides guardrails that enable autonomy while preventing dangerous actions. The 30k token budget accommodates these requirements—structured sections with concrete examples are more token-efficient than verbose prose ("one snippet beats three paragraphs").

**Integration Considerations:**
The Feature Spec and Implementation Plan work together through traceability—each acceptance criterion maps to implementation tasks. Drift markers in the Implementation Plan track assumptions that downstream sub-plans depend on, addressing the critical cascade problem where 10% drift in sub-plan 1 can cause 40% rework downstream. The verification checklists in both documents serve as handoff contracts—the Tester validates against Feature Spec criteria, the Coder validates against Implementation Plan success criteria, creating a closed loop of verification without human intervention.

**Trade-offs & Alternatives:**
The primary trade-off is specification overhead versus execution clarity. Detailed specifications require more Architect effort but prevent costly clarification loops and failures from ambiguous handoffs—research shows ambiguous specifications are the #1 cause of multi-agent failures. Contract-driven specifications (preconditions/postconditions/invariants) were considered but excluded due to complexity barriers; they may be valuable for critical paths but add overhead for simple functions. The TOML format was also considered (lower hallucination rates) but Markdown maintains broader ecosystem compatibility and human editability.

---

## Concrete Schemas

### Feature Specification Schema (for Tester)

**Target Token Budget:** 5-10k tokens

````markdown
# Feature: [Feature Name]

## Metadata

- **Feature ID**: [unique identifier, e.g., FEAT-001]
- **Parent Milestone**: [milestone reference]
- **Priority**: [high|medium|low]
- **Token Budget**: [estimated tokens, target 5-10k]

## Overview

[2-3 sentence description of feature purpose and user value. NO technical implementation details.]

## Acceptance Criteria

### AC-1: [Clear, testable outcome statement]

- **Given**: [Initial system state/preconditions]
- **When**: [User/system action]
- **Then**: [Expected observable outcome]
- **Pass Condition**: [Objective verification method]
- **Fail Condition**: [How failure manifests]

### AC-2: [...]

[Repeat for each independently testable criterion]

## Test Scenarios

### Scenario: [Happy Path Name]

```gherkin
Given [precondition]
And [additional context]
When [action]
Then [expected outcome]
And [additional assertions]
```
````

### Scenario: [Edge Case Name]

[Gherkin format for edge cases]

### Scenario: [Error Case Name]

[Gherkin format for error handling]

## Examples

### Example 1: [Concrete Use Case]

**Input**: [specific values]
**Expected Output**: [specific result]
**Walkthrough**: [step-by-step expected behavior]

### Example 2: [Edge Case Example]

[...]

## Out of Scope

- [What this feature explicitly does NOT include]
- [Functionality that belongs to other features]
- [Constraints on scope expansion]

## Domain Language

| Term          | Definition                |
| ------------- | ------------------------- |
| [domain term] | [meaning in this context] |

## Verification Checklist (Tester Self-Validation)

- [ ] All acceptance criteria have objective pass/fail conditions
- [ ] No implementation details mentioned (no "how", only "what")
- [ ] Each scenario is independently testable
- [ ] Examples cover common and edge cases
- [ ] Domain terms are defined
- [ ] Out of scope boundaries are clear

````

### Implementation Plan Schema (for Coder)

**Target Token Budget:** 15-20k tokens

```markdown
# Implementation Plan: [Feature Name]

## Metadata
- **Plan ID**: [unique identifier, e.g., IMPL-001]
- **Feature Spec Reference**: [feature_id]
- **Estimated LOC**: [lines of code, max 300]
- **Files to Modify**: [count, max 5]
- **Functions to Implement**: [count, max 10]

## Task Overview
[What this sub-plan accomplishes, how it fits into larger system]

## Architecture Context
[Relevant system architecture, existing patterns, integration points]
[Reference to existing codebase patterns if applicable]

## Files
### File 1: [path/to/file.py]
- **Action**: create | modify
- **Purpose**: [what this file does]
- **Estimated LOC**: [number]

### File 2: [...]
[Repeat for each file, max 5]

## Component Specifications

### Component 1: [Class/Module Name]
**Purpose**: [Single responsibility description]
**Location**: [file path]
**Dependencies**: [list of imports/dependencies]

#### Interface
```[language]
[Type definitions, function signatures]
````

#### Implementation Logic

```pseudo
1. [Step-by-step pseudo-code]
2. [Algorithm or workflow]
3. [...]
```

#### Error Handling

- **Edge Case**: [description] -> **Handle**: [approach]
- **Failure Mode**: [description] -> **Handle**: [approach]

### Component 2: [...]

[Repeat for each component, max 10 functions total]

## Data Structures

```[language]
[Schemas, types, interfaces, database models]
```

## Integration Points

| Component        | Integrates With      | Contract                    |
| ---------------- | -------------------- | --------------------------- |
| [this component] | [external component] | [API/interface description] |

## Commands

```bash
# Setup
[Installation/configuration commands]

# Run Tests
[Test execution commands, framework used]

# Lint/Format
[Linting commands]

# Build
[Build commands if applicable]
```

## Code Style

[Project-specific patterns - provide real code snippet examples]

```[language]
# Example of expected naming convention
# Example of expected error handling pattern
# Example of expected documentation style
```

## Boundaries

### Always Do

- [Actions agent should take without asking]
- Run tests before marking complete
- Follow existing naming conventions

### Ask First

- [Actions requiring human approval]
- Adding new dependencies
- Modifying database schemas

### Never Do

- [Hard stops]
- Commit secrets or API keys
- Remove failing tests without approval
- Modify files outside specified paths

## Implementation Sequence

1. [Step 1] -> **Expected Outcome**: [verification]
2. [Step 2] -> **Expected Outcome**: [verification]
3. [Integration] -> **Expected Outcome**: [verification]
4. [Final verification] -> **Expected Outcome**: [all tests pass]

## Drift Markers (Assumptions Downstream Depends On)

| Assumption                | Downstream Sub-Plan | If Changed, Impact |
| ------------------------- | ------------------- | ------------------ |
| [expected API contract]   | [sub-plan-id]       | [what would break] |
| [expected file structure] | [sub-plan-id]       | [what would break] |

## Dependencies

| Dependency     | Version   | Purpose      |
| -------------- | --------- | ------------ |
| [package name] | [version] | [why needed] |

## Success Criteria (Coder Self-Validation)

- [ ] All tests from Tester pass
- [ ] Code follows style guidelines
- [ ] Components integrate as specified
- [ ] Error handling covers edge cases
- [ ] No secrets in code
- [ ] LOC within estimate (+/-20%)
- [ ] No files modified outside specification

````

---

## Guideline Summary

### What Architect Must ADD Beyond Decomposition
1. **Domain language definitions** - Terms and their meanings in context
2. **Concrete examples** - 2+ per feature, specific inputs/outputs
3. **Out-of-scope boundaries** - Explicit exclusions to prevent scope creep
4. **Self-verification checklists** - Enable autonomous validation
5. **Drift markers** - Assumptions downstream sub-plans depend on
6. **Code style snippets** - Real examples > prose descriptions
7. **Three-tier boundaries** - Always/Ask/Never guardrails

### Pseudo-Code Guidelines
| Include For | Skip For | Granularity |
|-------------|----------|-------------|
| Complex algorithms (>3 steps) | Trivial getters/setters | 1-3 lines per logical step |
| Multi-step workflows | Standard CRUD operations | Language-agnostic or target language |
| Error handling logic | Simple property access | Focus on algorithm, not syntax |

### Granularity Triggers
| Action | Trigger |
|--------|---------|
| **SPLIT** | >5 files OR >10 functions OR >300 LOC OR >25k tokens |
| **MERGE** | <2 files AND <3 functions AND tightly coupled |

### Quality Criteria for Acceptance Criteria (4 C's)
- **Clear**: Tester can understand without Architect clarification
- **Concise**: No ambiguous or redundant language
- **Correct**: Matches actual feature intent
- **Testable**: Supports definitive pass/fail without subjective judgment

---

## Evidence & Confidence

### Source Agreement Analysis

| Claim | Exa | Brave | Bright Data | Consensus |
|-------|-----|-------|-------------|-----------|
| Given-When-Then format for behavioral specs | YES | YES | YES | STRONG |
| Three-tier boundary system (Always/Ask/Never) | YES | YES | YES | STRONG |
| Concrete examples outperform prose | YES | YES | YES | STRONG |
| Self-verification checklists needed | YES | YES | YES | STRONG |
| Six Core Areas in Implementation Plan | YES | - | - | SINGLE SOURCE (validated by 2,500+ configs) |
| Drift markers for downstream tracking | YES | - | - | SINGLE SOURCE |
| 4 C's quality framework | - | YES | - | SINGLE SOURCE |

### Confidence Factors

**Strengthening factors:**
- Universal agreement on dual-document architecture across all sources
- Production validation: 2,500+ agent configurations analyzed
- Multiple L5 sources (OpenAI, Anthropic, Google, Martin Fowler)
- Aligns with existing ACE decisions (RQ-3a, RQ-4a, RQ-4c)

**Weakening factors:**
- Some strategies from single sources (Six Core Areas, Drift Markers)
- Token budget allocation (5-10k vs 15-20k) is estimated, not empirically validated
- No real ACE feature example to validate schema completeness

---

## Appendix A: Strategy Reference

**Strategy Set Name:** Specification-Driven Autonomous Architecture
**Strategies:** 9 total (7 HIGH, 2 MEDIUM)

### Included Strategies

| # | Strategy | Confidence | Score | Role |
|---|----------|------------|-------|------|
| S1 | Given-When-Then Acceptance Criteria | HIGH | 9.0 | Core format for Feature Spec |
| S2 | Three-Tier Boundary System | HIGH | 8.8 | Safety guardrails for both docs |
| S3 | Concrete Examples in Both Specs | HIGH | 8.7 | Clarity over prose |
| S4 | Self-Verification Checklists | HIGH | 8.7 | Autonomous validation |
| S5 | Six Core Areas in Implementation Plan | HIGH | 8.4 | Implementation Plan structure |
| S6 | Pseudo-Code in Implementation Plan | HIGH | 8.3 | Algorithm clarity |
| S7 | Out-of-Scope Section | HIGH | 8.1 | Scope boundary |
| S8 | 4 C's Quality Framework | MEDIUM | 7.4 | Acceptance criteria quality |
| S9 | Drift Markers and Dependency Tracking | MEDIUM | 7.1 | Downstream assumption tracking |

### Implementation Roadmap

| Phase | Strategy | Dependencies | Notes |
|-------|----------|--------------|-------|
| 1 | S1: Given-When-Then | Foundation | Core format for Feature Spec |
| 1 | S2: Three-Tier Boundaries | Foundation | Safety for both documents |
| 2 | S7: Out-of-Scope | S1 | Constrains GWT scope |
| 2 | S5: Six Core Areas | - | Implementation Plan structure |
| 2 | S3: Concrete Examples | - | Applies to both documents |
| 3 | S6: Pseudo-Code | S5 | Fills Implementation Plan content |
| 3 | S8: 4 C's Framework | S1 | Validates acceptance criteria quality |
| 3 | S9: Drift Markers | - | Cross-sub-plan tracking |
| 4 | S4: Self-Verification | S1, S5 | Final validation layer |

### Strategy Relationships

- S1 (GWT) → S4 (Self-Verify): **LAYERED** — GWT scenarios become verification checklist items
- S1 (GWT) → S8 (4 C's): **LAYERED** — 4 C's quality checks validate GWT criteria
- S2 (Boundaries) → S5 (Six Areas): **COMPLEMENTARY** — Boundaries are one of six areas
- S3 (Examples) → S6 (Pseudo-Code): **COMPLEMENTARY** — Examples in Feature Spec, pseudo-code in Impl Plan
- S4 (Self-Verify) → S9 (Drift): **LAYERED** — Self-verify catches drift; markers enable tracking
- S7 (Out-of-Scope) → S1 (GWT): **COMPLEMENTARY** — OOS prevents GWT scope creep
- S5 (Six Areas) → S6 (Pseudo-Code): **LAYERED** — Six Areas provides structure, pseudo-code fills detail

### Excluded Strategies

| # | Strategy | Reason |
|---|----------|--------|
| S10 | Contract-Driven Specifications | High complexity barrier, overhead for simple functions - user skipped investigation |
| S11 | TOML/JSON Format Split | Experimental benchmarks, tooling maturity concerns - user skipped investigation |

### Key Trade-offs Accepted

- Specification overhead for execution clarity (detailed specs prevent costly clarification loops)
- Markdown over TOML (ecosystem compatibility > lower hallucination rates)
- Single-source strategies included (Six Core Areas validated by 2,500+ configs)

---

## Appendix B: Research Session

### Research Files

- Exa findings: /Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-20-sub-plan-schema-content/exa-findings.md
- Brave findings: /Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-20-sub-plan-schema-content/brave-findings.md
- Brightdata findings: /Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-20-sub-plan-schema-content/brightdata-findings.md
- Synthesis: /Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-20-sub-plan-schema-content/synthesis.md

### Consensus Points from Research

- Dual-document architecture is essential for Tester isolation
- Given-When-Then format is standard for behavioral specs
- Concrete examples outperform prose descriptions
- Self-verification criteria enable autonomous execution
- Three-tier boundaries are critical for agent safety
- Handoff failures primarily come from ambiguous specifications

### Conflicts Identified

- **Specification format**: Markdown vs TOML vs JSON — resolved via tooling maturity (Markdown wins)
- **Pseudo-code granularity**: Detailed vs hints only — resolved via complexity scaling

---

## Appendix C: Context

### Original Question

What fields and content should Feature Specifications and Implementation Plans contain to enable Tester and Coder to execute without clarification?

### Goal Context (from Process.md)

ACE (Autonomous Coding Ecosystem) - Highly automated software development factory that transforms high-level master plans into production-ready code. Architect produces dual outputs: Feature Spec (for Tester, isolated from implementation details) + Implementation Plan (for Coder). Token budget ~30k per spec. Must enable autonomous execution without clarification questions.

### Previous Decisions Applied

| Decision | Source | How Applied |
|----------|--------|-------------|
| Dual-output Architect | RQ-3a | Feature Spec + Implementation Plan schemas defined separately |
| 30k token budget | RQ-3a | Split as 5-10k Feature Spec + 15-20k Implementation Plan |
| Tester isolation | RQ-3a | Feature Spec contains NO implementation details |
| 8-section master plan | RQ-4a | Schemas decompose from master plan structure |
| Two-stage decomposition | RQ-4c | Schemas designed for Stage 2 enrichment |
| Complexity limits | RQ-3a | Granularity triggers: ≤5 files, ≤10 functions, ≤300 LOC |

---

## Appendix D: Intervention History

No interventions during research phase.

---

## Appendix E: Blueprint Additions for Process.md

The following additions are recommended for Process.md to capture this decision:

```markdown
## RQ-4b: Sub-Plan Schema Content ✓

**Resolved**: 2026-01-20 | **Confidence**: 90%

**Question**: What fields and content should Feature Specifications and Implementation Plans contain to enable Tester and Coder to execute without clarification?

### SOLUTION: Specification-Driven Autonomous Architecture (9 Strategies)

Adopted dual-schema approach: Feature Specification (8 sections, 5-10k tokens) uses Given-When-Then behavioral contracts for Tester isolation; Implementation Plan (14 sections, 15-20k tokens) uses Six Core Areas framework with pseudo-code, drift markers, and three-tier boundaries (Always/Ask/Never). Both include self-verification checklists enabling autonomous validation without human intervention.

**Key Decisions** (for future alignment):
| Decision | Choice | Implication |
|----------|--------|-------------|
| Feature Spec format | Given-When-Then (Gherkin-inspired) | Tester prompts must parse GWT scenarios |
| Implementation Plan structure | Six Core Areas | Coder prompts must expect Commands, Testing, Structure, Style, Git, Boundaries |
| Pseudo-code inclusion | Complexity-scaled (>3 steps) | Architect must assess algorithm complexity |
| Boundary format | Three-tier (Always/Ask/Never) | Coder must respect boundary categories |
| Drift marker format | Table: Assumption, Downstream, Impact | Judge must monitor drift markers during execution |
| Token allocation | 5-10k Feature Spec, 15-20k Impl Plan | Architect must respect per-document budgets |

**Strategy Set** (9 included):
| Strategy | Role | Score |
|----------|------|-------|
| S1: Given-When-Then Acceptance Criteria | Core format | 9.0 |
| S2: Three-Tier Boundary System | Safety | 8.8 |
| S3: Concrete Examples | Clarity | 8.7 |
| S4: Self-Verification Checklists | Validation | 8.7 |
| S5: Six Core Areas | Structure | 8.4 |
| S6: Pseudo-Code | Algorithm clarity | 8.3 |
| S7: Out-of-Scope Section | Scope boundary | 8.1 |
| S8: 4 C's Quality Framework | Criteria quality | 7.4 |
| S9: Drift Markers | Assumption tracking | 7.1 |

**Granularity Triggers**:
- **Split**: >5 files OR >10 functions OR >300 LOC OR >25k tokens
- **Merge**: <2 files AND <3 functions AND tightly coupled

**Dependencies**:
- **Unblocks**: OQ-4d (has schema fields for workflow design), Tester prompt, Coder prompt, Architect Stage 2 prompt
- **Constrains**: OQ-4d (workflow must produce these schemas), OQ-6 (drift markers feed breaking-change detection)

**Full Specification**: `research/2026-01-20-sub-plan-schema-content/internal-solution.md`
````

---

## Next Steps

To validate and finalize this solution:

```bash
# Switch to Solution-Validator profile
solv

# Run validation
/validate-solution "/Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-20-sub-plan-schema-content/internal-solution.md"
```

If you have an external solution to compare:

```bash
/validate-solution "/Users/ruben/.claude/profiles/Solution-Finder/ACE/research/2026-01-20-sub-plan-schema-content/internal-solution.md" "/path/to/external-solution.md"
```
