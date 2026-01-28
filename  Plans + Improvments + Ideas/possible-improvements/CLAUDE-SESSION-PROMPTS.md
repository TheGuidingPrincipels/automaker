# Claude Code Session Prompts

This file contains ready-to-copy prompts for dedicated Claude Code sessions. Execute the plans in order:

1. **Session 1**: Knowledge Library Cleanup UI (Plan 003)
2. **Session 2**: Knowledge Library Cleanup AI (Plan 004) - depends on Plan 003

---

## Session 1: Knowledge Library Cleanup UI

**Plan File**: `003-knowledge-library-cleanup-ui.md`

**Copy the prompt below and paste it into a new Claude Code session:**

---

```
I need you to implement a detailed plan for improving the Knowledge Library cleanup review UI.

**First, read the complete plan file:**
/Users/ruben/Documents/GitHub/automaker/ Plans + Improvments + Ideas/possible-improvements/003-knowledge-library-cleanup-ui.md

**Context:**
This plan improves the cleanup review UI in the Knowledge Library feature to show:
- Full block content (expandable)
- AI confidence percentages with visual bar
- Color-coded recommendations (green=keep, red=discard)
- Clearer block boundaries (block type + source line range)

**Your task:**
1. Read and understand the complete plan file
2. Follow the implementation phases in order:
   - Phase 1: Backend confidence propagation
   - Phase 2: Frontend Type Updates
   - Phase 3: UI Enhancements (new components + cleanup-review updates)
   - Phase 4: Non-AI Mode Fallback
3. Create the new component files as specified
4. Modify the existing files as outlined
5. Ensure no workflow regressions (preserve existing tab behavior and decision-changing capabilities)

**Important constraints:**
- Do NOT embed full block content in cleanup plan payloads - fetch via existing Blocks API
- Clamp confidence values to [0.0, 1.0]
- Preserve the existing "change my mind" workflow

After implementing, verify the acceptance criteria from the plan are met.
```

---

## Session 2: Knowledge Library Cleanup AI

**Plan File**: `004-knowledge-library-cleanup-ai.md`
**Depends On**: Plan 003 (UI Improvements) should be implemented first

**Copy the prompt below and paste it into a new Claude Code session:**

---

```
I need you to implement a detailed plan for adding AI cleanup mode selection to the Knowledge Library.

**First, read the complete plan file:**
/Users/ruben/Documents/GitHub/automaker/ Plans + Improvments + Ideas/possible-improvements/004-knowledge-library-cleanup-ai.md

**Context:**
This plan implements a comprehensive cleanup mode system with three selectable modes:
- **Conservative**: Keep more, only discard obvious noise (0.85+ confidence required)
- **Balanced**: Smart suggestions based on content signals (0.70+ confidence required)
- **Aggressive**: Actively flag time-sensitive content (0.55+ confidence required)

Each mode has its own optimized prompt - only the selected mode's prompt is sent to the AI for token efficiency.

**Your task:**
1. Read and understand the complete plan file
2. Follow the implementation phases in order:
   - Phase 1: Create CleanupMode enum
   - Phase 2: Create three mode-specific prompts with factory function
   - Phase 3: Update backend call chain (REST + WebSocket)
   - Phase 4: Update data models
   - Phase 5: Frontend implementation (store, API, components)
3. Create the new files as specified
4. Modify the existing files as outlined
5. Ensure mode flows end-to-end through the generation chain

**Important constraints:**
- Only ONE prompt should be sent per request (~800-900 tokens, NOT all three)
- Invalid cleanup_mode values must be rejected (no silent fallbacks)
- Mode should persist in localStorage
- Signals should be detected and displayed via SignalBadges component

**Dependency note:**
This plan depends on Plan 003 (UI Improvements) which should already be implemented. The confidence bar and content preview components from Plan 003 will be used alongside the new mode selector and signal badges from this plan.

After implementing, verify the acceptance criteria from the plan are met.
```

---

## Execution Order

1. Start a new Claude Code session
2. Copy-paste **Session 1** prompt
3. Complete all implementation and testing for Plan 003
4. Start a new Claude Code session
5. Copy-paste **Session 2** prompt
6. Complete all implementation and testing for Plan 004
