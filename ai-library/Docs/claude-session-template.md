```
You are implementing the Knowledge Library application. Your task is to execute Sub-Plan B.

## Project Context

This is a multi-phase implementation project. Each sub-plan builds on previous ones.

**Plan Files Location**:
- `sub-plan-A-core-engine.md` - Core data models, session management, extraction
- `sub-plan-B-smart-routing.md` - Planning flow, cleanup/routing plans, candidate finding
- `sub-plan-3A-vector-infrastructure.md` - Qdrant, embeddings, indexing, semantic search
- `sub-plan-3B-intelligence-layer.md` - Classification, taxonomy, relationships, ranking
- `sub-plan-D-rest-api.md` - FastAPI endpoints
- `sub-plan-E-query-mode.md` - RAG query engine
- `sub-plan-F-webui-migration.md` - Web interface

**Progress Tracking**: `progress-tracking.md`

## Your Process (Follow Exactly)

### Phase 1: Understand Context
2. Read the sub-plan file for `[SUB-PLAN-ID]`
3. If this sub-plan has dependencies, verify they are marked complete in progress tracking
4. Identify any interface contracts you must preserve (listed in progress-tracking.md)

### Phase 2: Plan (REQUIRED - Start in Plan Mode)
1. Enter plan mode to analyze the sub-plan thoroughly
2. Map sub-plan requirements to specific implementation tasks
3. Identify files to create and files to modify
4. Note any ambiguities or decisions needed
5. Create a detailed implementation plan with ordered steps
6. Exit plan mode only after I approve your plan

### Phase 3: Implement
1. Execute your approved plan step by step
2. Create files as specified in the sub-plan (copy code verbatim when provided)
3. Write tests for new functionality
4. Maintain backward compatibility with existing interfaces
5. Use the TodoWrite tool to track progress through implementation

### Phase 4: Verify
After implementation, verify against the sub-plan:
1. Read through ALL acceptance criteria in the sub-plan
2. Check each criterion is implemented
3. Run any tests to confirm functionality
4. List any criteria NOT yet complete


## Critical Rules

1. **Plan Mode First**: Always start in plan mode. Do not implement until I approve your plan.
2. **Read Before Write**: Read existing files before modifying them.
3. **Preserve Interfaces**: Check interface contracts in progress-tracking.md - do not break them.
4. **No Silent Failures**: If something doesn't work, report it clearly.
5. **Verify Against Sub-Plan**: Your final verification must check every acceptance criterion.

## Sub-Plan to Execute

**Execute Sub-Plan [SUB-PLAN-ID]**

Please begin by reading the progress tracking file and the sub-plan, then enter plan mode.
```

---

## Quick Reference: Sub-Plan IDs

| ID  | Name                  | Prerequisites      |
| --- | --------------------- | ------------------ |
| A   | Core Engine           | None               |
| B   | Smart Routing         | A                  |
| 3A  | Vector Infrastructure | A, B               |
| 3B  | Intelligence Layer    | A, B, 3A           |
| D   | REST API              | A, B, 3A           |
| E   | Query Mode            | A, B, 3A, 3B, D    |
| F   | Web UI Migration      | A, B, 3A, 3B, D, E |
