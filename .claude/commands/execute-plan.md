# Execute Plan

Generate a token-efficient execution prompt for a downstream Claude Code session to implement a plan.

## Purpose

When you have an implementation plan (single or part of a multi-plan chain), this command helps create a concise prompt that instructs a downstream Claude Code session to execute it.

## Workflow

1. **You provide**: Plan file path/link to this session
2. **This session creates**: A markdown prompt file saved to repo root
3. **You then provide**: The prompt file + plan link to the downstream session
4. **Downstream session**: Reads plan, executes implementation

## Prompt Generation

When invoked, analyze the provided plan and generate a prompt file with:

### Required Elements

```markdown
# Plan Execution: {Plan Title}

## Task

Read and execute the implementation plan at: `{plan-path}`

## Instructions

1. Read the entire plan before starting any implementation
2. Follow the plan steps in order unless dependencies require reordering
3. Mark each step complete as you finish it
4. If blocked, report the blocker before proceeding

## Plan Context

- **Plan**: {N} of {Total} (if multi-part chain)
- **Scope**: {Brief 1-line scope description}
- **Key deliverables**: {Bulleted list of main outputs}

## Constraints

{Any critical constraints from the plan}
```

### Token Efficiency Rules

- Maximum 50 lines for the generated prompt
- No duplicating plan content—reference the plan path
- Use bullet points, not paragraphs
- Include only actionable directives

## Output

Save the generated prompt to:

```
docs/plan-prompts/EXECUTE-{plan-name}.md
```

Example: `docs/plan-prompts/EXECUTE-knowledge-library-cleanup-phase-1.md`

## Usage Examples

### Single Plan

```
User: /execute-plan
User: Here's my plan: Plans + Improvements + Ideas/004-knowledge-library-cleanup-ai.md

Claude: [Reads plan, generates prompt]
Created: docs/plan-prompts/EXECUTE-knowledge-library-cleanup-ai.md
```

### Multi-Part Plan Chain

```
User: /execute-plan
User: This is part 2 of 3. Plan: Plans/feature-x-part-2.md

Claude: [Reads plan, generates prompt noting it's part 2/3]
Created: docs/plan-prompts/EXECUTE-feature-x-part-2.md
```

## Downstream Session Usage

After creating the prompt file, start a new Claude Code session and:

```
User: @docs/plan-prompts/EXECUTE-{plan-name}.md
User: Plan location: {path-to-plan}
User: Execute this plan
```

## Key Files

| File                            | Purpose                     |
| ------------------------------- | --------------------------- |
| `Plans + Improvements + Ideas/` | Common plan storage         |
| `docs/plan-prompts/`            | Generated execution prompts |
