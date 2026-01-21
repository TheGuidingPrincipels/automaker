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
| Multi-User Authentication System    | High     | Planned  | [002-multi-user-authentication-system.md](./002-multi-user-authentication-system.md) |
| Rollup Circular Dependency Warnings | Low      | Deferred | [001-rollup-circular-deps.md](./001-rollup-circular-deps.md)                         |

---

## Priority Levels

- **High**: Should be addressed soon, impacts development experience significantly
- **Medium**: Worth doing when touching related code
- **Low**: Nice to have, no urgency
- **Deferred**: Waiting on external factors (e.g., upstream changes)
