# Possible Improvements

This folder tracks potential improvements, refactoring opportunities, and technical debt that could be addressed in the future. Items here are not bugs or blockers - they are enhancements that would improve code quality, performance, or maintainability.

## How to Use This Folder

1. **Add new items** when you discover something that could be improved but isn't urgent
2. **Include context** - explain why it's an improvement and what the tradeoffs are
3. **Note dependencies** - if fixing something depends on upstream changes, note that
4. **Update status** when items are addressed or become obsolete

## Current Items

| Item                                | Priority | Status   | File                                                                                 |
| ----------------------------------- | -------- | -------- | ------------------------------------------------------------------------------------ |
| Knowledge Library Cleanup UI        | High     | Ready    | [003-knowledge-library-cleanup-ui.md](./003-knowledge-library-cleanup-ui.md)         |
| Knowledge Library Cleanup AI        | High     | Ready    | [004-knowledge-library-cleanup-ai.md](./004-knowledge-library-cleanup-ai.md)         |
| Multi-User Authentication System    | High     | Planned  | [002-multi-user-authentication-system.md](./002-multi-user-authentication-system.md) |
| Rollup Circular Dependency Warnings | Low      | Deferred | [001-rollup-circular-deps.md](./001-rollup-circular-deps.md)                         |

### Implementation Order for Knowledge Library

1. **Plan 003 (UI)** - Implement first (~7 hours)
   - Shows full block content, confidence bars, color-coded recommendations
   - Users can see exactly what will be removed

2. **Plan 004 (AI)** - Implement second (~9 hours)
   - Better decision criteria, signal detection
   - Requires Plan 003 to display the improved AI output

---

## Priority Levels

- **High**: Should be addressed soon, impacts development experience significantly
- **Medium**: Worth doing when touching related code
- **Low**: Nice to have, no urgency
- **Deferred**: Waiting on external factors (e.g., upstream changes)
